#!/usr/bin/env python3
"""
AWS Status Tool

Simple tool to check AWS CLI availability and current identity.
"""

import subprocess
import json
from typing import Dict, Any
from strands import tool


@tool
def aws_status() -> str:
    """Check AWS CLI status and current identity"""
    status = {
        "aws_cli_available": False,
        "aws_cli_version": None,
        "identity": None,
        "error": None
    }
    
    try:
        # Check AWS CLI version
        version_result = subprocess.run(
            ["aws", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if version_result.returncode == 0:
            status["aws_cli_available"] = True
            status["aws_cli_version"] = version_result.stdout.strip()
        
        # Check AWS identity
        identity_result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if identity_result.returncode == 0:
            status["identity"] = json.loads(identity_result.stdout)
        else:
            status["error"] = identity_result.stderr.strip()
            
    except FileNotFoundError:
        status["error"] = "AWS CLI not found"
    except subprocess.TimeoutExpired:
        status["error"] = "AWS CLI command timed out"
    except json.JSONDecodeError:
        status["error"] = "Failed to parse AWS identity response"
    except Exception as e:
        status["error"] = f"Unexpected error: {str(e)}"
    
    return json.dumps(status, indent=2)