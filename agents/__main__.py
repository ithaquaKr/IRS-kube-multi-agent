import json
import uvicorn
from fastapi import FastAPI
from typing import Any, Dict, TypedDict

from langgraph.graph import END, StateGraph

from agents.analyst_agent import AnalystAgent
from agents.executor_agent import ExecutorAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.planner_agent import PlannerAgent
from llms.gemini import create_gemini_client
from models import Alert, Incident


class IncidentStateGraph(TypedDict):
    """State for the incident workflow graph."""

    incident: Incident
    action: str
    error: str
    approved: bool
    plan_index: int
    feedback: str
    execution_complete: bool
    success: bool
    summary: str
    next_step: str
    alert_data: Dict[str, Any]


app = FastAPI()


@app.post("/webhook")
async def alertmanager_webhook(alert_payload: Alert):
    """Receives alerts from Alertmanager and triggers incident processing."""
    print(
        f"Received Alertmanager webhook: {json.dumps(alert_payload.model_dump(), indent=2)}"
    )

    try:
        # Process the incident using the existing logic
        incident = process_incident(alert_payload.model_dump())
        return {"status": "success", "incident_id": incident.id}
    except Exception as e:
        print(f"Error processing incident: {e}")
        return {"status": "error", "message": str(e)}, 500


def create_llm():
    """Create a language model instance."""
    return create_gemini_client()


def create_k8s_incident_graph() -> StateGraph:
    """Create the incident management workflow graph."""
    llm = create_llm()

    # Example: instantiate MCP clients here if needed
    # k8s_mcp_client = K8sMCPClient(server_url="http://k8s-mcp-server:8080")
    # prometheus_mcp_client = PrometheusMCPClient(server_url="http://prometheus-mcp-server:8080")

    # Pass MCP client to AnalystAgent if available
    orchestrator_agent = OrchestratorAgent(llm)
    analyst_agent = AnalystAgent(llm)  # Add mcp_client=k8s_mcp_client if integrating
    planner_agent = PlannerAgent(llm)
    executor_agent = ExecutorAgent(llm)

    workflow = StateGraph(IncidentStateGraph)

    # Add nodes for each agent, using the run method
    workflow.add_node("orchestrator", orchestrator_agent.run)
    workflow.add_node("analyst", analyst_agent.run)
    workflow.add_node("planner", planner_agent.run)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("executor", executor_agent.run)

    # Define conditional edges from orchestrator based on 'next_step'
    workflow.add_conditional_edges(
        "orchestrator",
        lambda state: state.get("next_step") or None,
        {
            "investigate": "analyst",
            "plan": "planner",
            "human_approval": "human_approval",
            "execute": "executor",
            "resolved": END,  # Incident resolved
            "failed": END,  # Incident failed
            None: END,  # Default to END if next_step is not set
        },
    )

    # Define unconditional edges back to orchestrator
    workflow.add_edge("analyst", "orchestrator")
    workflow.add_edge("planner", "orchestrator")
    workflow.add_edge("human_approval", "orchestrator")
    workflow.add_edge("executor", "orchestrator")

    # Set the entry point
    workflow.set_entry_point("orchestrator")

    return workflow


# Node functions
def human_approval_node(state: IncidentStateGraph) -> IncidentStateGraph:
    """Simulate human approval of remediation plans."""
    incident = state["incident"]
    print(f"[Human] Reviewing remediation plans for incident: {incident.id}")

    # In a real system, this would pause execution and wait for human input
    # For now, we'll simulate automatic approval of the first plan

    # Get approval request if it exists
    approval_request = state.get("approval_request", "")
    if approval_request:
        print(f"\n{approval_request}\n")

    # Print available plans
    print("\nAvailable remediation plans:")
    for i, plan in enumerate(incident.remediation_plans):
        print(f"Plan #{i + 1}: {plan.title}")
        print(f"Description: {plan.description}")
        print(f"Impact: {plan.impact_assessment}")
        print(f"Steps: {len(plan.steps)}")
        print()

    # Simulate human input
    print("Simulating human approval of the first plan...")
    approved = True
    plan_index = 0
    feedback = ""

    next_step = "execute" if approved else "plan"  # Determine next_step

    return {
        **state,
        "approved": approved,
        "plan_index": plan_index,
        "feedback": feedback,
        "next_step": next_step,  # Add next_step
    }


# Utility functions for the main workflow


def load_alert_from_file(file_path: str) -> Dict[str, Any]:
    """Load an alert from a JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def process_incident(alert_data: Dict[str, Any]) -> Incident:
    """Process an incident through the entire workflow."""
    workflow = create_k8s_incident_graph()
    app_graph = workflow.compile()

    state = {
        "incident": None,
        "action": "create_incident",
        "error": "",
        "approved": False,
        "plan_index": 0,
        "feedback": "",
        "execution_complete": False,
        "success": False,
        "summary": "",
        "next_step": "",
        "alert_data": alert_data,
    }

    for output in app_graph.stream(state):
        current_state = list(output.values())[0]
        if current_state.get("error"):
            print(f"Error: {current_state['error']}")

    final_state = list(output.values())[0]
    return final_state.get("incident")


def main():
    """Main entry point for the application."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        print("Starting FastAPI webhook server...")
        uvicorn.run(app, host="0.0.0.0", port=3000)
    else:
        if len(sys.argv) > 1:
            alert_file = sys.argv[1]
        else:
            alert_file = "examples/alerts/node-down.json"

        print(f"Processing alert from file: {alert_file}")

        alert_data = load_alert_from_file(alert_file)
        incident = process_incident(alert_data)

        print("\n" + "=" * 80)
        print(f"Incident {incident.id} - Final State: {incident.state}")

        if incident.resolution_summary:
            print("\nResolution Summary:")
            print(incident.resolution_summary)

        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
