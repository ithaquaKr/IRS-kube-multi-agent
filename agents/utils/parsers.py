"""
Output parsers for agents
"""

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AnalysisResult(BaseModel):
    """Analysis result from Analyst agent"""

    root_cause: str = Field(description="Root cause of the incident")
    severity_level: str = Field(
        description="Severity level: low, medium, high, critical"
    )
    affected_components: List[str] = Field(
        description="Components affected by the incident"
    )
    investigation_summary: str = Field(
        description="Summary of the investigation process"
    )


class PlanStep(BaseModel):
    """A step in the remediation plan"""

    step_number: int = Field(description="Step sequence number")
    action: str = Field(description="Action to be performed")
    command: str = Field(description="kubectl command or script to run")
    expected_result: str = Field(description="Expected result")
    rollback_command: Optional[str] = Field(
        description="Rollback command if error occurs"
    )


class RemediationPlan(BaseModel):
    """Remediation plan from Planner agent"""

    plan_id: str = Field(description="Plan ID")
    plan_name: str = Field(description="Plan name")
    description: str = Field(description="Plan description")
    risk_level: str = Field(description="Risk level: low, medium, high")
    estimated_time: str = Field(description="Estimated time")
    steps: List[PlanStep] = Field(description="Execution steps")
    prerequisites: List[str] = Field(description="Prerequisites")


class ExecutionResult(BaseModel):
    """Execution result from Executor agent"""

    execution_id: str = Field(description="Execution ID")
    status: str = Field(description="Status: success, failed, partial")
    executed_steps: List[Dict[str, Any]] = Field(description="Steps that were executed")
    error_message: Optional[str] = Field(description="Error message if any")
    rollback_performed: bool = Field(description="Whether rollback was performed")
    final_verification: str = Field(description="Final verification result")


# Create parser instances
analysis_parser = PydanticOutputParser(pydantic_object=AnalysisResult)
plan_parser = PydanticOutputParser(pydantic_object=RemediationPlan)
execution_parser = PydanticOutputParser(pydantic_object=ExecutionResult)


def get_analysis_format_instructions():
    """Return format instructions for Analyst"""
    return analysis_parser.get_format_instructions()


def get_plan_format_instructions():
    """Return format instructions for Planner"""
    return plan_parser.get_format_instructions()


def get_execution_format_instructions():
    """Return format instructions for Executor"""
    return execution_parser.get_format_instructions()
