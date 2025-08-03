#!/bin/bash

# Check required environment variables
: ${AWS_REGION:?'AWS_REGION is required for Bedrock AgentCore connection'}
: ${EXPOSE_HOST:?'EXPOSE_HOST is required for A2A URL generation'}
: ${EXPOSE_PORT:?'EXPOSE_PORT is required for A2A URL generation'}

# Check AWS credentials using same pattern
[ -n "$AWS_ACCESS_KEY_ID" ] || [ -n "$AWS_PROFILE" ] || [ -f ~/.aws/credentials ] || { echo "AWS credentials required. Set AWS_ACCESS_KEY_ID or AWS_PROFILE or configure ~/.aws/credentials" >&2; exit 1; }

echo "Environment check passed"