# GitHub Development Assistant Agent

A personalized GitHub workflow assistant that integrates with AWS Bedrock AgentCore using OIDC authentication and GitHub's MCP server.

## Features

### 🔐 OIDC Authentication
- **Role-based access**: Different capabilities for developers, team leads, and admins
- **Team-aware**: Filters data based on user's team memberships
- **Personalized responses**: Greets users by name and provides relevant information

### 📋 Pull Request Management
- View open PRs across accessible repositories
- Get PR review status and assignment information
- Role-based PR actions (merge for team leads, view for developers)

### 🐛 Issue Tracking
- See issues assigned to the authenticated user
- Create new issues with automatic assignment
- Smart labeling and categorization

### 📊 Repository Insights
- View accessible repositories with key metrics
- Language distribution and activity stats
- Admin users get advanced analytics

### 🤖 MCP Integration
- Uses GitHub's hosted MCP server for reliable API access
- Reduces agent code complexity
- Leverages GitHub's maintained integrations

## Quick Start

### Prerequisites
- GitHub Personal Access Token with appropriate permissions
- OIDC provider configured
- AWS Bedrock AgentCore access

### Environment Variables
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
export OIDC_CLIENT_ID=your-oidc-client-id
export IAM_ROLE_ARN=arn:aws:iam::123456789012:role/AgentCoreExecutionRole
```

### Deploy to Bedrock
```bash
make deploy
```

### Test Locally
```bash
make run
```

## Usage Examples

### For Developers
```
User: "What PRs do I need to review?"
Agent: "Hi John! Here are your pending PR reviews:
        - aws-bedrock-a2a-proxy: 2 PRs waiting
        - #42: Add GitHub integration support (by developer1)"
```

### For Team Leads
```
User: "Show me team activity"
Agent: "Hi Sarah! As a team lead, here's your team overview:
        - 5 open PRs across 3 repositories
        - 3 issues need assignment
        - 2 PRs ready for merge approval"
```

### For Admins
```
User: "Repository statistics"
Agent: "Hi Alex! Admin view - Repository insights:
        - Total repositories: 25
        - Active contributors: 12
        - Security alerts: 2 (requires attention)"
```

## OIDC Integration

### Claims Mapping
The agent extracts user information from OIDC claims:

```json
{
  "preferred_username": "johndoe",
  "email": "john.doe@company.com", 
  "name": "John Doe",
  "groups": ["team-platform", "team-leads"],
  "role": "team_lead"
}
```

### Role Permissions
- **Developer**: Read repositories, issues, PRs; Create issues
- **Team Lead**: All developer permissions + PR reviews, merge, issue management
- **Admin**: All permissions + repository management, advanced analytics

## MCP Server Integration

This agent integrates with GitHub's hosted MCP server to:
- Reduce maintenance overhead
- Ensure API compatibility
- Leverage GitHub's rate limiting and caching
- Access advanced GitHub features

### MCP Tools Used
- `github-api`: Core GitHub API operations
- `repository-search`: Advanced repository queries
- `pull-request-tools`: PR management operations
- `issue-management`: Issue lifecycle operations

## Configuration

See `config.json` for detailed configuration options including:
- OIDC provider settings
- GitHub API configuration
- Role-based permissions
- Feature toggles
- Logging preferences

## Development

### Local Testing
```bash
# Install dependencies
make install

# Run tests
make test

# Run locally with mock data
make run
```

### Validation
```bash
# Validate configuration and code
make validate
```

## Security Considerations

1. **Token Security**: GitHub tokens are passed securely through environment variables
2. **OIDC Validation**: All requests validate OIDC tokens before processing
3. **Role Enforcement**: API calls are filtered based on user roles
4. **Audit Logging**: All actions are logged with user context
5. **Least Privilege**: Users only see data they have permission to access

## Troubleshooting

### Common Issues

**Agent not authenticating**
- Verify OIDC_CLIENT_ID is correctly set
- Check OIDC provider configuration
- Ensure user has required group memberships

**GitHub API errors**
- Verify GITHUB_TOKEN has necessary permissions
- Check rate limiting status
- Ensure repositories are accessible to the token

**Deployment failures**
- Verify IAM_ROLE_ARN has AgentCore permissions
- Check ECR_REPOSITORY_URL is accessible
- Ensure AWS credentials are configured

### Logs
```bash
# View agent logs
make logs

# Local debugging
PYTHONPATH=. python -c "import agent; agent.main()"
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure OIDC integration works correctly
5. Test with different user roles

## License

This agent is part of the AWS Bedrock AgentCore A2A Proxy project.