#!/usr/bin/env python3
"""
GitHub Development Assistant Agent

This agent helps developers with GitHub workflows using GitHub's hosted MCP server.
Provides personalized, role-aware assistance for:
- PR management and reviews
- Issue tracking and assignment
- Repository insights and metrics
- CI/CD pipeline monitoring

Integrates with:
- GitHub's hosted MCP server (https://api.githubcopilot.com/mcp/)
- OIDC for user authentication and role-based access
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx

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
    
    def __init__(self, github_token: str = None):
        self.github_token = github_token
        self.mcp_url = "https://api.githubcopilot.com/mcp/"
        self.headers = {
            "Content-Type": "application/json"
        }
        if github_token:
            self.headers["Authorization"] = f"Bearer {github_token}"
    
    def update_token(self, github_token: str):
        """Update the GitHub token for API calls"""
        self.github_token = github_token
        self.headers["Authorization"] = f"Bearer {github_token}"
    
    async def _make_mcp_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to GitHub's hosted MCP server"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": f"tools/call",
            "params": {
                "name": method,
                "arguments": params or {}
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.mcp_url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    logger.error(f"MCP error: {data['error']}")
                    return {}
                
                return data.get("result", {}).get("content", [{}])[0].get("data", {})
            except Exception as e:
                logger.error(f"MCP request failed: {e}")
                return {}
    
    async def get_me(self) -> Dict[str, Any]:
        """Get current user profile"""
        return await self._make_mcp_request("get_me")
    
    async def search_repositories(self, query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        """Search repositories accessible to the user"""
        result = await self._make_mcp_request("search_repositories", {
            "query": query,
            "perPage": per_page
        })
        return result.get("items", [])
    
    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Get pull requests for a repository"""
        return await self._make_mcp_request("list_pull_requests", {
            "owner": owner,
            "repo": repo,
            "state": state
        })
    
    async def list_issues(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Get issues for a repository"""
        return await self._make_mcp_request("list_issues", {
            "owner": owner,
            "repo": repo,
            "state": state
        })
    
    async def create_issue(self, owner: str, repo: str, title: str, body: str, assignees: List[str] = None) -> Dict[str, Any]:
        """Create a new issue"""
        params = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body
        }
        if assignees:
            params["assignees"] = assignees
            
        return await self._make_mcp_request("create_issue", params)
    
    async def get_notifications(self, participating: bool = True) -> List[Dict[str, Any]]:
        """Get user's GitHub notifications"""
        filter_type = "participating" if participating else "all"
        return await self._make_mcp_request("list_notifications", {
            "filter": filter_type
        })
    
    async def list_workflow_runs(self, owner: str, repo: str, workflow_id: str = None) -> List[Dict[str, Any]]:
        """Get workflow runs for a repository"""
        if workflow_id:
            return await self._make_mcp_request("list_workflow_runs", {
                "owner": owner,
                "repo": repo,
                "workflow_id": workflow_id
            })
        else:
            # Get all workflows first, then runs for each
            workflows = await self._make_mcp_request("list_workflows", {
                "owner": owner,
                "repo": repo
            })
            
            all_runs = []
            for workflow in workflows.get("workflows", [])[:3]:  # Limit to first 3 workflows
                runs = await self._make_mcp_request("list_workflow_runs", {
                    "owner": owner,
                    "repo": repo,
                    "workflow_id": workflow["id"]
                })
                all_runs.extend(runs.get("workflow_runs", [])[:5])  # Limit runs per workflow
            
            return all_runs

class GitHubDevelopmentAssistant:
    """Main agent class for GitHub development assistance"""
    
    def __init__(self):
        self.mcp_client = GitHubMCPClient()
        self.current_user: Optional[GitHubUser] = None
    
    def authenticate_user(self, oidc_claims: Dict[str, Any]) -> GitHubUser:
        """Authenticate user from OIDC claims and extract GitHub info"""
        # Extract user info from OIDC claims
        username = oidc_claims.get("preferred_username", "unknown")
        email = oidc_claims.get("email", "")
        name = oidc_claims.get("name", username)
        
        # Extract GitHub access token from OIDC claims
        # This could be in different claim fields depending on OIDC provider configuration
        github_token = (
            oidc_claims.get("github_token") or  # Custom claim
            oidc_claims.get("access_token") or  # Standard OAuth claim
            oidc_claims.get("token") or         # Alternative claim name
            os.getenv("GITHUB_TOKEN")           # Fallback to env var for testing
        )
        
        if not github_token:
            logger.warning("No GitHub token found in OIDC claims or environment")
            # Continue without token - agent will handle gracefully
        else:
            # Update MCP client with user's GitHub token
            self.mcp_client.update_token(github_token)
            logger.info(f"Updated GitHub token for user: {username}")
        
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
        elif "notification" in prompt_lower:
            return await self.handle_notifications_query(prompt)
        elif "workflow" in prompt_lower or "ci" in prompt_lower or "build" in prompt_lower:
            return await self.handle_workflow_query(prompt)
        elif "create" in prompt_lower:
            return await self.handle_creation_request(prompt)
        else:
            return await self.handle_general_query(prompt)
    
    async def handle_pull_request_query(self, prompt: str) -> str:
        """Handle PR-related queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub data."
        
        if not self.mcp_client.github_token:
            return f"Hi {self.current_user.name}! I need your GitHub access token to fetch your pull requests. Please ensure your OIDC provider includes GitHub token in the claims."
        
        # Search for user's repositories (showing recent activity)
        repos = await self.mcp_client.search_repositories(f"user:{self.current_user.username}")
        
        pr_summary = []
        total_prs = 0
        
        for repo in repos[:3]:  # Limit to first 3 repos
            repo_name = repo["name"]
            owner = repo["owner"]["login"]
            
            # Get PRs for this repository
            prs = await self.mcp_client.list_pull_requests(owner, repo_name)
            prs_list = prs.get("pull_requests") if isinstance(prs, dict) else prs
            
            if prs_list:
                total_prs += len(prs_list)
                pr_summary.append(f"**{repo_name}**: {len(prs_list)} open PRs")
                
                for pr in prs_list[:2]:  # Show first 2 PRs per repo
                    pr_summary.append(f"  - #{pr['number']}: {pr['title']} (by {pr['user']['login']})")
        
        user_greeting = f"Hi {self.current_user.name}!" if self.current_user.name != self.current_user.username else f"Hi {self.current_user.username}!"
        
        if total_prs == 0:
            return f"{user_greeting} You have no open pull requests in your repositories."
        
        return f"{user_greeting} Here's your PR overview ({total_prs} total):\n\n" + "\n".join(pr_summary)
    
    async def handle_issue_query(self, prompt: str) -> str:
        """Handle issue-related queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub data."
        
        if not self.mcp_client.github_token:
            return f"Hi {self.current_user.name}! I need your GitHub access token to fetch your issues. Please ensure your OIDC provider includes GitHub token in the claims."
        
        # Search for user's repositories  
        repos = await self.mcp_client.search_repositories(f"user:{self.current_user.username}")
        
        issue_summary = []
        total_assigned = 0
        
        for repo in repos[:3]:  # Limit to first 3 repos
            repo_name = repo["name"]
            owner = repo["owner"]["login"]
            
            # Get all issues for this repository
            issues = await self.mcp_client.list_issues(owner, repo_name)
            issues_list = issues.get("issues") if isinstance(issues, dict) else issues
            
            # Filter for issues assigned to current user
            assigned_issues = [
                issue for issue in (issues_list or []) 
                if issue.get("assignee") and issue["assignee"]["login"] == self.current_user.username
            ]
            
            if assigned_issues:
                total_assigned += len(assigned_issues)
                issue_summary.append(f"**{repo_name}**: {len(assigned_issues)} issues assigned to you")
                
                for issue in assigned_issues[:3]:  # Show first 3 issues per repo
                    labels = ", ".join([label["name"] for label in issue.get("labels", [])])
                    issue_summary.append(f"  - #{issue['number']}: {issue['title']} [{labels}]")
        
        if total_assigned == 0:
            return "You have no issues assigned to you in your repositories."
        
        return f"Your assigned issues ({total_assigned} total):\n\n" + "\n".join(issue_summary)
    
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
    
    async def handle_notifications_query(self, prompt: str) -> str:
        """Handle GitHub notifications queries"""
        if not self.current_user:
            return "Please authenticate to access GitHub notifications."
        
        notifications = await self.mcp_client.get_notifications(participating=True)
        notifications_list = notifications.get("notifications") if isinstance(notifications, dict) else notifications
        
        if not notifications_list:
            return "🔔 No new notifications! You're all caught up."
        
        notification_summary = []
        for notification in (notifications_list or [])[:10]:  # Show first 10 notifications
            subject = notification.get("subject", {})
            repo = notification.get("repository", {})
            
            notification_summary.append(
                f"📌 **{subject.get('title', 'Unknown')}** in {repo.get('full_name', 'Unknown repo')}"
            )
        
        role_context = ""
        if self.current_user.role == "team_lead":
            role_context = "\n\n*As a team lead, you might want to prioritize PR reviews and issue assignments.*"
        
        return f"🔔 Your recent notifications ({len(notifications_list)} total):\n\n" + "\n".join(notification_summary) + role_context
    
    async def handle_workflow_query(self, prompt: str) -> str:
        """Handle CI/CD workflow queries"""
        if not self.current_user:
            return "Please authenticate to access workflow data."
        
        # Search for user's repositories
        repos = await self.mcp_client.search_repositories(f"user:{self.current_user.username}")
        
        workflow_summary = []
        
        for repo in repos[:2]:  # Limit to first 2 repos for workflow data
            repo_name = repo["name"] 
            owner = repo["owner"]["login"]
            
            # Get recent workflow runs
            workflow_runs = await self.mcp_client.list_workflow_runs(owner, repo_name)
            
            if workflow_runs:
                recent_runs = workflow_runs[:3]  # Show 3 most recent runs
                workflow_summary.append(f"**{repo_name}** CI/CD:")
                
                for run in recent_runs:
                    status_emoji = "✅" if run.get("conclusion") == "success" else "❌" if run.get("conclusion") == "failure" else "🟡"
                    workflow_summary.append(f"  {status_emoji} {run.get('name', 'Workflow')}: {run.get('conclusion', 'running')}")
        
        if not workflow_summary:
            return "No recent workflow activity found in your repositories."
        
        role_context = ""
        if self.current_user.role in ["team_lead", "admin"]:
            role_context = "\n\n*Use 'rerun failed workflows' to restart failed builds.*"
        
        return f"🔧 Recent CI/CD activity:\n\n" + "\n".join(workflow_summary) + role_context
    
    async def handle_creation_request(self, prompt: str) -> str:
        """Handle requests to create issues, PRs, etc."""
        if not self.current_user:
            return "Please authenticate to create GitHub resources."
        
        if "issue" in prompt.lower():
            # Extract issue details from prompt (simplified)
            title = "New issue created via GitHub Assistant"
            body = f"Created by: {self.current_user.name}\nOriginal request: {prompt}\n\nThis issue was created automatically via the GitHub Development Assistant."
            
            # Get user's repositories
            repos = await self.mcp_client.search_repositories(f"user:{self.current_user.username}")
            
            if repos:
                repo = repos[0]  # Use first repository
                repo_name = repo["name"]
                owner = repo["owner"]["login"]
                
                # Create the issue
                issue = await self.mcp_client.create_issue(
                    owner,
                    repo_name,
                    title, 
                    body,
                    [self.current_user.username]  # Assign to current user
                )
                
                if issue and issue.get("number"):
                    return f"✅ Created issue #{issue['number']}: {issue['title']} in {owner}/{repo_name}\n\nAssigned to: {self.current_user.username}"
                else:
                    return f"❌ Failed to create issue in {owner}/{repo_name}. Check your permissions."
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
- 🔔 **Notifications**: "Check my notifications" or "What needs my attention?"
- 🔧 **CI/CD**: "Show workflow status" or "Check build failures"

**Powered by GitHub's MCP Server** - Real-time access to all your GitHub data!

Your current role: **{self.current_user.role.replace('_', ' ').title()}**
Teams: {', '.join(self.current_user.teams) if self.current_user.teams else 'None'}

What would you like to do?"""

# Agent entry point for AWS Bedrock AgentCore
async def main():
    """Main entry point when running as standalone script"""
    # This would be called by Bedrock AgentCore runtime
    assistant = GitHubDevelopmentAssistant()
    
    # Example usage with mock OIDC claims (includes GitHub token from env for testing)
    mock_oidc_claims = {
        "preferred_username": "johndoe",
        "email": "john.doe@company.com",
        "name": "John Doe",
        "groups": ["team-platform", "team-leads"],
        "github_token": os.getenv("GITHUB_TOKEN")  # For testing - normally comes from OIDC provider
    }
    
    # Test queries showcasing GitHub MCP server integration
    test_queries = [
        "Hello, what can you help me with?",
        "Show me my pull requests",
        "What issues are assigned to me?",
        "Check my notifications",
        "Show workflow status",
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