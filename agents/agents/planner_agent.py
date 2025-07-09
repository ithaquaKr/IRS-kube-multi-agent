"""
Planner Agent

This module defines the Planner Agent, which is responsible for creating
remediation plans based on root cause analysis. The agent is implemented
as a runnable chain that takes an incident and root cause analysis as input
and returns a list of proposed remediation plans.
"""

import json

from prompts.planner_prompt import PLANNER_HUMAN_PROMPT, PLANNER_SYSTEM_PROMPT
from utils import BaseAgent
from utils.parsers import plan_parser


class PlannerAgent(BaseAgent):
    def __init__(self, llm, tools: list, debug: bool = False):
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            agent_name="planner_agent",
            parser=plan_parser,
            debug=debug,
        )

    def run(self, analysis_result: dict, alert_data: dict) -> dict:
        human_prompt = PLANNER_HUMAN_PROMPT.format(
            analysis_result=json.dumps(analysis_result, indent=2, ensure_ascii=False),
            alert_data=json.dumps(alert_data, indent=2, ensure_ascii=False),
        )
        return super().run(human_prompt)
