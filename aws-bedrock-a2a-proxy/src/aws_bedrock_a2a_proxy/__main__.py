import uvicorn


def main():
    """Entry point for aws-bedrock-a2a-proxy CLI command."""
    uvicorn.run(
        "aws_bedrock_a2a_proxy.main:app", 
        host="0.0.0.0", 
        port=2972, 
        reload=True,
        log_level="warning",  # Suppress uvicorn info messages
        access_log=False      # Suppress access logs
    )


if __name__ == "__main__":
    main()