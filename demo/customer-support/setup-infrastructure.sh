#!/bin/bash

# Setup AWS infrastructure for AgentCore agent (idempotent)
# Usage: ./setup-infrastructure.sh [role-name]

set -e

ROLE_NAME=${1:-"AgentCoreExecutionRole"}
POLICY_NAME="${ROLE_NAME}Policy"

echo "🏗️  Setting up AWS infrastructure for AgentCore agent..."

# Function to check if role exists
role_exists() {
    aws iam get-role --role-name "$1" >/dev/null 2>&1
}

# Function to check if policy exists
policy_exists() {
    local policy_arn="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/$1"
    aws iam get-policy --policy-arn "$policy_arn" >/dev/null 2>&1
}

# Check if role already exists
if role_exists "$ROLE_NAME"; then
    echo "✅ IAM role '$ROLE_NAME' already exists"
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
else
    echo "🔐 Creating IAM role: $ROLE_NAME"
    
    # Create trust policy - allows AgentCore service to assume this role
    cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        },
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create the role
    echo "📝 Creating IAM role..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://trust-policy.json \
        --description "Execution role for AgentCore agents"
    
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    rm -f trust-policy.json
fi

# Check if custom policy already exists
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

if policy_exists "$POLICY_NAME"; then
    echo "✅ IAM policy '$POLICY_NAME' already exists"
else
    echo "📋 Creating IAM policy: $POLICY_NAME"
    
    # Create permissions policy - what the agent can do
    cat > permissions-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:GetFoundationModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchCheckLayerAvailability"
            ],
            "Resource": "*"
        }
    ]
}
EOF

    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://permissions-policy.json \
        --description "Permissions for AgentCore agent execution" \
        --query 'Policy.Arn' \
        --output text)
    
    rm -f permissions-policy.json
fi

# Check if policy is attached to role
if aws iam list-attached-role-policies --role-name "$ROLE_NAME" --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN']" --output text | grep -q "$POLICY_ARN"; then
    echo "✅ Policy already attached to role"
else
    echo "🔗 Attaching policy to role..."
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$POLICY_ARN"
fi

# Enable Bedrock model access (idempotent)
echo "🤖 Ensuring Bedrock model access..."

# Enable Claude 3.5 Sonnet model access if not already enabled
aws bedrock put-model-invocation-logging-configuration \
    --logging-config cloudWatchConfig={logGroupName="/aws/bedrock/agentcore",roleArn="$ROLE_ARN"} \
    2>/dev/null || echo "⚠️  Bedrock logging config already set or not supported in region"

# Check if Claude 3.5 Sonnet is available
echo "🔍 Checking available Bedrock models..."
aws bedrock list-foundation-models \
    --by-provider anthropic \
    --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].{ModelId:modelId,ModelName:modelName}' \
    --output table 2>/dev/null || echo "⚠️  Could not list Bedrock models - check permissions"

echo ""
echo "✅ Infrastructure setup complete!"
echo ""
echo "🔗 Role ARN: $ROLE_ARN"
echo ""
echo "📝 Add this to your ../../.env file:"
echo "IAM_ROLE_ARN=$ROLE_ARN"
echo ""

# Get current region and construct console URL
CURRENT_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
CONSOLE_URL="https://console.aws.amazon.com/iam/home?region=${CURRENT_REGION}#/roles/${ROLE_NAME}"
echo "🌐 View role in AWS Console:"
echo "$CONSOLE_URL"
echo ""
echo "⏳ Note: It may take a few minutes for the role to be fully available."
echo ""
# Create user policy for AgentCore invocation
CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
USER_POLICY_NAME="AgentCoreUserPolicy"

echo "🔐 Setting up user permissions for AgentCore invocation..."
echo "👤 Current user: $CURRENT_USER"

# Create user policy for AgentCore operations
cat > user-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime",
        "bedrock-agentcore:ListAgentRuntimes",
        "bedrock-agentcore:DescribeAgentRuntime"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Check if user policy already exists
USER_POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${USER_POLICY_NAME}"
if policy_exists "$USER_POLICY_NAME"; then
    echo "✅ User policy '$USER_POLICY_NAME' already exists"
else
    echo "📋 Creating user policy: $USER_POLICY_NAME"
    aws iam create-policy \
        --policy-name "$USER_POLICY_NAME" \
        --policy-document file://user-policy.json \
        --description "Allows user to invoke AgentCore agents" \
        >/dev/null
fi

# Attach policy to current user
if aws iam list-attached-user-policies --user-name "$CURRENT_USER" --query "AttachedPolicies[?PolicyArn=='$USER_POLICY_ARN']" --output text | grep -q "$USER_POLICY_ARN"; then
    echo "✅ User policy already attached to $CURRENT_USER"
else
    echo "🔗 Attaching user policy to $CURRENT_USER..."
    aws iam attach-user-policy \
        --user-name "$CURRENT_USER" \
        --policy-arn "$USER_POLICY_ARN"
fi

rm -f user-policy.json
echo ""