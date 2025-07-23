# Customer Support Agent

AgentCore sample that deploys a customer support assistant capable of:
- Looking up customers by email
- Retrieving order information
- Providing product knowledge base answers
- Performing calculations and getting current time

## Usage

Set up your environment in `../../.env`:
```bash
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_REGION=us-east-1
IAM_ROLE_ARN=arn:aws:iam::123456789012:role/AgentCoreRole
```

Deploy everything:
```bash
make all
```

Or step by step:
```bash
make install     # Install dependencies
make configure   # Configure with IAM role
make deploy      # Deploy to AWS
make status      # Check deployment status
```

Test locally:
```bash
make test-local
```

Test deployed agent:
```bash
make test-remote
```

Custom test:
```bash
make invoke-remote PROMPT="I need help with my smartphone order"
```