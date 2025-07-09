"""
Slack Event Handler

This module handles incoming Slack events and interactions for the kube-multi-agent system.
"""

import json
import logging
from typing import Any, Callable, Dict

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)


class SlackEventHandler:
    """Handler for Slack events and interactions"""

    def __init__(self, socket_client: SocketModeClient, web_client: WebClient):
        self.socket_client = socket_client
        self.web_client = web_client
        self.button_handlers: Dict[str, Callable] = {}

    def register_button_handler(self, action_id: str, handler: Callable):
        """Register a handler for a specific button action"""
        self.button_handlers[action_id] = handler

    def handle_event(self, event: Dict[str, Any]):
        """Handle incoming Slack events"""
        event_type = event.get("type")

        if event_type == "events_api":
            self._handle_events_api(event)
        elif event_type == "interactive":
            self._handle_interactive(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def _handle_events_api(self, event: Dict[str, Any]):
        """Handle Events API events"""
        payload = event.get("payload", {})
        event_type = payload.get("type")

        if event_type == "url_verification":
            self._handle_url_verification(payload)
        elif event_type == "event_callback":
            self._handle_event_callback(payload)
        else:
            logger.info(f"Unhandled Events API event type: {event_type}")

    def _handle_interactive(self, event: Dict[str, Any]):
        """Handle interactive events (button clicks, etc.)"""
        payload = json.loads(event.get("payload", "{}"))

        if payload.get("type") == "block_actions":
            self._handle_block_actions(payload)
        elif payload.get("type") == "view_submission":
            self._handle_view_submission(payload)
        else:
            logger.info(f"Unhandled interactive event type: {payload.get('type')}")

    def _handle_url_verification(self, payload: Dict[str, Any]):
        """Handle URL verification challenge"""
        challenge = payload.get("challenge")
        if challenge:
            self.socket_client.send_socket_mode_response(
                {
                    "envelope_id": payload.get("envelope_id"),
                    "payload": {"challenge": challenge},
                }
            )

    def _handle_event_callback(self, payload: Dict[str, Any]):
        """Handle event callbacks"""
        event = payload.get("event", {})
        event_type = event.get("type")

        if event_type == "message":
            self._handle_message(event)
        elif event_type == "app_mention":
            self._handle_app_mention(event)
        else:
            logger.info(f"Unhandled event callback type: {event_type}")

    def _handle_message(self, event: Dict[str, Any]):
        """Handle message events"""
        # Handle direct messages or channel messages as needed
        logger.info(f"Received message: {event.get('text', '')}")

    def _handle_app_mention(self, event: Dict[str, Any]):
        """Handle app mention events"""
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")

        logger.info(f"App mentioned by {user} in {channel}: {text}")

        # You can add custom commands here
        if "status" in text.lower():
            self._send_status_message(channel)
        elif "help" in text.lower():
            self._send_help_message(channel)

    def _handle_block_actions(self, payload: Dict[str, Any]):
        """Handle block actions (button clicks, etc.)"""
        actions = payload.get("actions", [])

        for action in actions:
            action_id = action.get("action_id", "")

            # Check if we have a registered handler for this action
            if action_id in self.button_handlers:
                try:
                    self.button_handlers[action_id](payload)
                except Exception as e:
                    logger.error(f"Error handling button action {action_id}: {e}")
            else:
                logger.info(f"No handler registered for action: {action_id}")

    def _handle_view_submission(self, payload: Dict[str, Any]):
        """Handle view submission events"""
        # Handle modal submissions if needed
        logger.info("View submission received")

    def _send_status_message(self, channel: str):
        """Send status message to channel"""
        message = {
            "channel": channel,
            "text": "🤖 Kube Multi-Agent Status: Online and monitoring for incidents",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🤖 *Kube Multi-Agent Status*\n\n✅ System is online and monitoring for Kubernetes incidents\n\nUse `@kube-agent help` for available commands.",
                    },
                }
            ],
        }

        self.web_client.chat_postMessage(**message)

    def _send_help_message(self, channel: str):
        """Send help message to channel"""
        message = {
            "channel": channel,
            "text": "Kube Multi-Agent Help",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🤖 *Kube Multi-Agent Help*\n\n*Available Commands:*\n• `@kube-agent status` - Check system status\n• `@kube-agent help` - Show this help message\n\n*Features:*\n• Automatic incident analysis\n• Remediation plan generation\n• Slack approval workflow\n• Kubernetes action execution",
                    },
                }
            ],
        }

        self.web_client.chat_postMessage(**message)
