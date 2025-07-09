# Slack Integration Setup

This document explains how to set up Slack integration for the kube-multi-agent system.

## Prerequisites

1. A Slack workspace where you have admin permissions
2. Python 3.13+ with the required dependencies installed

## Slack App Setup

### 1. Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter app name (e.g., "Kube Multi-Agent")
5. Select your workspace

### 2. Configure Bot Token Scopes

1. Go to "OAuth & Permissions" in the left sidebar
2. Under "Scopes" > "Bot Token Scopes", add the following:
   - `chat:write` - Send messages to channels
   - `chat:write.public` - Send messages to public channels
   - `channels:read` - View basic channel info
   - `app_mentions:read` - Read mentions of your app
   - `im:read` - Read direct messages
   - `im:write` - Send direct messages

### 3. Install App to Workspace

1. Go to "Install App" in the left sidebar
2. Click "Install to Workspace"
3. Authorize the app
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

### 4. Configure Socket Mode

1. Go to "Socket Mode" in the left sidebar
2. Enable Socket Mode
3. Generate an App-Level Token (starts with `xapp-`)
4. Copy the App-Level Token

### 5. Configure Event Subscriptions

1. Go to "Event Subscriptions" in the left sidebar
2. Enable Events
3. Add the following Bot Events:
   - `app_mention` - When someone mentions your app
   - `message.im` - Direct messages to your app
   - `app_home_opened` - When someone opens your app's home

### 6. Configure Interactive Components

1. Go to "Interactivity & Shortcuts" in the left sidebar
2. Enable Interactivity
3. Set Request URL to: `https://your-domain.com/slack/events`

### 7. Get Signing Secret

1. Go to "Basic Information" in the left sidebar
2. Copy the "Signing Secret"

## Environment Configuration

Create a `.env` file in the `agents` directory with the following variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_CHANNEL_ID=#incident-response
SLACK_APPROVAL_TIMEOUT=300

# LLM Configuration
GOOGLE_API_KEY=your-google-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here

# Kubernetes Configuration
KUBECONFIG_PATH=/path/to/your/kubeconfig

# Server Configuration
HOST=0.0.0.0
PORT=3000
```

## Invite Bot to Channel

1. In your Slack workspace, go to the channel where you want the bot to post
2. Type `/invite @your-bot-name` to invite the bot to the channel

## Testing the Integration

1. Start the server:
   ```bash
   python main.py serve
   ```

2. Test with a sample alert:
   ```bash
   python main.py examples/alerts/node-down.json
   ```

3. Check your Slack channel for:
   - Analysis results
   - Remediation plans with approval buttons
   - Execution results

## Features

### Analysis Results
- Automatically sent to Slack when analysis is complete
- Includes root cause, severity, affected components, and investigation summary

### Remediation Plans
- Sent to Slack with approval workflow
- Interactive buttons for Approve/Reject/View Details
- Configurable timeout for approval (default: 5 minutes)
- Detailed plan information available in modal view

### Execution Results
- Sent to Slack when plan execution is complete
- Includes status, rollback information, and final verification

### Error Notifications
- Automatic error notifications sent to Slack
- Includes error context and timestamp

### Interactive Commands
- `@kube-agent status` - Check system status
- `@kube-agent help` - Show help information

## Troubleshooting

### Common Issues

1. **Bot not posting messages**
   - Check bot token permissions
   - Ensure bot is invited to the channel
   - Verify channel ID format (should start with #)

2. **Button interactions not working**
   - Check Socket Mode is enabled
   - Verify App-Level Token is correct
   - Ensure interactive components are configured

3. **Signature verification errors**
   - Verify signing secret is correct
   - Check request headers are properly set

4. **Approval timeout issues**
   - Check approval timeout configuration
   - Ensure event handlers are properly registered

### Debug Mode

Enable debug logging by setting the `debug` parameter to `True` when initializing agents:

```python
analyst_agent = AnalystAgent(llm, tools=tools, debug=True)
```

## Security Considerations

1. **Token Security**
   - Never commit tokens to version control
   - Use environment variables for all sensitive data
   - Rotate tokens regularly

2. **Channel Access**
   - Only invite the bot to necessary channels
   - Use private channels for sensitive information
   - Review bot permissions regularly

3. **Approval Workflow**
   - Set appropriate approval timeouts
   - Monitor approval patterns
   - Consider implementing approval hierarchies for critical actions

## Advanced Configuration

### Custom Approval Workflows

You can extend the approval system by modifying the `SlackService` class:

```python
# Add custom approval logic
async def custom_approval_handler(self, approval_id: str, user_id: str):
    # Check user permissions
    # Implement approval hierarchies
    # Add audit logging
    pass
```

### Custom Notifications

Extend the notification system by adding new methods to `SlackService`:

```python
async def send_custom_notification(self, message: str, level: str = "info"):
    # Custom notification logic
    pass
```
