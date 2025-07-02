"""
Executor Agent

This module defines the Executor Agent, which is responsible for executing
remediation plans. The agent is implemented as a runnable chain that takes
an incident and an approved plan as input, executes the steps, and returns
the execution results and a summary.
"""

import subprocess
import time
from typing import Any, Dict, List, Tuple

from langchain_core.language_models import BaseLLM
from langchain_core.runnables import Runnable, RunnablePassthrough

from models import ExecutionResult, Incident

# Flag to control whether commands are actually executed
# In production, this would be True
EXECUTE_COMMANDS = False


def _execute_step(step: Dict[str, Any], step_index: int) -> ExecutionResult:
    """
    Executes a single step from the remediation plan.
    """
    print(f"Executing step {step_index + 1}: {step['description']}")

    command = step.get("command")
    if not command:
        return ExecutionResult(
            step_index=step_index,
            step_description=step["description"],
            command=None,
            success=True,
            output="No command to execute - marked as completed",
            error=None,
        )

    print(f"Command: {command}")

    try:
        if EXECUTE_COMMANDS:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr if result.stderr else None
        else:
            print("[SIMULATED] Command would be executed here")
            time.sleep(1)
            success = True
            output = f"[SIMULATED] Command executed successfully: {command}"
            error = None

        return ExecutionResult(
            step_index=step_index,
            step_description=step["description"],
            command=command,
            success=success,
            output=output,
            error=error,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            step_index=step_index,
            step_description=step["description"],
            command=command,
            success=False,
            output="",
            error="Command timed out after 5 minutes",
        )
    except Exception as e:
        return ExecutionResult(
            step_index=step_index,
            step_description=step["description"],
            command=command,
            success=False,
            output="",
            error=str(e),
        )


def _verify_resolution(incident: Incident) -> Tuple[bool, str]:
    """
    Verifies that the incident has been resolved.
    """
    alert = incident.alert.alerts[0]
    alert_name = alert.labels.alertname

    print(f"Verifying resolution for alert: {alert_name}")

    if alert_name == "KubeNodeNotReady" and "node" in alert.labels.__dict__:
        node_name = alert.labels.node
        if EXECUTE_COMMANDS:
            try:
                result = subprocess.run(
                    f"kubectl get node {node_name} -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip() == "True":
                    return True, f"Node {node_name} is now Ready"
                else:
                    return (
                        False,
                        f"Node {node_name} is still NotReady: {result.stderr}",
                    )
            except Exception as e:
                return False, f"Failed to verify node status: {str(e)}"
        else:
            return True, f"[SIMULATED] Node {node_name} is now Ready"

    return True, f"[SIMULATED] Alert {alert_name} is no longer firing"


def _create_execution_summary(
    llm: BaseLLM,
    incident: Incident,
    execution_results: List[ExecutionResult],
    resolution_verified: bool,
    verification_output: str,
) -> str:
    """
    Creates a summary of the execution results using the LLM.
    """
    alert = incident.alert.alerts[0]
    plan = incident.remediation_plans[incident.approved_plan_index]

    prompt = f"""
    Create a concise summary of the execution of a Kubernetes incident remediation plan.

    INCIDENT:
    ID: {incident.id}
    Alert: {alert.labels.alertname}
    Description: {alert.annotations.description}

    REMEDIATION PLAN:
    Title: {plan.title}

    EXECUTION RESULTS:
    """

    for result in execution_results:
        status = "✅ Success" if result.success else "❌ Failed"
        prompt += (
            f"\nStep {result.step_index + 1}: {status} - {result.step_description}"
        )
        if not result.success and result.error:
            prompt += f"\n   Error: {result.error}"

    prompt += f"\n\nVERIFICATION: {'✅ Resolved' if resolution_verified else '❌ Not resolved'}"
    prompt += f"\n{verification_output}"

    prompt += """
    Please provide a concise summary (3-5 sentences) that:
    1. States whether the remediation was successful or not
    2. Highlights key steps that were performed
    3. Mentions any issues encountered
    4. Confirms whether the original alert condition has been resolved

    Write this as a concise technical report for an operations team.
    """

    return llm.invoke(prompt).content


def get_executor_agent(llm: BaseLLM) -> Runnable:
    """
    Builds and returns the Executor Agent as a runnable chain.
    """

    def execute_plan(inputs: Dict[str, Any]) -> Dict[str, Any]:
        incident = inputs["incident"]
        plan_index = incident.approved_plan_index
        plan = incident.remediation_plans[plan_index]

        execution_results = []
        overall_success = True

        for i, step in enumerate(plan.steps):
            result = _execute_step(step.model_dump(), i)
            execution_results.append(result)
            incident.execution_results.append(result)

            if not result.success:
                overall_success = False
                break

        resolution_verified = False
        verification_output = ""

        if overall_success:
            resolution_verified, verification_output = _verify_resolution(incident)
            overall_success = resolution_verified

        summary = _create_execution_summary(
            llm, incident, execution_results, resolution_verified, verification_output
        )

        return {
            "incident": incident,
            "execution_results": execution_results,
            "success": overall_success,
            "summary": summary,
            "execution_complete": True,
        }

    return RunnablePassthrough.assign(output=execute_plan) | (lambda x: x["output"])
