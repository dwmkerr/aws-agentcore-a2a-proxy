#!/usr/bin/env python3
"""
GitHub Development Assistant Agent

This agent helps developers with GitHub workflows using MCP integration.
Provides personalized, role-aware assistance for:
- PR management and reviews
- Issue tracking and assignment
- Repository insights and metrics
- CI/CD pipeline monitoring

Integrates with:
- GitHub's hosted MCP server for API calls
- OIDC for user authentication and role-based access
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GitHubUser:
    """Represents an authenticated GitHub user with OIDC claims"""
    username: str
    email: str
    name: str
    role: str = "developer"  # developer, team_lead, admin
    teams: List[str] = None
    repositories: List[str] = None
    
    def __post_init__(self):
        if self.teams is None:
            self.teams = []
        if self.repositories is None:
            self.repositories = []

class GitHubMCPClient:
    """Client for interacting with GitHub's hosted MCP server"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Dev-Assistant-Agent"
        }
    
    async def get_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """Get repositories accessible to the user"""
        # This would integrate with GitHub's MCP server
        # For now, returning mock data
        return [
            {
                "name": "aws-bedrock-a2a-proxy",
                "full_name": f"{username}/aws-bedrock-a2a-proxy",
                "private": False,
                "description": "A2A proxy for AWS Bedrock AgentCore",
                "language": "Python",
                "stargazers_count": 15,
                "open_issues_count": 3
            }
        ]
    
    async def get_pull_requests(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Get pull requests for a repository"""
        return [
            {
                "number": 42,
                "title": "Add GitHub integration support",
                "state": "open",
                "user": {"login": "developer1"},
                "created_at": "2025-01-26T15:30:00Z",
                "draft": False,
                "requested_reviewers": [{"login": "team_lead"}]
            }
        ]
    
    async def get_issues(self, repo: str, assignee: str = None) -> List[Dict[str, Any]]:
        """Get issues for a repository"""
        return [
            {
                "number": 123,
                "title": "Implement OIDC authentication",
                "state": "open",
                "assignee": {"login": assignee} if assignee else None,
                "labels": [{"name": "enhancement"}, {"name": "security"}],
                "created_at": "2025-01-25T10:00:00Z"
            }
        ]
    
    async def create_issue(self, repo: str, title: str, body: str, assignee: str = None) -> Dict[str, Any]:
        """Create a new issue"""
        return {
            "number": 124,
            "title": title,
            "body": body,
            "state": "open",
            "assignee": {"login": assignee} if assignee else None,
            "created_at": datetime.now().isoformat()
        }

class GitHubDevelopmentAssistant:
    """Main agent class for GitHub development assistance"""
    
    def __init__(self, github_token: str):
        self.mcp_client = GitHubMCPClient(github_token)
        self.current_user: Optional[GitHubUser] = None
    
    def authenticate_user(self, oidc_claims: Dict[str, Any]) -> GitHubUser:
        """Authenticate user from OIDC claims and extract GitHub info"""
        # Extract user info from OIDC claims
        username = oidc_claims.get("preferred_username", "unknown")
        email = oidc_claims.get("email", "")
        name = oidc_claims.get("name", username)
        
        # Extract role from groups or custom claims
        groups = oidc_claims.get("groups", [])
        role = "developer"
        if "team-leads" in groups:
            role = "team_lead"
        elif "admins" in groups:
            role = "admin"
        
        # Extract team memberships
        teams = [group for group in groups if group.startswith("team-")]
        
        self.current_user = GitHubUser(
            username=username,
            email=email,
            name=name,
            role=role,
            teams=teams
        )
        
        logger.info(f"Authenticated user: {name} ({username}) with role: {role}")
        return self.current_user
    
    async def handle_request(self, prompt: str, oidc_claims: Dict[str, Any] = None) -> str:
        """Main entry point for handling user requests"""
        
        # Authenticate user if OIDC claims provided
        if oidc_claims:
            self.authenticate_user(oidc_claims)
        
        # Parse user intent and route to appropriate handler
        prompt_lower = prompt.lower()
        
        if "pull request" in prompt_lower or "pr" in prompt_lower:
            return await self.handle_pull_request_query(prompt)
        elif "issue" in prompt_lower:
            return await self.handle_issue_query(prompt)
        elif "repository" in prompt_lower or "repo" in prompt_lower:
            return await self.handle_repository_query(prompt)
        elif "create" in prompt_lower:
            return await self.handle_creation_request(prompt)
        else:
            return await self.handle_general_query(prompt)
    
    async def handle_pull_request_query(self, prompt: str) -> str:
        """Handle PR-related queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub data."
        
        # Get user's repositories
        repos = await self.mcp_client.get_user_repositories(self.current_user.username)
        
        pr_summary = []
        for repo in repos[:3]:  # Limit to first 3 repos
            prs = await self.mcp_client.get_pull_requests(repo["name"])
            pr_summary.append(f"**{repo['name']}**: {len(prs)} open PRs")
            
            for pr in prs[:2]:  # Show first 2 PRs per repo
                pr_summary.append(f"  - #{pr['number']}: {pr['title']} (by {pr['user']['login']})")
        
        user_greeting = f"Hi {self.current_user.name}!" if self.current_user.name != self.current_user.username else f"Hi {self.current_user.username}!"
        
        return f"{user_greeting} Here's your PR overview:\n\n" + "\n".join(pr_summary)
    
    async def handle_issue_query(self, prompt: str) -> str:
        """Handle issue-related queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub data."
        
        repos = await self.mcp_client.get_user_repositories(self.current_user.username)
        
        issue_summary = []
        for repo in repos[:2]:
            issues = await self.mcp_client.get_issues(repo["name"], self.current_user.username)
            assigned_issues = [issue for issue in issues if issue.get("assignee")]
            
            issue_summary.append(f"**{repo['name']}**: {len(assigned_issues)} issues assigned to you")
            
            for issue in assigned_issues[:3]:
                labels = ", ".join([label["name"] for label in issue.get("labels", [])])
                issue_summary.append(f"  - #{issue['number']}: {issue['title']} [{labels}]")
        
        return f"Your assigned issues:\n\n" + "\n".join(issue_summary)
    
    async def handle_repository_query(self, prompt: str) -> str:
        """Handle repository-related queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub data."
        
        repos = await self.mcp_client.get_user_repositories(self.current_user.username)
        
        repo_summary = []
        for repo in repos[:5]:
            repo_summary.append(
                f"**{repo['name']}** ({repo['language']}): "
                f"⭐{repo['stargazers_count']} | 🐛{repo['open_issues_count']} open issues"
            )
        
        role_info = ""
        if self.current_user.role == "team_lead":
            role_info = "\n\n*As a team lead, you can access advanced repository analytics.*"
        elif self.current_user.role == "admin":
            role_info = "\n\n*As an admin, you have full repository management access.*"
        
        return f"Your accessible repositories:\n\n" + "\n".join(repo_summary) + role_info
    
    async def handle_creation_request(self, prompt: str) -> str:
        """Handle requests to create issues, PRs, etc."""
        if not self.current_user:
            return "Please authenticate to create GitHub resources."
        
        if "issue" in prompt.lower():
            # Extract issue details from prompt (simplified)
            title = "New issue created via GitHub Assistant"
            body = f"Created by: {self.current_user.name}\nOriginal request: {prompt}"
            
            # For demo, use first repo
            repos = await self.mcp_client.get_user_repositories(self.current_user.username)
            if repos:
                issue = await self.mcp_client.create_issue(
                    repos[0]["name"], 
                    title, 
                    body,
                    self.current_user.username
                )
                return f"✅ Created issue #{issue['number']}: {issue['title']} in {repos[0]['name']}"
            else:
                return "No accessible repositories found for issue creation."
        
        return "I can help you create issues. Try: 'Create an issue for implementing dark mode'"
    
    async def handle_general_query(self, prompt: str) -> str:
        """Handle general GitHub-related queries"""
        if not self.current_user:
            return """Hello! I'm your GitHub Development Assistant. 

I can help you with:
- 📋 Pull request reviews and status
- 🐛 Issue tracking and assignment  
- 📊 Repository insights and metrics
- 🔧 Creating issues and managing workflows

Please authenticate with OIDC to access your GitHub data."""
        
        return f"""Hello {self.current_user.name}! I'm your GitHub Development Assistant.

I can help you with:
- 📋 **Pull Requests**: "Show me my open PRs" or "What PRs need review?"
- 🐛 **Issues**: "What issues are assigned to me?" or "Create an issue for bug fix"
- 📊 **Repositories**: "Show my repositories" or "Repository statistics"

Your current role: **{self.current_user.role.replace('_', ' ').title()}**
Teams: {', '.join(self.current_user.teams) if self.current_user.teams else 'None'}

What would you like to do?"""

# Agent entry point for AWS Bedrock AgentCore
async def main():
    """Main entry point when running as standalone script"""
    # This would be called by Bedrock AgentCore runtime
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable required")
        return
    
    assistant = GitHubDevelopmentAssistant(github_token)
    
    # Example usage with mock OIDC claims
    mock_oidc_claims = {
        "preferred_username": "johndoe",
        "email": "john.doe@company.com",
        "name": "John Doe",
        "groups": ["team-platform", "team-leads"]
    }
    
    # Test queries
    test_queries = [
        "Hello, what can you help me with?",
        "Show me my pull requests",
        "What issues are assigned to me?",
        "Show my repositories",
        "Create an issue for implementing OIDC"
    ]
    
    for query in test_queries:
        print(f"\n🤖 User: {query}")
        response = await assistant.handle_request(query, mock_oidc_claims)
        print(f"🤖 Assistant: {response}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main())