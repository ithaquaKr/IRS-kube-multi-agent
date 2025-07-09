from typing import Any, Callable
import json


class BaseAgent:
    def __init__(
        self,
        llm,
        tools: list,
        system_prompt: str = None,
        agent_name: str = None,
        parser: Callable = None,
        debug: bool = False,
    ):
        from langgraph.prebuilt import create_react_agent

        self.agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            name=agent_name,
            debug=debug,
        )
        self.parser = parser

    def run(self, human_prompt: str) -> Any:
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": human_prompt}]}
        )
        try:
            # if self.parser:
            #     return self.parser.parse(last_message)
            content = result["messages"][-1].content

            # Remove code block markers if present
            if content.startswith("```json"):
                content = content[len("```json") :].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            parsed_result = json.loads(content)
            return parsed_result
        except Exception as e:
            return {
                "error": f"Error parsing agent result: {str(e)}",
                "raw_result": str(result),
            }
