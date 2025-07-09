"""
Slack Service for Kube Multi-Agent

This module provides Slack integration for the kube-multi-agent system,
including sending notifications and handling approval workflows.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from config import config
from slack_sdk.models.blocks import (
    ActionsBlock,
    ButtonElement,
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    MarkdownTextObject,
    PlainTextObject,
    SectionBlock,
)
from slack_sdk.models.views import View
from slack_sdk.signature import SignatureVerifier
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)


class SlackService:
    """Slack service for handling notifications and approvals"""

    def __init__(self):
        self.web_client = WebClient(token=config.SLACK_BOT_TOKEN)
        self.socket_client = SocketModeClient(
            app_token=config.SLACK_APP_TOKEN, web_client=self.web_client
        )
        self.signature_verifier = SignatureVerifier(config.SLACK_SIGNING_SECRET)
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def start(self):
        """Start the Slack socket client"""
        self.socket_client.connect()
        logger.info("Slack socket client started")

    def stop(self):
        """Stop the Slack socket client"""
        self.socket_client.close()
        logger.info("Slack socket client stopped")

    def verify_signature(self, body: str, headers: Dict[str, str]) -> bool:
        """Verify Slack request signature"""
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        return self.signature_verifier.is_valid(body, timestamp, signature)

    def send_analysis_result(
        self, alert_data: Dict[str, Any], analysis_result: Dict[str, Any]
    ) -> str:
        """Send analysis result to Slack channel, supporting multiple alerts"""
        alerts = alert_data.get("alerts", [])
        if not alerts:
            # fallback to single alert if "alerts" key is missing
            alerts = [alert_data]

        alert_summaries = []
        for alert in alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            summary = (
                f"*Alert:* {labels.get('alertname', 'Unknown')}\n"
                f"*Instance:* {labels.get('instance', 'N/A')}\n"
                f"*Status:* {alert.get('status', 'Unknown')}\n"
                f"*Severity:* {labels.get('severity', 'Unknown')}\n"
                f"*Summary:* {annotations.get('summary', '')}\n"
                f"*Description:* {annotations.get('description', '')}\n"
            )
            alert_summaries.append(summary)

        blocks = [
            HeaderBlock(text=PlainTextObject(text="🔍 Incident Analysis Complete")),
            DividerBlock(),
            SectionBlock(
                text=MarkdownTextObject(
                    text="*Alerts:*\n" + "\n---\n".join(alert_summaries)
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Severity:* {analysis_result.get('severity_level', 'Unknown')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Root Cause:*\n{analysis_result.get('root_cause', 'Not identified')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Affected Components:*\n{', '.join(analysis_result.get('affected_components', []))}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Investigation Summary:*\n{analysis_result.get('investigation_summary', 'No summary available')}"
                )
            ),
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                ]
            ),
        ]

        response = self.web_client.chat_postMessage(
            channel=config.SLACK_CHANNEL_ID,
            blocks=blocks,
            text="Incident analysis completed",
        )

        if not response["ok"]:
            raise Exception(f"Failed to send analysis result: {response.get('error')}")

        return response["ts"]

    def send_remediation_plan(
        self, alert_data: Dict[str, Any], plan: Dict[str, Any]
    ) -> str:
        """Send remediation plan to Slack channel and request approval"""
        approval_id = str(uuid4())

        # Format steps summary
        steps = plan.get("steps", [])
        steps_text = ""
        for step in steps:
            steps_text += (
                f"*Step {step.get('step_number', '?')}:* {step.get('action', 'Unknown action')}\n"
                f"> *Command:* `{step.get('command', 'N/A')}`\n"
                f"> *Dry Run:* `{step.get('dry_run_command', 'N/A')}`\n"
                f"> *Expected:* {step.get('expected_result', 'N/A')}\n"
                f"> *Rollback:* `{step.get('rollback_command', 'N/A')}`\n"
                f"> *Verify:* {step.get('verification_method', 'N/A')}\n"
                f"> *Duration:* {step.get('estimated_duration', 'N/A')}\n"
                f"> *Step Risk:* {step.get('risk_level', 'N/A')}\n"
                f"> *Escalate if:* {step.get('escalation_trigger', 'N/A')}\n\n"
            )

        # Format list fields
        def fmt_list(key):
            items = plan.get(key, [])
            return "\n• " + "\n• ".join(items) if items else "N/A"

        blocks = [
            HeaderBlock(text=PlainTextObject(text="📋 Remediation Plan Ready")),
            DividerBlock(),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Plan:* {plan.get('plan_name', 'Unknown Plan')}"
                ),
                fields=[
                    MarkdownTextObject(
                        text=f"*Risk Level:* {plan.get('risk_level', 'Unknown')}"
                    ),
                    MarkdownTextObject(
                        text=f"*Estimated Time:* {plan.get('estimated_execution_time', plan.get('estimated_time', 'Unknown'))}"
                    ),
                ],
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Description:*\n{plan.get('description', 'No description available')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Business Impact:*\n{plan.get('business_impact', 'N/A')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Prerequisites:*{fmt_list('prerequisites')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Success Criteria:*{fmt_list('success_criteria')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(text=f"*Execution Steps:*\n{steps_text}")
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Post-Execution Validation:*{fmt_list('post_execution_validation_procedures')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Monitoring Plan:*{fmt_list('monitoring_plan')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Alert Adjustments:*{fmt_list('alert_adjustments')}"
                )
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Documentation Updates:*{fmt_list('documentation_updates')}"
                )
            ),
            DividerBlock(),
            SectionBlock(
                text=MarkdownTextObject(
                    text="⚠️ *This plan requires approval before execution*"
                )
            ),
            ActionsBlock(
                elements=[
                    ButtonElement(
                        text=PlainTextObject(text="✅ Approve"),
                        style="primary",
                        action_id=f"approve_{approval_id}",
                        value=approval_id,
                    ),
                    ButtonElement(
                        text=PlainTextObject(text="❌ Reject"),
                        style="danger",
                        action_id=f"reject_{approval_id}",
                        value=approval_id,
                    ),
                    ButtonElement(
                        text=PlainTextObject(text="📋 View Details"),
                        action_id=f"details_{approval_id}",
                        value=approval_id,
                    ),
                ]
            ),
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Plan ID: {plan.get('plan_id', 'Unknown')} | Approval timeout: {config.SLACK_APPROVAL_TIMEOUT}s"
                    )
                ]
            ),
        ]

        response = self.web_client.chat_postMessage(
            channel=config.SLACK_CHANNEL_ID,
            blocks=blocks,
            text="Remediation plan ready for approval",
        )

        if not response["ok"]:
            raise Exception(f"Failed to send remediation plan: {response.get('error')}")

        # Store approval request
        self.pending_approvals[approval_id] = {
            "plan": plan,
            "alert_data": alert_data,
            "message_ts": response["ts"],
            "channel": config.SLACK_CHANNEL_ID,
            "created_at": datetime.now(),
            "status": "pending",
        }

        return approval_id

    def wait_for_approval(self, approval_id: str) -> Optional[bool]:
        """Wait for approval decision with timeout"""
        start_time = datetime.now()
        timeout = timedelta(seconds=config.SLACK_APPROVAL_TIMEOUT)

        while datetime.now() - start_time < timeout:
            if approval_id in self.pending_approvals:
                approval_data = self.pending_approvals[approval_id]
                if approval_data["status"] in ["approved", "rejected"]:
                    result = approval_data["status"] == "approved"
                    del self.pending_approvals[approval_id]
                    return result

            time.sleep(1)

        # Timeout reached
        if approval_id in self.pending_approvals:
            self._handle_approval_timeout(approval_id)
            del self.pending_approvals[approval_id]

        return None

    def _handle_approval_timeout(self, approval_id: str):
        """Handle approval timeout"""
        approval_data = self.pending_approvals[approval_id]

        blocks = [
            SectionBlock(
                text=MarkdownTextObject(
                    text="⏰ *Approval timeout reached* - Plan execution cancelled"
                )
            ),
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Plan ID: {approval_data['plan'].get('plan_id', 'Unknown')}"
                    )
                ]
            ),
        ]

        self.web_client.chat_update(
            channel=approval_data["channel"],
            ts=approval_data["message_ts"],
            blocks=blocks,
            text="Approval timeout - plan cancelled",
        )

    def handle_button_click(self, payload: Dict[str, Any]):
        """Handle button click events from Slack"""
        action_id = payload.get("actions", [{}])[0].get("action_id", "")
        value = payload.get("actions", [{}])[0].get("value", "")

        if not value or value not in self.pending_approvals:
            return

        self.pending_approvals[value]

        if action_id.startswith("approve_"):
            self._handle_approval(value, True, payload.get("user", {}).get("id"))
        elif action_id.startswith("reject_"):
            self._handle_approval(value, False, payload.get("user", {}).get("id"))
        elif action_id.startswith("details_"):
            self._show_plan_details(value, payload.get("user", {}).get("id"))

    def _handle_approval(self, approval_id: str, approved: bool, user_id: str):
        """Handle approval decision"""
        approval_data = self.pending_approvals[approval_id]
        approval_data["status"] = "approved" if approved else "rejected"
        approval_data["approved_by"] = user_id
        approval_data["approved_at"] = datetime.now()

        status_text = "✅ *Approved*" if approved else "❌ *Rejected*"

        blocks = [
            SectionBlock(
                text=MarkdownTextObject(text=f"{status_text} by <@{user_id}>")
            ),
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Plan ID: {approval_data['plan'].get('plan_id', 'Unknown')}"
                    )
                ]
            ),
        ]

        self.web_client.chat_update(
            channel=approval_data["channel"],
            ts=approval_data["message_ts"],
            blocks=blocks,
            text=f"Plan {'approved' if approved else 'rejected'}",
        )

    def _show_plan_details(self, approval_id: str, user_id: str):
        """Show detailed plan information in a modal"""
        approval_data = self.pending_approvals[approval_id]
        plan = approval_data["plan"]

        # Create detailed view
        steps_text = ""
        for i, step in enumerate(plan.get("steps", []), 1):
            steps_text += f"**Step {i}:** {step.get('action', 'Unknown')}\n"
            steps_text += f"Command: `{step.get('command', 'No command')}`\n"
            if step.get("rollback_command"):
                steps_text += f"Rollback: `{step.get('rollback_command')}`\n"
            steps_text += f"Expected: {step.get('expected_result', 'Unknown')}\n\n"

        view = View(
            type="modal",
            title=PlainTextObject(text="Remediation Plan Details"),
            blocks=[
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Plan:* {plan.get('plan_name', 'Unknown')}"
                    )
                ),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Description:*\n{plan.get('description', 'No description')}"
                    )
                ),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Risk Level:* {plan.get('risk_level', 'Unknown')}"
                    )
                ),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Estimated Time:* {plan.get('estimated_time', 'Unknown')}"
                    )
                ),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Prerequisites:*\n{', '.join(plan.get('prerequisites', []))}"
                    )
                ),
                SectionBlock(
                    text=MarkdownTextObject(text=f"*Execution Steps:*\n{steps_text}")
                ),
            ],
        )

        self.web_client.views_open(
            trigger_id=approval_id,  # This should be the actual trigger_id from the payload
            view=view,
        )

    def send_execution_result(self, execution_result: Dict[str, Any]) -> str:
        """Send execution result to Slack channel"""
        status_emoji = "✅" if execution_result.get("status") == "success" else "❌"

        blocks = [
            HeaderBlock(
                text=PlainTextObject(text=f"{status_emoji} Plan Execution Complete")
            ),
            DividerBlock(),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Execution ID:* {execution_result.get('execution_id', 'Unknown')}"
                ),
                fields=[
                    MarkdownTextObject(
                        text=f"*Status:* {execution_result.get('status', 'Unknown')}"
                    ),
                    MarkdownTextObject(
                        text=f"*Rollback:* {'Yes' if execution_result.get('rollback_performed') else 'No'}"
                    ),
                ],
            ),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*Final Verification:*\n{execution_result.get('final_verification', 'No verification available')}"
                )
            ),
        ]

        if execution_result.get("error_message"):
            blocks.append(
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*Error:*\n{execution_result.get('error_message')}"
                    )
                )
            )

        blocks.append(
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                ]
            )
        )

        response = self.web_client.chat_postMessage(
            channel=config.SLACK_CHANNEL_ID,
            blocks=blocks,
            text="Plan execution completed",
        )

        if not response["ok"]:
            raise Exception(f"Failed to send execution result: {response.get('error')}")

        return response["ts"]

    def send_error_notification(self, error_message: str, context: str = ""):
        """Send error notification to Slack channel"""
        blocks = [
            HeaderBlock(text=PlainTextObject(text="🚨 Error Notification")),
            DividerBlock(),
            SectionBlock(text=MarkdownTextObject(text=f"*Error:*\n{error_message}")),
        ]

        if context:
            blocks.append(
                SectionBlock(text=MarkdownTextObject(text=f"*Context:*\n{context}"))
            )

        blocks.append(
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=f"Error occurred at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                ]
            )
        )

        self.web_client.chat_postMessage(
            channel=config.SLACK_CHANNEL_ID, blocks=blocks, text="Error notification"
        )
