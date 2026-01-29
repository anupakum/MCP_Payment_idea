"""
Standalone MCP HTTP Server

This is a SEPARATE FastAPI server that runs independently from the main application.
It provides MCP (Model Context Protocol) tools over HTTP/REST API.

Run this server separately:
    python -m mcp.http_server

Default port: 8001
Main app runs on: 8000

Architecture:
    Main FastAPI (port 8000) → HTTP → MCP Server (port 8001) → DynamoDB
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for DynamoDB queries."""
    table_name: str = Field(..., description="DynamoDB table name")
    operation: str = Field(..., description="Operation: query, scan, get_item, put_item")
    key_condition: Optional[Dict[str, Any]] = Field(None, description="Key condition for query")
    filter_expression: Optional[Dict[str, Any]] = Field(None, description="Filter expression")
    limit: Optional[int] = Field(None, description="Max items to return")
    projection_expression: Optional[str] = Field(None, description="Attributes to return")
    item: Optional[Dict[str, Any]] = Field(None, description="Item for put_item")
    key: Optional[Dict[str, Any]] = Field(None, description="Key for get_item")
    explanation: str = Field(..., description="Explanation of what this query does")


class QueryResponse(BaseModel):
    """Response model for DynamoDB queries."""
    success: bool
    operation: str
    table_name: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    items_count: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    aws_region: str


class ToolInfo(BaseModel):
    """Tool information."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolsListResponse(BaseModel):
    """Response for tools list endpoint."""
    tools: list[ToolInfo]


# ============================================================================
# Initialize FastAPI App
# ============================================================================

app = FastAPI(
    title="MCP HTTP Server",
    description="Standalone MCP server providing DynamoDB query tools over HTTP",
    version="1.0.0"
)

# CORS middleware - allow main app to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify main app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# DynamoDB Client Initialization
# ============================================================================

def get_dynamo_client():
    """Get or create DynamoDB client."""
    from crew_ai_app.db.dynamo_client import DynamoDBClient
    
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    logger.info(f"Initializing DynamoDB client for region: {aws_region}")
    
    return DynamoDBClient(region_name=aws_region)


# Global DB client (initialized on first request)
_db_client = None

def get_db():
    """Get DB client singleton."""
    global _db_client
    if _db_client is None:
        _db_client = get_dynamo_client()
    return _db_client


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        service="MCP HTTP Server",
        version="1.0.0",
        aws_region=os.getenv("AWS_REGION", "us-east-1")
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="MCP HTTP Server",
        version="1.0.0",
        aws_region=os.getenv("AWS_REGION", "us-east-1")
    )


@app.get("/tools", response_model=ToolsListResponse)
async def list_tools():
    """List available MCP tools."""
    tools = [
        ToolInfo(
            name="dynamo_query",
            description="Execute DynamoDB queries (query, scan, get_item, put_item)",
            input_schema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "DynamoDB table name"},
                    "operation": {"type": "string", "enum": ["query", "scan", "get_item", "put_item"]},
                    "key_condition": {"type": "object", "description": "Key condition for query"},
                    "filter_expression": {"type": "object", "description": "Filter expression"},
                    "limit": {"type": "integer", "description": "Max items to return"},
                    "projection_expression": {"type": "string", "description": "Attributes to return"},
                    "item": {"type": "object", "description": "Item for put_item"},
                    "key": {"type": "object", "description": "Key for get_item"},
                    "explanation": {"type": "string", "description": "Query explanation"}
                },
                "required": ["table_name", "operation", "explanation"]
            }
        )
    ]
    
    return ToolsListResponse(tools=tools)


@app.post("/tools/dynamo_query", response_model=QueryResponse)
async def execute_dynamo_query(request: QueryRequest):
    """
    Execute a DynamoDB query.
    
    This endpoint provides access to DynamoDB operations:
    - query: Query items with key conditions
    - scan: Scan table with optional filters
    - get_item: Get a single item by key
    - put_item: Insert or update an item
    """
    logger.info(f"Executing {request.operation} on {request.table_name}")
    logger.info(f"Explanation: {request.explanation}")
    
    try:
        db = get_db()
        
        # Execute based on operation type
        if request.operation == "query":
            if not request.key_condition:
                raise HTTPException(
                    status_code=400,
                    detail="key_condition is required for query operation"
                )
            
            result = db.query_items(
                table_name=request.table_name,
                key_condition_expression=request.key_condition,
                filter_expression=request.filter_expression,
                limit=request.limit,
                projection_expression=request.projection_expression
            )
            
        elif request.operation == "scan":
            result = db.scan_items(
                table_name=request.table_name,
                filter_expression=request.filter_expression,
                limit=request.limit,
                projection_expression=request.projection_expression
            )
            
        elif request.operation == "get_item":
            if not request.key:
                raise HTTPException(
                    status_code=400,
                    detail="key is required for get_item operation"
                )
            
            result = db.get_item(
                table_name=request.table_name,
                key=request.key
            )
            
        elif request.operation == "put_item":
            if not request.item:
                raise HTTPException(
                    status_code=400,
                    detail="item is required for put_item operation"
                )
            
            result = db.put_item(
                table_name=request.table_name,
                item=request.item
            )
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported operation: {request.operation}"
            )
        
        # Count items if result has Items
        items_count = len(result.get("Items", [])) if isinstance(result, dict) else None
        
        logger.info(f"Query successful: {items_count} items returned")
        
        return QueryResponse(
            success=True,
            operation=request.operation,
            table_name=request.table_name,
            result=result,
            items_count=items_count
        )
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        return QueryResponse(
            success=False,
            operation=request.operation,
            table_name=request.table_name,
            error=str(e)
        )


# ============================================================================
# Server Startup
# ============================================================================

def main():
    """Run the MCP HTTP server."""
    port = int(os.getenv("MCP_PORT", "8001"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    
    logger.info("=" * 80)
    logger.info("Starting MCP HTTP Server")
    logger.info("=" * 80)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Available endpoints:")
    logger.info(f"  GET  http://{host}:{port}/           - Health check")
    logger.info(f"  GET  http://{host}:{port}/health     - Health check")
    logger.info(f"  GET  http://{host}:{port}/tools      - List tools")
    logger.info(f"  POST http://{host}:{port}/tools/dynamo_query - Execute query")
    logger.info("=" * 80)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
