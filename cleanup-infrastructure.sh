#!/bin/bash
# Complete AWS Infrastructure Cleanup for aws-bedrock-agentcore
set -e

echo "🧹 Starting complete cleanup of aws-bedrock-agentcore infrastructure..."

# 1. Delete CloudWatch Log Groups
echo "🗂️  Deleting CloudWatch Log Groups..."
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/Bedrock_Customer_Support_Agent-IjyJ7O5PgN-DEFAULT" --region us-east-1 2>/dev/null || echo "   ⚠️  Log group not found"
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/Bedrock_Customer_Support_Agent-KBGaibBQNW-DEFAULT" --region us-east-1 2>/dev/null || echo "   ⚠️  Log group not found"
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/customer_support_agent-ATr2K3Evb8-DEFAULT" --region us-east-1 2>/dev/null || echo "   ⚠️  Log group not found"
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/customer_support_agent-CxSzRsAVex-DEFAULT" --region us-east-1 2>/dev/null || echo "   ⚠️  Log group not found"
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/customer_support_agent-wdbUjQGWCg-DEFAULT" --region us-east-1 2>/dev/null || echo "   ⚠️  Log group not found"

# 2. Delete AgentCore Agent Runtimes
echo "🤖 Deleting AgentCore agent runtimes..."
aws bedrock-agentcore delete-agent-runtime --agent-runtime-id "Bedrock_Customer_Support_Agent-IjyJ7O5PgN" --region us-east-1 2>/dev/null || echo "   ⚠️  Agent runtime not found"

# List and delete any additional agents
echo "🔍 Checking for additional agent runtimes..."
AGENTS=$(aws bedrock-agentcore list-agent-runtimes --region us-east-1 --query "agentRuntimeSummaries[].agentRuntimeId" --output text 2>/dev/null || echo "")
if [ -n "$AGENTS" ]; then
    for agent in $AGENTS; do
        echo "   Deleting agent: $agent"
        aws bedrock-agentcore delete-agent-runtime --agent-runtime-id "$agent" --region us-east-1 2>/dev/null || echo "   ⚠️  Failed to delete $agent"
    done
else
    echo "   ✅ No additional agents found"
fi

# 3. Delete ECR Repository
echo "📦 Deleting ECR repository..."
aws ecr delete-repository --repository-name "bedrock_agentcore-agent" --region us-east-1 --force 2>/dev/null || echo "   ⚠️  ECR repository not found"

# 4. Clean up IAM Resources
echo "🔐 Cleaning up IAM resources..."

# Detach policies from role first
aws iam detach-role-policy --role-name "AgentCoreExecutionRole" --policy-arn "arn:aws:iam::705383350627:policy/AgentCoreExecutionRolePolicy" 2>/dev/null || echo "   ⚠️  Policy already detached"

# Delete policies
aws iam delete-policy --policy-arn "arn:aws:iam::705383350627:policy/AgentCoreExecutionRolePolicy" 2>/dev/null || echo "   ⚠️  Policy not found"
aws iam delete-policy --policy-arn "arn:aws:iam::705383350627:policy/AgentCoreUserPolicy" 2>/dev/null || echo "   ⚠️  Policy not found"

# Delete role
aws iam delete-role --role-name "AgentCoreExecutionRole" 2>/dev/null || echo "   ⚠️  Role not found"

# 5. Clean up Bedrock logging
echo "📝 Cleaning up Bedrock logging configuration..."
aws bedrock delete-model-invocation-logging-configuration --region us-east-1 2>/dev/null || echo "   ⚠️  No Bedrock logging config found"

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "🔍 To verify cleanup, run these verification commands:"
echo ""
echo "# Check IAM resources"
echo "aws iam list-roles --query \"Roles[?contains(RoleName, 'AgentCore')]\""
echo "aws iam list-policies --scope Local --query \"Policies[?contains(PolicyName, 'AgentCore')]\""
echo ""
echo "# Check CloudWatch logs"
echo "aws logs describe-log-groups --log-group-name-prefix \"/aws/bedrock\" --region us-east-1"
echo ""
echo "# Check ECR repositories"  
echo "aws ecr describe-repositories --query \"repositories[?contains(repositoryName, 'bedrock')]\" --region us-east-1"
echo ""
echo "# Check AgentCore agents"
echo "aws bedrock-agentcore list-agent-runtimes --region us-east-1"
echo ""