"""
Planner Agent

This module defines the Planner Agent, which is responsible for creating
remediation plans based on root cause analysis. The agent is implemented
as a runnable chain that takes an incident and root cause analysis as input
and returns a list of proposed remediation plans.
"""

import json
from typing import Any, Dict, List


from models import Incident, RemediationPlan, RemediationStep
from .base_agent import BaseAgent


def _generate_remediation_plans_prompt(incident: Incident, feedback: str = "") -> str:
    """
    Generates the prompt for the LLM to create remediation plans.
    """
    alert = incident.alert.alerts[0]
    root_cause = incident.root_cause_analysis

    prompt = f"""
    Based on the following information about a Kubernetes incident, create detailed remediation plans.

    ALERT:
    Name: {alert.labels.alertname}
    Description: {alert.annotations.description}
    Severity: {alert.labels.severity}

    ROOT CAUSE ANALYSIS:
    Component: {root_cause.component}
    Description: {root_cause.description}
    Evidence: {", ".join(root_cause.evidence)}
    Confidence: {root_cause.confidence}

    {f"FEEDBACK FROM PREVIOUS PLAN: {feedback}" if feedback else ""}

    Generate 1-2 remediation plans that address the root cause of this incident.
    Each plan should include:

    1. A title and description of the approach
    2. An assessment of the potential impact
    3. A detailed list of steps with commands to execute
    4. Estimated time to implement
    5. A rollback plan in case of failure

    Format your response as a JSON array with the following structure:
    [
        {{
            "title": "Plan Title",
            "description": "Description of the approach",
            "impact_assessment": "Assessment of potential impact",
            "estimated_time": "Estimated implementation time (e.g., '5 minutes')",
            "steps": [
                {{
                    "description": "Step description",
                    "command": "command to execute (if applicable)",
                    "expected_outcome": "What should happen after this step",
                    "risk_level": "low/medium/high"
                }}
            ],
            "rollback_plan": [
                {{
                    "description": "Rollback step",
                    "command": "command to execute",
                    "expected_outcome": "Expected outcome",
                    "risk_level": "low/medium/high"
                }}
            ]
        }}
    ]
    """
    return prompt


def _parse_remediation_plans(plans_data: List[Dict[str, Any]]) -> List[RemediationPlan]:
    """
    Parses the JSON response from the LLM into a list of RemediationPlan objects.
    """
    plans = []
    for plan_data in plans_data:
        steps = [RemediationStep(**step) for step in plan_data.pop("steps", [])]

        rollback_steps = None
        if "rollback_plan" in plan_data:
            rollback_steps = [
                RemediationStep(**step) for step in plan_data.pop("rollback_plan", [])
            ]

        plan = RemediationPlan(**plan_data, steps=steps, rollback_plan=rollback_steps)
        plans.append(plan)
    return plans


class PlannerAgent(BaseAgent):
    def run(self, inputs: dict) -> dict:
        incident = inputs["incident"]
        feedback = inputs.get("feedback", "")
        if not incident.root_cause_analysis:
            step = RemediationStep(
                description="Contact Kubernetes administrator for manual intervention",
                command=None,
                expected_outcome="Manual resolution of the issue",
                risk_level="low",
            )
            fallback_plan = RemediationPlan(
                title="Fallback Plan: Manual Intervention",
                description="Automated planning failed. Manual intervention required.",
                impact_assessment="Unknown, requires human assessment",
                steps=[step],
                estimated_time="Unknown, depends on human availability",
                rollback_plan=None,
            )
            return {"incident": incident, "remediation_plans": [fallback_plan]}
        prompt = _generate_remediation_plans_prompt(incident, feedback)
        response = self.llm.invoke(prompt).content
        try:
            plans_data = json.loads(response)
            plans = _parse_remediation_plans(plans_data)
        except (json.JSONDecodeError, KeyError):
            step = RemediationStep(
                description="Contact Kubernetes administrator for manual intervention",
                command=None,
                expected_outcome="Manual resolution of the issue",
                risk_level="low",
            )
            fallback_plan = RemediationPlan(
                title="Fallback Plan: Manual Intervention",
                description="Automated planning failed. Manual intervention required.",
                impact_assessment="Unknown, requires human assessment",
                steps=[step],
                estimated_time="Unknown, depends on human availability",
                rollback_plan=None,
            )
            plans = [fallback_plan]
        incident.remediation_plans = plans
        return {"incident": incident, "remediation_plans": plans}
