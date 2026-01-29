"""
MCP Server Implementation
Model Context Protocol server that runs as a separate process
and communicates via stdin/stdout using JSON-RPC
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, Optional, List
from datetime import datetime

# Configure logging to stderr (stdout is used for MCP communication)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server that handles tool execution requests via stdio."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.tools = {}
        self.db_client = None
        logger.info("MCP Server initialized")
    
    async def initialize_db_client(self):
        """Initialize DynamoDB client."""
        try:
            import os
            from crew_ai_app.db.dynamo_client import DynamoDBClient
            
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            self.db_client = DynamoDBClient(region=aws_region)
            logger.info(f"DynamoDB client initialized for region: {aws_region}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB client: {e}")
            raise
    
    def register_tool(self, name: str, handler):
        """Register a tool handler.
        
        Args:
            name: Tool name
            handler: Async function to handle tool execution
        """
        self.tools[name] = handler
        logger.info(f"Registered tool: {name}")
    
    async def handle_query_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DynamoDB query tool execution.
        
        Args:
            params: Tool parameters
            
        Returns:
            Query results
        """
        try:
            table_name = params.get("table_name")
            operation = params.get("operation")
            key_condition = params.get("key_condition")
            filter_expression = params.get("filter_expression")
            index_name = params.get("index_name")
            attributes_to_get = params.get("attributes_to_get")
            limit = params.get("limit")
            item_data = params.get("item_data")
            update_expression = params.get("update_expression")
            
            logger.info(f"Executing {operation} on {table_name}")
            
            # Import the tool logic
            from mcp.tools.dynamo_query_tool import DynamoQueryCreatorTool
            
            # Create tool instance
            tool = DynamoQueryCreatorTool(self.db_client)
            
            # Execute query
            result = tool._run(
                table_name=table_name,
                operation=operation,
                key_condition=key_condition,
                filter_expression=filter_expression,
                index_name=index_name,
                attributes_to_get=attributes_to_get,
                limit=limit,
                item_data=item_data,
                update_expression=update_expression
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query tool: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools.
        
        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "dynamo_query_creator",
                "description": "Create and execute DynamoDB queries dynamically",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "DynamoDB table name"
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["query", "get_item", "scan", "put_item", "update_item"],
                            "description": "Operation type"
                        },
                        "key_condition": {
                            "type": "object",
                            "description": "Key condition for query"
                        },
                        "filter_expression": {
                            "type": "object",
                            "description": "Additional filter conditions"
                        },
                        "index_name": {
                            "type": "string",
                            "description": "GSI name if querying an index"
                        },
                        "attributes_to_get": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific attributes to retrieve"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of items to return"
                        }
                    },
                    "required": ["table_name", "operation"]
                }
            }
        ]
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request.
        
        Args:
            params: Initialization parameters
            
        Returns:
            Server capabilities
        """
        logger.info("Handling initialize request")
        
        await self.initialize_db_client()
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "dynamodb-mcp-server",
                "version": "1.0.0"
            }
        }
    
    async def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request.
        
        Returns:
            List of available tools
        """
        tools = await self.handle_list_tools()
        return {"tools": tools}
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request.
        
        Args:
            params: Tool call parameters
            
        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})
        
        logger.info(f"Calling tool: {tool_name}")
        
        if tool_name == "dynamo_query_creator":
            result = await self.handle_query_tool(tool_arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ]
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Unknown tool: {tool_name}"
                        })
                    }
                ],
                "isError": True
            }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request.
        
        Args:
            request: JSON-RPC request
            
        Returns:
            JSON-RPC response
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.info(f"Handling request: {method}")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list()
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """Run the MCP server (stdio loop)."""
        logger.info("MCP Server starting...")
        logger.info("Listening on stdin for JSON-RPC requests")
        
        # Read from stdin line by line
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # Read line from stdin
                line = await loop.run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    continue
                
                # Handle request
                response = await self.handle_request(request)
                
                # Write response to stdout
                print(json.dumps(response), flush=True)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                break
        
        logger.info("MCP Server shutting down")


async def main():
    """Main entry point for MCP server."""
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
