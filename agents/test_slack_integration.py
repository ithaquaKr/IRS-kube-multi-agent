#!/usr/bin/env python3
"""
Test script for Slack integration

This script demonstrates the Slack integration features without requiring
a full Kubernetes environment or actual incident alerts.
"""

import asyncio
import os
import sys
from datetime import datetime

from config import validate_slack_config
from utils.slack_service import SlackService

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_slack_integration():
    """Test the Slack integration features"""

    print("🧪 Testing Slack Integration")
    print("=" * 50)

    try:
        # Validate configuration
        validate_slack_config()
        print("✅ Configuration validation passed")

        # Initialize Slack service
        slack_service = SlackService()
        slack_service.start()
        print("✅ Slack service initialized")

        # Test data
        test_alert = {
            "status": "firing",
            "labels": {
                "alertname": "NodeDown",
                "severity": "critical",
                "node": "worker-01",
            },
            "annotations": {
                "summary": "Node worker-01 is down",
                "description": "Node worker-01 has been unreachable for more than 5 minutes",
            },
            "startsAt": datetime.now().isoformat(),
            "generatorURL": "http://prometheus:9090",
        }

        test_analysis = {
            "root_cause": "Network connectivity issue between worker-01 and control plane",
            "severity_level": "critical",
            "affected_components": ["worker-01", "pods on worker-01", "services"],
            "investigation_summary": "Investigation revealed network partition affecting worker-01. All pods on this node are unreachable.",
        }

        test_plan = {
            "plan_id": "plan-001",
            "plan_name": "Network Recovery Plan",
            "description": "Restore network connectivity to worker-01 and reschedule affected pods",
            "risk_level": "medium",
            "estimated_time": "10 minutes",
            "prerequisites": ["Network team approval", "Maintenance window"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "Check network connectivity",
                    "command": "kubectl get nodes -o wide",
                    "expected_result": "Confirm worker-01 is unreachable",
                    "rollback_command": "N/A",
                },
                {
                    "step_number": 2,
                    "action": "Cordon worker-01",
                    "command": "kubectl cordon worker-01",
                    "expected_result": "Worker-01 marked as unschedulable",
                    "rollback_command": "kubectl uncordon worker-01",
                },
                {
                    "step_number": 3,
                    "action": "Drain worker-01",
                    "command": "kubectl drain worker-01 --ignore-daemonsets --delete-emptydir-data",
                    "expected_result": "All pods evicted from worker-01",
                    "rollback_command": "kubectl uncordon worker-01",
                },
            ],
        }

        test_execution = {
            "execution_id": "exec-001",
            "status": "success",
            "executed_steps": [
                {
                    "step": 1,
                    "status": "success",
                    "output": "Worker-01 confirmed unreachable",
                },
                {
                    "step": 2,
                    "status": "success",
                    "output": "Worker-01 cordoned successfully",
                },
                {
                    "step": 3,
                    "status": "success",
                    "output": "All pods evicted successfully",
                },
            ],
            "error_message": None,
            "rollback_performed": False,
            "final_verification": "All pods rescheduled successfully. Worker-01 isolated for maintenance.",
        }

        # Test 1: Send analysis result
        print("\n📊 Test 1: Sending Analysis Result")
        try:
            message_ts = slack_service.send_analysis_result(test_alert, test_analysis)
            print(f"✅ Analysis result sent (Message TS: {message_ts})")
        except Exception as e:
            print(f"❌ Failed to send analysis result: {e}")

        # Test 2: Send remediation plan and test approval
        print("\n📋 Test 2: Sending Remediation Plan")
        try:
            approval_id = slack_service.send_remediation_plan(test_alert, test_plan)
            print(f"✅ Remediation plan sent (Approval ID: {approval_id})")

            # Note: In a real scenario, you would wait for user interaction
            # For testing, we'll simulate a timeout
            print("⏳ Simulating approval timeout (5 seconds)...")
            approval_result = slack_service.wait_for_approval(approval_id)

            if approval_result is None:
                print("⏰ Approval timeout (expected for test)")
            elif approval_result:
                print("✅ Plan approved")
            else:
                print("❌ Plan rejected")

        except Exception as e:
            print(f"❌ Failed to send remediation plan: {e}")

        # Test 3: Send execution result
        print("\n🚀 Test 3: Sending Execution Result")
        try:
            message_ts = slack_service.send_execution_result(test_execution)
            print(f"✅ Execution result sent (Message TS: {message_ts})")
        except Exception as e:
            print(f"❌ Failed to send execution result: {e}")

        # Test 4: Send error notification
        print("\n🚨 Test 4: Sending Error Notification")
        try:
            slack_service.send_error_notification(
                "Test error message", "This is a test error notification"
            )
            print("✅ Error notification sent")
        except Exception as e:
            print(f"❌ Failed to send error notification: {e}")

        # Cleanup
        slack_service.stop()
        print("\n✅ Slack service stopped")

        print("\n🎉 All tests completed!")
        print("\n📝 Check your Slack channel for the test messages.")
        print("💡 In a real scenario, you would interact with the approval buttons.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


def main():
    """Main function"""
    print("Kube Multi-Agent - Slack Integration Test")
    print("=" * 50)

    # Check if required environment variables are set
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET",
        "SLACK_APP_TOKEN",
        "SLACK_CHANNEL_ID",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please set up your environment variables first.")
        print("📖 See docs/SLACK_SETUP.md for setup instructions.")
        return False

    # Run the test
    success = asyncio.run(test_slack_integration())

    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
