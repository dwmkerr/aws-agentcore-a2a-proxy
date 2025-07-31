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
        Dictionary containing command results
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
        # Try to parse JSON output
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            data = result.stdout.strip()
        
        return {
            "success": True,
            "data": data,
            "command": command
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip() or "Command failed",
            "command": command
        }