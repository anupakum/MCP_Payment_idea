"""
MCP Client Tool for CrewAI
Communicates with MCP server via stdio (stdin/stdout)
"""

import json
import logging
import subprocess
import sys
import threading
from typing import Dict, Any, Optional, List
from queue import Queue, Empty
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPClientTool(BaseTool):
    """
    CrewAI tool that communicates with an MCP server via stdio.
    
    This tool spawns the MCP server as a subprocess and communicates
    via stdin/stdout using JSON-RPC protocol.
    """
    
    name: str = "mcp_dynamo_query"
    description: str = """
    Execute DynamoDB queries via MCP server (separate process).
    Supports: query, get_item, scan, put_item, update_item operations.
    Can query tables: 'ptr_dispute_resol_customer_cards_and_transactions', 'ptr_dispute_resol_case_db'.
    Can use indexes: 'TransactionIndex' (on transaction_id), 'CustomerIndex' (on customer_id).
    """
    
    # Process and communication
    process: Any = Field(default=None, exclude=True)
    request_id_counter: int = Field(default=0, exclude=True)
    output_queue: Any = Field(default=None, exclude=True)
    reader_thread: Any = Field(default=None, exclude=True)
    initialized: bool = Field(default=False, exclude=True)
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, **kwargs):
        """Initialize the MCP client tool."""
        super().__init__(**kwargs)
        self._start_mcp_server()
        self._initialize_server()
    
    def _start_mcp_server(self):
        """Start the MCP server as a subprocess."""
        try:
            logger.info("Starting MCP server subprocess...")
            
            # Start MCP server process
            self.process = subprocess.Popen(
                [sys.executable, "-m", "mcp.mcp_server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Create queue for responses
            object.__setattr__(self, 'output_queue', Queue())
            
            # Start thread to read from stdout
            def read_output():
                """Read lines from MCP server stdout."""
                try:
                    for line in self.process.stdout:
                        line = line.strip()
                        if line:
                            try:
                                response = json.loads(line)
                                self.output_queue.put(response)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse response: {e}")
                except Exception as e:
                    logger.error(f"Error reading output: {e}")
            
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            object.__setattr__(self, 'reader_thread', reader_thread)
            
            logger.info("MCP server subprocess started")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    def _initialize_server(self):
        """Send initialize request to MCP server."""
        try:
            logger.info("Initializing MCP server...")
            
            response = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "crewai-mcp-client",
                    "version": "1.0.0"
                }
            })
            
            if "result" in response:
                object.__setattr__(self, 'initialized', True)
                logger.info(f"MCP server initialized: {response['result']}")
            else:
                logger.error(f"Initialization failed: {response}")
                raise Exception("Failed to initialize MCP server")
                
        except Exception as e:
            logger.error(f"Error initializing server: {e}")
            raise
    
    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server and wait for response.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response
        """
        try:
            # Generate request ID
            self.request_id_counter += 1
            request_id = self.request_id_counter
            
            # Build JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params
            }
            
            # Send to stdin
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            logger.debug(f"Sent request: {method} (id={request_id})")
            
            # Wait for response
            timeout = 30  # 30 seconds timeout
            response = self.output_queue.get(timeout=timeout)
            
            # Verify response ID matches
            if response.get("id") != request_id:
                logger.warning(f"Response ID mismatch: expected {request_id}, got {response.get('id')}")
            
            return response
            
        except Empty:
            logger.error(f"Timeout waiting for response to {method}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": "Request timeout"
                }
            }
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    def _run(
        self,
        table_name: str,
        operation: str,
        key_condition: Optional[Dict[str, Any]] = None,
        filter_expression: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
        attributes_to_get: Optional[List[str]] = None,
        limit: Optional[int] = None,
        item_data: Optional[Dict[str, Any]] = None,
        update_expression: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a DynamoDB query via MCP server.
        
        Args:
            table_name: Name of the DynamoDB table
            operation: Type of operation (query, get_item, scan, put_item, update_item)
            key_condition: Primary key condition
            filter_expression: Additional filter conditions
            index_name: GSI name if querying an index
            attributes_to_get: List of specific attributes to retrieve
            limit: Maximum number of items to return
            item_data: Data for put_item operation
            update_expression: Update expression for update_item
            
        Returns:
            Query results or operation status
        """
        try:
            if not self.initialized:
                return {
                    "success": False,
                    "error": "MCP server not initialized"
                }
            
            logger.info(f"Executing MCP query: {operation} on {table_name}")
            
            # Build tool call parameters
            tool_params = {
                "name": "dynamo_query_creator",
                "arguments": {
                    "table_name": table_name,
                    "operation": operation
                }
            }
            
            # Add optional parameters
            if key_condition is not None:
                tool_params["arguments"]["key_condition"] = key_condition
            if filter_expression is not None:
                tool_params["arguments"]["filter_expression"] = filter_expression
            if index_name is not None:
                tool_params["arguments"]["index_name"] = index_name
            if attributes_to_get is not None:
                tool_params["arguments"]["attributes_to_get"] = attributes_to_get
            if limit is not None:
                tool_params["arguments"]["limit"] = limit
            if item_data is not None:
                tool_params["arguments"]["item_data"] = item_data
            if update_expression is not None:
                tool_params["arguments"]["update_expression"] = update_expression
            
            # Send tools/call request
            response = self._send_request("tools/call", tool_params)
            
            # Handle response
            if "error" in response:
                logger.error(f"MCP error: {response['error']}")
                return {
                    "success": False,
                    "error": response["error"].get("message", "Unknown error")
                }
            
            if "result" in response:
                result = response["result"]
                
                # Extract text content
                if "content" in result and len(result["content"]) > 0:
                    content = result["content"][0]
                    if content.get("type") == "text":
                        # Parse the JSON result
                        return json.loads(content["text"])
                
                return result
            
            return {
                "success": False,
                "error": "Unexpected response format"
            }
            
        except Exception as e:
            logger.error(f"Error executing MCP query: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def __del__(self):
        """Clean up: terminate MCP server process."""
        try:
            if hasattr(self, 'process') and self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("MCP server process terminated")
        except Exception as e:
            logger.error(f"Error terminating MCP server: {e}")
