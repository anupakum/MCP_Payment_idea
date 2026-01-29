"""
MCP HTTP Client Tool for CrewAI

This tool calls the standalone MCP HTTP server to execute DynamoDB queries.
The MCP server runs separately on a different port (default: 8001).

Architecture:
    CrewAI Agent → MCPHttpClientTool → HTTP → MCP Server (port 8001) → DynamoDB
"""

import os
import logging
import time
from typing import Optional, Dict, Any
import requests
from crewai.tools import BaseTool
from pydantic import Field

# Import log manager for centralized logging
try:
    from mcp.log_manager import log_mcp_call, log_error, log_success, log_warning
    HAS_LOG_MANAGER = True
except ImportError:
    HAS_LOG_MANAGER = False

logger = logging.getLogger(__name__)


class MCPHttpClientTool(BaseTool):
    """
    HTTP client tool that calls the standalone MCP server.
    
    This tool enables CrewAI agents to query DynamoDB by making HTTP requests
    to a separate MCP HTTP server running independently.
    
    Usage:
        tool = MCPHttpClientTool(mcp_url="http://localhost:8001")
        result = tool._run(
            table_name="my_table",
            operation="query",
            key_condition={"customer_id": "C123"},
            explanation="Fetch customer data"
        )
    """
    
    name: str = "mcp_http_dynamo_query"
    description: str = """
    Query DynamoDB via MCP HTTP server.
    
    Use this tool to execute DynamoDB operations:
    - query: Query items with key conditions
    - scan: Scan table with optional filters
    - get_item: Get a single item by primary key
    - put_item: Insert or update an item
    
    Required parameters:
    - table_name: The DynamoDB table to query
    - operation: One of: query, scan, get_item, put_item
    - explanation: What you're trying to find/do
    
    Optional parameters based on operation:
    - key_condition: For query operations (dict with partition/sort key)
    - filter_expression: Additional filters (dict)
    - limit: Maximum items to return
    - projection_expression: Specific attributes to return
    - item: Item to insert (for put_item)
    - key: Primary key (for get_item)
    
    Returns:
    JSON string with query results or error message.
    """
    
    mcp_url: str = Field(
        default_factory=lambda: os.getenv("MCP_URL", "http://localhost:8001"),
        description="MCP HTTP server URL"
    )
    timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    
    def __init__(self, mcp_url: Optional[str] = None, **kwargs):
        """
        Initialize the MCP HTTP client tool.
        
        Args:
            mcp_url: URL of the MCP HTTP server (default: http://localhost:8001)
        """
        if mcp_url:
            kwargs['mcp_url'] = mcp_url
        
        super().__init__(**kwargs)
        
        # Verify MCP server is reachable
        self._verify_connection()
    
    def _verify_connection(self) -> None:
        """Verify connection to MCP server."""
        try:
            response = requests.get(
                f"{self.mcp_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Connected to MCP server: {data.get('service')} v{data.get('version')}")
                logger.info(f"MCP server region: {data.get('aws_region')}")
            else:
                logger.warning(f"MCP server returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to MCP server at {self.mcp_url}. "
                "Make sure it's running: python -m mcp.http_server"
            )
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
    
    def _run(
        self,
        table_name: str,
        operation: str,
        explanation: str,
        key_condition: Optional[Dict[str, Any]] = None,
        filter_expression: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        item: Optional[Dict[str, Any]] = None,
        key: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a DynamoDB query via MCP HTTP server.
        
        Args:
            table_name: DynamoDB table name
            operation: Operation type (query, scan, get_item, put_item)
            explanation: What this query is trying to accomplish
            key_condition: Key condition for query operations
            filter_expression: Filter expression for query/scan
            limit: Maximum number of items to return
            projection_expression: Attributes to return
            item: Item to insert (for put_item)
            key: Primary key (for get_item)
            
        Returns:
            JSON string with query results or error message
        """
        logger.info(f"Calling MCP HTTP server: {operation} on {table_name}")
        logger.info(f"Explanation: {explanation}")
        
        # Start timing
        start_time = time.time()
        
        try:
            # Build request payload
            payload = {
                "table_name": table_name,
                "operation": operation,
                "explanation": explanation
            }
            
            # Add optional parameters if provided
            if key_condition is not None:
                payload["key_condition"] = key_condition
            if filter_expression is not None:
                payload["filter_expression"] = filter_expression
            if limit is not None:
                payload["limit"] = limit
            if projection_expression is not None:
                payload["projection_expression"] = projection_expression
            if item is not None:
                payload["item"] = item
            if key is not None:
                payload["key"] = key
            
            # Make HTTP request to MCP server
            response = requests.post(
                f"{self.mcp_url}/tools/dynamo_query",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            duration_str = f"{duration_ms}ms"
            
            # Check response status
            if response.status_code != 200:
                error_msg = f"MCP server returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                
                # Log to centralized system
                if HAS_LOG_MANAGER:
                    log_error(
                        f"MCP call failed: {operation} on {table_name}",
                        agent="MCP Client",
                        action=f"DynamoDB {operation}",
                        details=error_msg,
                        duration=duration_str
                    )
                
                return f"Error: {error_msg}"
            
            # Parse response
            result = response.json()
            
            if not result.get("success"):
                error = result.get("error", "Unknown error")
                logger.error(f"Query failed: {error}")
                
                # Log to centralized system
                if HAS_LOG_MANAGER:
                    log_error(
                        f"DynamoDB query failed: {operation} on {table_name}",
                        agent="MCP Client",
                        action=f"DynamoDB {operation}",
                        details=error,
                        duration=duration_str
                    )
                
                return f"Error: {error}"
            
            # Success!
            items_count = result.get("items_count", 0)
            logger.info(f"Query successful: {items_count} items returned")
            
            # Log to centralized system
            if HAS_LOG_MANAGER:
                log_mcp_call(
                    operation=operation,
                    table=table_name,
                    result_count=items_count,
                    duration=duration_str
                )
            
            # Return formatted result
            import json
            return json.dumps({
                "success": True,
                "operation": operation,
                "table_name": table_name,
                "items_count": items_count,
                "result": result.get("result")
            }, indent=2)
            
        except requests.exceptions.Timeout:
            error_msg = f"Request to MCP server timed out after {self.timeout}s"
            logger.error(error_msg)
            return f"Error: {error_msg}"
            
        except requests.exceptions.ConnectionError:
            error_msg = (
                f"Cannot connect to MCP server at {self.mcp_url}. "
                "Make sure it's running: python -m mcp.http_server"
            )
            logger.error(error_msg)
            return f"Error: {error_msg}"
            
        except Exception as e:
            error_msg = f"Unexpected error calling MCP server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"
    
    def get_tools_list(self) -> Dict[str, Any]:
        """
        Get list of available tools from MCP server.
        
        Returns:
            Dictionary with tools information
        """
        try:
            response = requests.get(
                f"{self.mcp_url}/tools",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get tools list: {response.status_code}")
                return {"tools": []}
                
        except Exception as e:
            logger.error(f"Error getting tools list: {e}")
            return {"tools": []}
