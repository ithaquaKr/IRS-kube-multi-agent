from langgraph_supervisor import create_supervisor
from prompts.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT

from agents.analyst_agent import AnalystAgent
from agents.executor_agent import ExecutorAgent
from agents.planner_agent import PlannerAgent


def supervisor_agent(llm, tools):
    # analyst_tools = get_analysis_tools()
    # planner_tools = get_planner_tools()
    # executor_tools = get_executor_tools()
    analyst = AnalystAgent(llm, tools)
    planner = PlannerAgent(llm, tools)
    executor = ExecutorAgent(llm, tools)
    supervisor = create_supervisor(
        agents=[analyst.agent, planner.agent, executor.agent],
        model=llm,
        prompt=SUPERVISOR_SYSTEM_PROMPT,
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    return supervisor
