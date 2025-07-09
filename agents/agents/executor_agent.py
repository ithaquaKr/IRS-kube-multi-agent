"""
Executor Agent

This module defines the Executor Agent, which is responsible for executing
remediation plans. The agent is implemented as a runnable chain that takes
an incident and an approved plan as input, executes the steps, and returns
the execution results and a summary.
"""

import json
import uuid

from prompts.executor_prompt import EXECUTOR_HUMAN_PROMPT, EXECUTOR_SYSTEM_PROMPT
from utils import BaseAgent
from utils.parsers import execution_parser


class ExecutorAgent(BaseAgent):
    def __init__(self, llm, tools: list, debug: bool = False):
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            agent_name="executor_agent",
            parser=execution_parser,
            debug=debug,
        )

    def run(self, approved_plan: dict, alert_data: dict, analysis_result: dict) -> dict:
        human_prompt = EXECUTOR_HUMAN_PROMPT.format(
            approved_plan=json.dumps(approved_plan, indent=2, ensure_ascii=False),
            alert_data=json.dumps(alert_data, indent=2, ensure_ascii=False),
            analysis_result=json.dumps(analysis_result, indent=2, ensure_ascii=False),
        )
        result = super().run(human_prompt)
        # Ensure execution_id exists
        if isinstance(result, dict) and not result.get("execution_id"):
            result["execution_id"] = str(uuid.uuid4())
        return result
