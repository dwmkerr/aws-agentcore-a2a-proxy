import json
import logging
import subprocess
from typing import Dict, Any

from strands import tool

logger = logging.getLogger(__name__)

@tool
def aws_command(command: str) -> Dict[str, Any]:
    """
    Execute AWS CLI commands. Use standard AWS CLI syntax like 'ec2 describe-instances', 's3 ls', 'sts get-caller-identity', etc.
    
    Args:
        command: AWS CLI command (e.g., 'ec2 describe-instances', 's3 ls', 'lambda list-functions')
        
    Returns:
        Dictionary containing command results with execution status
    """
    # Build the command
    cmd_parts = ["aws"] + command.split()
    
    # Add JSON output format for structured parsing
    if "--output" not in command:
        cmd_parts.extend(["--output", "json"])
    
    logger.info(f"Executing: {' '.join(cmd_parts)}")
    
    # Execute the command
    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        return {
            "action": "executed",
            "command": f"aws {command}",
            "success": True,
            "output": result.stdout.strip() if result.stdout.strip() else "Command completed successfully",
            "summary": f"Successfully executed: aws {command}"
        }
    else:
        return {
            "action": "failed", 
            "command": f"aws {command}",
            "success": False,
            "error": result.stderr.strip() or 'Command failed',
            "summary": f"Command failed: aws {command}"
        }