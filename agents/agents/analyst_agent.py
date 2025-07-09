"""
Analyst Agent

This module defines the Analyst Agent, which is responsible for investigating
incidents to determine the root cause. The agent is implemented as a runnable
chain that takes an incident as input and returns a root cause analysis.
"""

import json

from prompts.analyst_prompt import ANALYST_HUMAN_PROMPT, ANALYST_SYSTEM_PROMPT
from utils import BaseAgent
from utils.parsers import analysis_parser


class AnalystAgent(BaseAgent):
    def __init__(self, llm, tools: list, debug: bool = False):
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=ANALYST_SYSTEM_PROMPT,
            agent_name="analyst_agent",
            parser=analysis_parser,
            debug=debug,
        )

    def run(self, alert_data: dict) -> dict:
        human_prompt = ANALYST_HUMAN_PROMPT.format(
            alert_data=json.dumps(alert_data, indent=2, ensure_ascii=False)
        )
        return super().run(human_prompt)
