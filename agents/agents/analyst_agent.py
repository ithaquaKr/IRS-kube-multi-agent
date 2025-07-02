"""
Analyst Agent

This module defines the Analyst Agent, which is responsible for investigating
incidents to determine the root cause. The agent is implemented as a runnable
chain that takes an incident as input and returns a root cause analysis.
"""

import json
from typing import Any, Dict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from models import RootCauseAnalysis
from agents.base_agent import BaseAgent
from mcps.abstract_mcp import AbstractMCPClient

# Mock data for simulating access to a Kubernetes environment.
# In a real-world scenario, this would be replaced with actual API calls
# to monitoring, logging, and Kubernetes systems.
mock_data = {
    "logs": {
        "worker-node-1": [
            "[2025-06-19T01:05:12Z] kubelet: Node controller: node worker-node-1 is not ready",
            "[2025-06-19T01:05:30Z] kubelet: Connection to API server timeout",
            "[2025-06-19T01:06:45Z] kernel: CPU thermal throttling activated",
            "[2025-06-19T01:07:20Z] kernel: Memory pressure detected",
        ],
        "api-server": [
            "[2025-06-19T01:03:00Z] Unable to contact node worker-node-1",
            "[2025-06-19T01:05:00Z] Node worker-node-1 marked as NotReady",
        ],
    },
    "metrics": {
        "worker-node-1": {
            "cpu": {"usage": 98.5, "timestamp": "2025-06-19T01:06:00Z"},
            "memory": {"usage": 95.2, "timestamp": "2025-06-19T01:06:00Z"},
            "disk": {"usage": 87.0, "timestamp": "2025-06-19T01:06:00Z"},
            "network": {
                "status": "degraded",
                "timestamp": "2025-06-19T01:05:10Z",
            },
        }
    },
    "node_status": {
        "worker-node-1": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "False",
                    "reason": "KubeletNotReady",
                    "message": "PLEG is not healthy",
                },
                {"type": "MemoryPressure", "status": "True"},
                {"type": "DiskPressure", "status": "False"},
                {"type": "NetworkUnavailable", "status": "False"},
            ]
        }
    },
}


def _collect_evidence(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collects evidence related to the incident from mock data.
    """
    evidence = {}
    alert = incident["alert"].alerts[0]

    if "node" in alert.labels.__dict__:
        node_name = alert.labels.node
        evidence["node_logs"] = mock_data["logs"].get(node_name, [])
        evidence["api_server_logs"] = mock_data["logs"].get("api-server", [])
        evidence["node_metrics"] = mock_data["metrics"].get(node_name, {})
        evidence["node_status"] = mock_data["node_status"].get(node_name, {})

    return evidence


class AnalystAgent(BaseAgent):
    def __init__(self, llm, mcp_client: AbstractMCPClient = None):
        super().__init__(llm)
        self.mcp_client = mcp_client

    def run(self, inputs: dict) -> dict:
        incident = inputs["incident"]
        # Use MCP if available, otherwise fallback to mock data
        if self.mcp_client:
            evidence = self.mcp_client.fetch_evidence(incident.id, context_type="all")
        else:
            evidence = _collect_evidence(incident)
        prompt_template = PromptTemplate(
            template="""
            You are the Analyst, a detective specialized in Kubernetes incident investigation.
            Your role is to find the root cause of incidents by analyzing all available evidence.

            Based on the following information, determine the most likely root cause.

            ALERT:
            Name: {alert_name}
            Description: {alert_description}
            Severity: {alert_severity}

            EVIDENCE:
            {evidence}

            Analyze the above information and provide:
            1. The specific component that is the source of the problem
            2. A clear description of the root cause
            3. List the key evidence that supports your conclusion
            4. A confidence level between 0.0 and 1.0

            Format your response as a JSON object with the following structure:
            {{
                "component": "The specific component that failed",
                "description": "A technical description of the root cause",
                "evidence": ["Key evidence point 1", "Key evidence point 2"],
                "confidence": 0.X
            }}
            """,
            input_variables=[
                "alert_name",
                "alert_description",
                "alert_severity",
                "evidence",
            ],
        )
        prompt_inputs = {
            "alert_name": incident.alert.alerts[0].labels.alertname,
            "alert_description": incident.alert.alerts[0].annotations.description,
            "alert_severity": incident.alert.alerts[0].labels.severity,
            "evidence": json.dumps(evidence, indent=2),
        }
        prompt = prompt_template.format(**prompt_inputs)
        llm_response = self.llm.invoke(prompt)
        parsed = JsonOutputParser(pydantic_object=RootCauseAnalysis).invoke(
            llm_response
        )
        return {"incident": incident, "root_cause_analysis": parsed}
