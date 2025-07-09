# Kubernetes Multi-Agent Incident Response System

A sophisticated multi-agent system for automated Kubernetes incident response with Slack integration for notifications and approvals.

## Features

### 🤖 Multi-Agent Architecture
- **Analyst Agent**: Performs root cause analysis using Kubernetes diagnostics
- **Planner Agent**: Generates safe remediation plans with rollback procedures
- **Executor Agent**: Executes approved plans with real-time monitoring
- **Supervisor Agent**: Orchestrates the entire incident response workflow

### 📱 Slack Integration
- **Real-time Notifications**: Get instant alerts about incident analysis and remediation plans
- **Approval Workflow**: Interactive buttons for approving/rejecting remediation plans
- **Status Updates**: Track execution progress and results
- **Error Notifications**: Automatic error reporting with context
- **Interactive Commands**: Use `@kube-agent status` and `@kube-agent help`

### 🔧 Kubernetes Integration
- **MCP Server Integration**: Real-time cluster diagnostics via kubectl-ai
- **Live Cluster State**: Access to current Kubernetes resources and events
- **Safe Execution**: Dry-run validation and rollback procedures
- **Comprehensive Monitoring**: Pod logs, events, metrics, and resource status

## Quick Start

### Prerequisites
- Python 3.13+
- Kubernetes cluster access
- Slack workspace (for notifications)
- Google Gemini API key
- Tavily API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IRS-kube-multi-agent
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables (see [Slack Setup Guide](docs/SLACK_SETUP.md)):
```bash
cp agents/.env.example agents/.env
# Edit agents/.env with your configuration
```

4. Start the server:
```bash
cd agents
python main.py serve
```

### Testing

Test with a sample alert:
```bash
python main.py examples/alerts/node-down.json
```

## Slack Integration Setup

The system includes comprehensive Slack integration for:
- Sending analysis results to Slack channels
- Requesting approval for remediation plans
- Providing execution status updates
- Error notifications

See the [Slack Setup Guide](docs/SLACK_SETUP.md) for detailed configuration instructions.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alertmanager  │───▶│  Multi-Agent    │───▶│   Slack Bot     │
│   Webhook       │    │   System        │    │   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Kubernetes    │
                       │   Cluster       │
                       └─────────────────┘
```

### Agent Workflow

1. **Alert Reception**: Alertmanager webhook triggers the system
2. **Analysis**: Analyst agent investigates the incident
3. **Planning**: Planner agent creates remediation plan
4. **Slack Notification**: Analysis and plan sent to Slack
5. **Approval**: Team reviews and approves/rejects plan
6. **Execution**: Executor agent implements approved plan
7. **Verification**: System verifies remediation success

## Configuration

### Environment Variables

Required environment variables:
- `SLACK_BOT_TOKEN`: Slack bot user OAuth token
- `SLACK_SIGNING_SECRET`: Slack app signing secret
- `SLACK_APP_TOKEN`: Slack app-level token for Socket Mode
- `SLACK_CHANNEL_ID`: Target Slack channel for notifications
- `GOOGLE_API_KEY`: Google Gemini API key
- `TAVILY_API_KEY`: Tavily search API key

### Slack Configuration

The Slack integration supports:
- **Approval Timeouts**: Configurable timeout for plan approvals
- **Channel Targeting**: Send notifications to specific channels
- **Interactive Elements**: Buttons for approve/reject/view details
- **Modal Views**: Detailed plan information in popup modals

## API Endpoints

- `POST /webhook`: Alertmanager webhook endpoint
- `POST /slack/events`: Slack events endpoint for interactions

## Development

### Project Structure
```
agents/
├── agents/           # Agent implementations
├── utils/           # Utilities and tools
├── prompts/         # Agent prompts
├── llms/           # LLM integrations
├── models.py       # Data models
├── config.py       # Configuration
└── main.py         # Main application
```

### Adding New Agents

1. Create agent class in `agents/agents/`
2. Define prompts in `prompts/`
3. Add parser in `utils/parsers.py`
4. Integrate in `main.py`

### Extending Slack Integration

The `SlackService` class provides extensible methods for:
- Custom notifications
- Approval workflows
- Event handling
- Error reporting

## Security Considerations

- All sensitive data stored in environment variables
- Slack signature verification for webhook security
- Approval workflows for critical Kubernetes actions
- Comprehensive audit logging
- Rollback procedures for all remediation actions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
