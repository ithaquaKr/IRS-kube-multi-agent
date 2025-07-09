import asyncio
import json
import sys
from contextlib import contextmanager
from typing import Any, Dict

import uvicorn
from config import config, validate_llm_config, validate_slack_config
from fastapi import FastAPI, HTTPException, Request
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from llms.gemini import create_gemini_client
from models import Alert
from prompts.analyst_prompt import ANALYST_SYSTEM_PROMPT
from utils.search_tool import get_analysis_tools
from utils.slack_events import SlackEventHandler
from utils.slack_service import SlackService

from agents.analyst_agent import AnalystAgent
from agents.executor_agent import ExecutorAgent
from agents.planner_agent import PlannerAgent


@contextmanager
def lifespan(app: FastAPI):
    """Lifespan context for FastAPI startup and shutdown"""
    # Startup
    try:
        validate_llm_config()
        validate_slack_config()
        slack_service = SlackService()
        slack_event_handler = SlackEventHandler(
            slack_service.socket_client, slack_service.web_client
        )
        slack_event_handler.register_button_handler(
            "approve", slack_service.handle_button_click
        )
        slack_event_handler.register_button_handler(
            "reject", slack_service.handle_button_click
        )
        slack_event_handler.register_button_handler(
            "details", slack_service.handle_button_click
        )
        slack_service.start()
        slack_service.socket_client.socket_mode_request_listeners.append(
            slack_event_handler.handle_event
        )
        app.state.slack_service = slack_service
        app.state.slack_event_handler = slack_event_handler
        print("Slack service initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Slack service: {e}")
        raise
    try:
        yield
    finally:
        # Shutdown
        slack_service = getattr(app.state, "slack_service", None)
        if slack_service:
            slack_service.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def alertmanager_webhook(alert_payload: Alert, request: Request):
    """Handle Alertmanager webhook events.

    Args:
        alert_payload (Alert): The alert payload from Alertmanager.
        request (Request): The FastAPI request object.

    Returns:
        dict: The response from the webhook handling.
    """
    print(
        f"Received Alertmanager webhook: {json.dumps(alert_payload.model_dump(), indent=2)}"
    )
    slack_service = request.app.state.slack_service
    try:
        # Run the multi-agent system with Slack integration
        result = await run_multi_agent_system_with_slack(
            alert_payload.model_dump(), slack_service
        )
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"Error processing incident: {e}")
        if slack_service:
            slack_service.send_error_notification(
                str(e), f"Error processing alert: {alert_payload.labels.alertname}"
            )
        return {"status": "error", "message": str(e)}, 500


@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events (for webhook verification)"""
    slack_service = request.app.state.slack_service
    body = await request.body()
    headers = dict(request.headers)

    # Verify signature
    if not slack_service.verify_signature(body.decode(), headers):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Handle URL verification
    data = await request.json()
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    return {"status": "ok"}


def load_alert_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load alert data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Dict[str, Any]: Alert data as a dictionary.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# TODO: Use Supervisor Agent
# Logic send, approval from Slack move to tools
# Supervisor will use tool to do the flow
async def run_multi_agent_system_with_slack(alert_data: dict, slack_service):
    """Run the multi-agent system with Slack integration"""
    if not slack_service:
        raise ValueError("SlackService instance is required for this function")

    llm = create_gemini_client()

    mcp_client = MultiServerMCPClient(
        {
            "kubectl-ai": {
                "command": "kubectl-ai",
                "args": ["--mcp-server"],
                "transport": "stdio",
            },
        }
    )
    tools_mcp = await mcp_client.get_tools()
    tools = tools_mcp + get_analysis_tools()

    # Initialize agents
    analyst_agent = AnalystAgent(llm, tools=tools, debug=False)
    planner_agent = PlannerAgent(llm, tools=tools, debug=False)
    executor_agent = ExecutorAgent(llm, tools=tools, debug=False)

    try:
        # Step 1: Run analysis
        print("🔍 Running analysis...")
        analysis_result = analyst_agent.run(alert_data)

        # Send analysis result to Slack
        slack_service.send_analysis_result(alert_data, analysis_result)
        print("✅ Analysis result sent to Slack")

        # Step 2: Generate remediation plan
        print("📋 Generating remediation plan...")
        plan = planner_agent.run(analysis_result, alert_data)

        # Send plan to Slack and request approval
        approval_id = slack_service.send_remediation_plan(alert_data, plan)
        print(f"📋 Remediation plan sent to Slack (Approval ID: {approval_id})")

        # Wait for approval
        print("⏳ Waiting for Slack approval...")
        approval_result = slack_service.wait_for_approval(approval_id)

        if approval_result is None:
            print("⏰ Approval timeout - cancelling execution")
            return {"status": "cancelled", "reason": "approval_timeout"}
        elif not approval_result:
            print("❌ Plan rejected - cancelling execution")
            return {"status": "cancelled", "reason": "plan_rejected"}
        else:
            print("✅ Plan approved - proceeding with execution")

        # Step 3: Execute the plan
        print("🚀 Executing remediation plan...")
        execution_result = executor_agent.run(plan, alert_data)

        # Send execution result to Slack
        slack_service.send_execution_result(execution_result)
        print("✅ Execution result sent to Slack")

        return {
            "analysis": analysis_result,
            "plan": plan,
            "execution": execution_result,
            "status": "completed",
        }

    except Exception as e:
        error_msg = f"Error in multi-agent system: {str(e)}"
        print(f"❌ {error_msg}")
        slack_service.send_error_notification(error_msg, "Multi-agent system error")

        raise


async def run_multi_agent_system(alert_data: dict):
    """Original multi-agent system without Slack integration"""
    llm = create_gemini_client()

    mcp_client = MultiServerMCPClient(
        {
            "kubectl-ai": {
                "command": "kubectl-ai",
                "args": ["--mcp-server"],
                "transport": "stdio",
            },
        }
    )
    tools_mcp = await mcp_client.get_tools()
    tools = tools_mcp + get_analysis_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=ANALYST_SYSTEM_PROMPT,
        name="analyst_agent",
    )

    for step in agent.stream(
        {"messages": [{"role": "user", "content": f"Incident alert: {alert_data}"}]},
        stream_mode="values",
    ):
        print(step["messages"][-1].pretty_print())


def main():
    """Main function to run the multi-agent system or start the FastAPI server"""
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        print("Starting FastAPI webhook server with Slack integration...")
        uvicorn.run(app, host=config.HOST, port=config.PORT)
    else:
        if len(sys.argv) > 1:
            alert_file = sys.argv[1]
        else:
            alert_file = "examples/alerts/node-down.json"
        print(f"Processing alert from file: {alert_file}")
        alert_data = load_alert_from_file(alert_file)
        # For CLI, we don't use app.state, so create a SlackService instance directly
        slack_service = SlackService()
        asyncio.run(run_multi_agent_system_with_slack(alert_data, slack_service))


if __name__ == "__main__":
    main()
