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
    
    try:
        # Execute the command
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=60
        )
    except subprocess.TimeoutExpired:
        return {
            "action": "timeout",
            "command": f"aws {command}",
            "success": False,
            "error": "Command timed out after 60 seconds"
        }
    except Exception as e:
        return {
            "action": "error",
            "command": f"aws {command}",
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
    
    if result.returncode == 0:
        # Try to parse JSON output for better structure
        output_data = result.stdout.strip()
        
        response = {
            "action": "executed",
            "command": f"aws {command}",
            "success": True,
            "output": output_data if output_data else "Command completed successfully"
        }
        
        # Add parsed JSON if available
        if output_data:
            try:
                response["parsed_output"] = json.loads(output_data)
            except json.JSONDecodeError:
                pass  # Keep as plain text
                
        return response
        
    else:
        error_msg = result.stderr.strip() or 'Command failed with no error message'
        
        return {
            "action": "failed", 
            "command": f"aws {command}",
            "success": False,
            "error": error_msg,
            "return_code": result.returncode
        }