"""
Orchestrator Agent

This module defines the Orchestrator Agent, which manages the overall incident
resolution workflow. It delegates tasks to specialist agents and makes decisions
about the next steps to take based on the incident's state.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict

from langchain_core.language_models import BaseLLM
from langchain_core.runnables import Runnable, RunnableLambda

from models import AlertGroup, Incident, IncidentState


def _create_incident(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new incident from an alert.
    """
    try:
        if isinstance(alert_data, str):
            alert_data = json.loads(alert_data)

        alert_group = AlertGroup.model_validate(alert_data)

        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        now = datetime.now()

        incident = Incident(
            id=incident_id,
            state=IncidentState.RECEIVED,
            alert=alert_group,
            creation_time=now,
            last_updated=now,
        )

        return {
            "incident": incident,
            "message": f"Created new incident {incident_id} for alert {alert_group.alerts[0].labels.alertname}",
        }

    except Exception as e:
        return {"error": f"Failed to create incident: {str(e)}"}


def _generate_approval_request(llm: BaseLLM, incident: Incident) -> Dict[str, Any]:
    """
    Generates a human-friendly approval request for remediation plans using the LLM.
    """
    if not incident.remediation_plans:
        return {
            "incident": incident,
            "error": "No remediation plans available for approval",
        }

    alert = incident.alert.alerts[0]

    prompt = f"""
    You need to create a clear, concise approval request for human operators.

    INCIDENT DETAILS:
    ID: {incident.id}
    Alert: {alert.labels.alertname}
    Description: {alert.annotations.description}
    Component: {incident.root_cause_analysis.component if incident.root_cause_analysis else "Unknown"}

    ROOT CAUSE:
    {incident.root_cause_analysis.description if incident.root_cause_analysis else "Not determined"}

    PROPOSED REMEDIATION PLAN(S):
    """

    for i, plan in enumerate(incident.remediation_plans):
        prompt += f"""
        PLAN #{i + 1}: {plan.title}
        Description: {plan.description}
        Impact: {plan.impact_assessment}
        Estimated time: {plan.estimated_time}
        Risk level: {plan.steps[0].risk_level if plan.steps else "Unknown"}

        Steps:
        """

        for j, step in enumerate(plan.steps):
            prompt += f"  {j + 1}. {step.description}"
            if step.command:
                prompt += f" (Command: {step.command})"
            prompt += "\n"

    approval_message = llm.invoke(prompt).content

    return {
        "incident": incident,
        "approval_request": approval_message,
        "plans": incident.remediation_plans,
    }


def get_orchestrator_agent(llm: BaseLLM) -> Runnable:
    """
    Builds and returns the Orchestrator Agent as a runnable chain.
    """

    def orchestrate_logic(inputs: Dict[str, Any]) -> Dict[str, Any]:
        incident = inputs.get("incident")
        action = inputs.get("action", "process")

        if action == "create_incident" and not incident:
            return _create_incident(inputs["alert_data"])

        if not incident:
            return {"error": "No incident provided for processing"}

        # Handle different incident states
        if incident.state == IncidentState.RECEIVED:
            incident.update_state(IncidentState.INVESTIGATING)
            return {
                "next_step": "investigate",
                "agent": "analyst",
                "incident": incident,
            }

        elif incident.state == IncidentState.ANALYZED:
            incident.update_state(IncidentState.PLANNING)
            return {"next_step": "plan", "agent": "planner", "incident": incident}

        elif incident.state == IncidentState.PLANNING:
            # Need human approval for the plan
            incident.update_state(IncidentState.APPROVAL_PENDING)
            return _generate_approval_request(llm, incident)

        elif incident.state == IncidentState.APPROVAL_PENDING:
            if inputs.get("approved"):
                incident.approved_plan_index = inputs.get("plan_index", 0)
                incident.update_state(IncidentState.EXECUTING)
                return {
                    "next_step": "execute",
                    "agent": "executor",
                    "incident": incident,
                }
            else:
                # Plan rejected, go back to planning with feedback
                incident.update_state(IncidentState.PLANNING)
                return {
                    "next_step": "plan",
                    "agent": "planner",
                    "incident": incident,
                    "feedback": inputs.get("feedback", ""),
                }

        elif incident.state == IncidentState.EXECUTING:
            # If execution is complete, update the incident state
            if inputs.get("execution_complete"):
                if inputs.get("success"):
                    incident.update_state(IncidentState.RESOLVED)
                    incident.resolution_summary = inputs.get(
                        "summary", "Incident resolved successfully."
                    )
                else:
                    incident.update_state(IncidentState.FAILED)
                    incident.resolution_summary = inputs.get(
                        "summary", "Incident resolution failed."
                    )

            return {"incident": incident}

        # Default response for other states
        return {"incident": incident}

    return RunnableLambda(orchestrate_logic)
