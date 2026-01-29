# python
"""
FastAPI server serving as Fast MCP (Model Context Protocol) backend.
Integrates CrewAI dispute resolution system with REST API endpoints.
"""

# Immediate event-loop & platform compatibility setup
import asyncio
import platform
import signal
import os
import sys
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Compatibility shim for Windows: define common POSIX signal names if missing
# Place BEFORE importing any third-party library that may reference POSIX signals.
if platform.system() == "Windows":
    _fallback = getattr(signal, "SIGTERM", 15)
    _posix_signals = (
        "SIGHUP",
        "SIGQUIT",
        "SIGCONT",
        "SIGCHLD",
        "SIGTSTP",
        "SIGSTOP",
        "SIGALRM",
        "SIGPIPE",
        "SIGUSR1",
        "SIGUSR2",
        "SIGILL",
        "SIGTRAP",
        "SIGBUS",
        "SIGFPE",
        "SIGSEGV",
    )
    for _name in _posix_signals:
        if not hasattr(signal, _name):
            setattr(signal, _name, _fallback)

# Disable uvloop explicitly if present and set default policy
try:
    import uvloop  # type: ignore

    # uvloop may not expose uninstall; simply choose default loop policy explicitly
    print("✓ uvloop detected, using default asyncio policy")
except ImportError:
    print("✓ uvloop not installed, using default asyncio")
except Exception as e:
    print(f"Warning: Could not handle uvloop: {e}")

asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
print("✓ Default asyncio event loop policy set")

# Apply nest_asyncio patch only in interactive environments (avoid breaking uvicorn)
try:
    import nest_asyncio  # type: ignore

    def _should_apply_nest_asyncio() -> bool:
        # Apply only in interactive / notebook / IDE sessions, not when running uvicorn/reloader.
        # REPL interactive check
        if hasattr(sys, "ps1"):
            return True
        # IPython / Jupyter
        if "IPYTHON" in sys.modules:
            return True
        # PyCharm interactive run
        if os.environ.get("PYCHARM_HOSTED") == "1":
            return True
        # Jupyter runtime dir hint
        if os.environ.get("JUPYTER_RUNTIME_DIR"):
            return True
        # If running under uvicorn worker subprocess (reloader) or as a production service, skip.
        if any(k in sys.argv[0].lower() for k in ("uvicorn", "gunicorn", "hypercorn")):
            return False
        return False

    if _should_apply_nest_asyncio():
        nest_asyncio.apply()
        print("✓ nest_asyncio patch applied")
    else:
        print("✓ nest_asyncio available but not applied (skipping for uvicorn/production)")
except ImportError:
    print("✓ nest_asyncio not available, using standard asyncio")
except Exception as e:
    print(f"Warning: Could not apply nest_asyncio patch: {e}")

# Framework & application imports
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Local application modules (import after signal shim)
from crew_ai_app.crew import get_crew_instance
from crew_ai_app.utils.s3_client import S3Client
from crew_ai_app.db.dynamo_client import DynamoDBClient
from mcp.log_manager import LogManager, log_info, log_agent_activity

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Request/Response Models
class CustomerVerificationRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID to verify")


class CardVerificationRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID")
    card_number: str = Field(..., description="Card number to verify")


class TransactionVerificationRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to verify")
    customer_id: Optional[str] = Field(None, description="Customer ID (optional for validation)")
    card_number: Optional[str] = Field(None, description="Card number (optional for validation)")


class CaseStatusRequest(BaseModel):
    case_id: str = Field(..., description="Case ID to lookup")


class CustomerCasesRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID to get cases for")


class UnifiedDisputeRequest(BaseModel):
    request: str = Field(..., description="Natural language description of the request")
    customer_id: Optional[str] = Field(None, description="Customer ID (if applicable)")
    card_number: Optional[str] = Field(None, description="Card number (if applicable)")
    transaction_id: Optional[str] = Field(None, description="Transaction ID (if applicable)")
    case_id: Optional[str] = Field(None, description="Case ID (if applicable)")


class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


# Global crew instance (initialized in lifespan)
crew_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    global crew_instance

    logger.info("Starting Fast MCP server...")
    try:
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        use_mcp_http = os.getenv("USE_MCP_HTTP", "false").lower() == "true"
        mcp_url = os.getenv("MCP_URL", "http://localhost:8001")

        crew_instance = get_crew_instance(
            aws_region=aws_region,
            use_mcp_http=use_mcp_http,
            mcp_url=mcp_url if use_mcp_http else None,
        )

        if use_mcp_http:
            logger.info(
                f"CrewAI instance initialized with HTTP-BASED MCP server at {mcp_url} (separate service) for region: {aws_region}"
            )
        else:
            logger.info(
                f"CrewAI instance initialized with DIRECT PYTHON MCP tools (in-process) for region: {aws_region}"
            )

    except Exception as e:
        logger.error(f"Failed to initialize CrewAI: {e}", exc_info=True)
        raise

    yield

    logger.info("Shutting down Fast MCP server...")


# Initialize FastAPI app
app = FastAPI(
    title="Dispute Resolution Fast MCP Server",
    description="FastAPI server integrating CrewAI agents for financial dispute resolution",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware setup
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,https://disp-reccom-dev.orchestrateai.tech,http://disp-reccom-dev.orchestrateai.tech,https://disp-reccom-prod.orchestrateai.tech,http://disp-reccom-prod.orchestrateai.tech",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for load balancer setup
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def handle_load_balancer(request: Request, call_next):
    """Handle load balancer forwarded headers and ensure CORS on responses."""
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")

    response = await call_next(request)

    # Ensure CORS headers are always present
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and timings."""
    import time

    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")

    return response


@app.options("/{full_path:path}")
async def handle_options(request: Request):
    """Handle CORS preflight requests."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if crew_instance and crew_instance.db_client:
            db_health = await crew_instance.db_client.health_check()
            return APIResponse(
                success=True,
                data={"status": "healthy", "database": db_health},
                message="Service is healthy",
            )
        else:
            return APIResponse(
                success=False,
                error="CrewAI instance not initialized",
                message="Service is not ready",
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return APIResponse(success=False, error=str(e), message="Health check failed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Dispute Resolution Fast MCP Server",
        "version": "0.1.0",
        "status": "running",
        "mode": "hierarchical",
        "description": "Manager agent orchestrates specialized agents for intelligent routing",
        "endpoints": {
            "health": "/health",
            "process_request": "/process (NEW: Unified manager-based endpoint)",
            "verify_customer": "/verify/customer (Legacy: Direct agent access)",
            "verify_card": "/verify/card (Legacy: Direct agent access)",
            "verify_transaction": "/verify/txn (Legacy: Direct agent access)",
            "case_status": "/case/status (Legacy: Direct agent access)",
            "customer_cases": "/case/customer (Legacy: Direct agent access)",
        },
    }


# ============================================================================
# Unified Manager-Based Endpoint
# ============================================================================
@app.post("/process", response_model=APIResponse)
async def process_unified_request(request: UnifiedDisputeRequest):
    """Process any dispute resolution request through the Manager Agent."""
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Processing unified request via Manager Agent: {request.request}")

        # Build enriched request description with context
        context_parts = []
        if request.customer_id:
            context_parts.append(f"customer_id={request.customer_id}")
        if request.card_number:
            context_parts.append(f"card_number={request.card_number}")
        if request.transaction_id:
            context_parts.append(f"transaction_id={request.transaction_id}")
        if request.case_id:
            context_parts.append(f"case_id={request.case_id}")

        full_request = request.request
        if context_parts:
            full_request += f" [{', '.join(context_parts)}]"

        # Process through manager agent
        result = await crew_instance.process_request(full_request)

        if result.get("success"):
            return APIResponse(
                success=True,
                data=result,
                message="Request processed successfully by Manager Agent",
            )
        else:
            return APIResponse(
                success=False,
                error=result.get("error", "Request processing failed"),
                message=result.get("message", "Manager agent could not process request"),
            )

    except Exception as e:
        logger.error(f"Error in unified request processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Manager agent error: {str(e)}")


# ============================================================================
# Legacy Endpoints - Direct Agent Access
# ============================================================================
@app.post("/verify/customer", response_model=APIResponse)
async def verify_customer(request: CustomerVerificationRequest):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Verifying customer: {request.customer_id}")
        result = await crew_instance.verify_customer(request.customer_id)

        if result.get("success"):
            return APIResponse(success=True, data=result, message="Customer verification completed")
        else:
            return APIResponse(success=False, error=result.get("message", "Customer verification failed"), message="Customer not found, please retry")

    except Exception as e:
        logger.error(f"Error in customer verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")


@app.post("/verify/card", response_model=APIResponse)
async def verify_card(request: CardVerificationRequest):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Verifying card {request.card_number} for customer {request.customer_id}")
        result = await crew_instance.verify_card(request.customer_id, request.card_number)

        if result.get("success"):
            return APIResponse(success=True, data=result, message="Card verification completed")
        else:
            return APIResponse(success=False, error=result.get("message", "Card verification failed"), message="Card not found")

    except Exception as e:
        logger.error(f"Error in card verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Card verification error: {str(e)}")


@app.post("/verify/txn", response_model=APIResponse)
async def verify_transaction(request: TransactionVerificationRequest):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Verifying transaction {request.transaction_id}")
        result = await crew_instance.verify_transaction(request.transaction_id, request.customer_id, request.card_number)

        if result.get("success"):
            return APIResponse(success=True, data=result, message="Transaction verification and dispute processing completed")
        else:
            return APIResponse(success=False, error=result.get("message", "Transaction verification failed"), message="Transaction not found")

    except Exception as e:
        logger.error(f"Error in transaction verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transaction verification error: {str(e)}")


# ============================================================================
# Case Management Endpoints
# ============================================================================
@app.post("/case/status", response_model=APIResponse)
async def get_case_status(request: CaseStatusRequest):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Getting status for case: {request.case_id}")
        case_data = await crew_instance.get_case_status(request.case_id)

        if case_data:
            return APIResponse(success=True, data={"case": case_data}, message="Case status retrieved successfully")
        else:
            return APIResponse(success=False, error="Case not found", message=f"No case found with ID: {request.case_id}")

    except Exception as e:
        logger.error(f"Error getting case status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Case lookup error: {str(e)}")


@app.post("/case/customer", response_model=APIResponse)
async def get_customer_cases(request: CustomerCasesRequest):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Getting cases for customer: {request.customer_id}")
        cases = await crew_instance.get_customer_cases(request.customer_id)

        return APIResponse(success=True, data={"cases": cases, "count": len(cases)}, message=f"Found {len(cases)} case(s) for customer {request.customer_id}")

    except Exception as e:
        logger.error(f"Error getting customer cases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Customer cases lookup error: {str(e)}")


class DynamoQueryRequest(BaseModel):
    table_name: str = Field(..., description="DynamoDB table name")
    operation: str = Field(..., description="Operation type: query, get_item, scan, put_item, update_item")
    key_condition: Optional[Dict[str, Any]] = Field(None, description="Key condition for query")
    filter_expression: Optional[Dict[str, Any]] = Field(None, description="Filter conditions")
    index_name: Optional[str] = Field(None, description="GSI name")
    attributes_to_get: Optional[List[str]] = Field(None, description="Attributes to retrieve")
    limit: Optional[int] = Field(None, description="Max items to return")
    item_data: Optional[Dict[str, Any]] = Field(None, description="Item data for put_item")
    update_expression: Optional[Dict[str, Any]] = Field(None, description="Update expression")


@app.post("/mcp/query", response_model=APIResponse)
async def execute_dynamo_query(request: DynamoQueryRequest):
    """Execute a DynamoDB query using the MCP Query Creator tool."""
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Executing MCP DynamoDB query: {request.operation} on {request.table_name}")

        from mcp.tools import DynamoQueryCreatorTool  # local tool

        query_tool = DynamoQueryCreatorTool(crew_instance.db_client)

        result = query_tool._run(
            table_name=request.table_name,
            operation=request.operation,
            key_condition=request.key_condition,
            filter_expression=request.filter_expression,
            index_name=request.index_name,
            attributes_to_get=request.attributes_to_get,
            limit=request.limit,
            item_data=request.item_data,
            update_expression=request.update_expression,
        )

        if result.get("success"):
            return APIResponse(success=True, data=result, message="Query executed successfully")
        else:
            return APIResponse(success=False, error=result.get("error", "Query execution failed"), message=result.get("message", "Failed to execute query"))

    except Exception as e:
        logger.error(f"Error executing MCP query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"MCP query error: {str(e)}")


@app.get("/case/{case_id}", response_model=APIResponse)
async def get_case_by_id(case_id: str):
    try:
        if not crew_instance:
            raise HTTPException(status_code=503, detail="Service not ready")

        logger.info(f"Getting case details: {case_id}")
        case_data = await crew_instance.get_case_status(case_id)

        if case_data:
            return APIResponse(success=True, data={"case": case_data}, message="Case details retrieved successfully")
        else:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Case lookup error: {str(e)}")


# ============================================================================
# Development / Debug Endpoints
# ============================================================================
@app.get("/debug/crew-info")
async def debug_crew_info():
    if not crew_instance:
        return {"error": "Crew instance not initialized"}

    return {
        "crew_initialized": crew_instance is not None,
        "db_client_initialized": crew_instance.db_client is not None,
        "agents": {
            "verification_agent": getattr(crew_instance, "verification_agent", None) is not None,
            "dispute_decision_agent": getattr(crew_instance, "dispute_decision_agent", None) is not None,
        },
        "aws_region": (crew_instance.db_client.region if crew_instance.db_client else None),
    }


# ============================================================================
# Document Upload / Retrieval Endpoints
# ============================================================================
@app.post("/case/{case_id}/upload-documents")
async def upload_case_documents(case_id: str, files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        aws_region = os.getenv("AWS_REGION", "us-east-1")
        s3_client = S3Client(region=aws_region)
        dynamo_client = DynamoDBClient(region=aws_region)

        case = await dynamo_client.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        uploaded_docs = []
        for file in files:
            content = await file.read()
            result = s3_client.upload_document(
                file_content=content,
                filename=file.filename or "unknown",
                case_id=case_id,
                content_type=file.content_type or "application/octet-stream",
            )

            if result.get("success"):
                uploaded_docs.append(
                    {
                        "filename": result.get("original_filename"),
                        "url": result.get("url"),
                        "key": result.get("key"),
                        "bucket": result.get("bucket"),
                    }
                )
            else:
                logger.error(f"Failed to upload {file.filename}: {result.get('error')}")

        if uploaded_docs:
            existing_docs = case.get("documents", [])
            if not isinstance(existing_docs, list):
                existing_docs = []
            all_docs = existing_docs + uploaded_docs
            await dynamo_client.update_case(case_id, {"documents": all_docs})
            logger.info(f"Uploaded {len(uploaded_docs)} documents for case {case_id}")

        return {
            "success": True,
            "case_id": case_id,
            "uploaded_documents": uploaded_docs,
            "total_documents": len(uploaded_docs),
            "message": f"Successfully uploaded {len(uploaded_docs)} document(s)",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documents for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/case/{case_id}/documents")
async def get_case_documents(case_id: str):
    try:
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        dynamo_client = DynamoDBClient(region=aws_region)
        s3_client = S3Client(region=aws_region)

        case = await dynamo_client.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        documents = case.get("documents", [])
        for doc in documents:
            if "key" in doc:
                presigned_url = s3_client.generate_presigned_url(doc["key"])
                if presigned_url:
                    doc["download_url"] = presigned_url

        return {"success": True, "case_id": case_id, "documents": documents, "count": len(documents)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documents for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Logging & Monitoring Endpoints
# ============================================================================
@app.get("/logs/live")
async def get_live_logs(limit: int = 50):
    try:
        log_manager = LogManager.get_instance()
        logs = log_manager.get_live_logs(limit=limit)
        return {"success": True, "logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error getting live logs: {e}", exc_info=True)
        return {"success": False, "logs": [], "error": str(e)}


@app.get("/logs/detailed")
async def get_detailed_logs(limit: int = 20):
    try:
        log_manager = LogManager.get_instance()
        logs = log_manager.get_detailed_logs(limit=limit)
        return {"success": True, "logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error getting detailed logs: {e}", exc_info=True)
        return {"success": False, "logs": [], "error": str(e)}


@app.get("/logs/stats")
async def get_log_stats():
    try:
        log_manager = LogManager.get_instance()
        stats = log_manager.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting log stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.delete("/logs/clear")
async def clear_logs():
    try:
        log_manager = LogManager.get_instance()
        log_manager.clear_logs()
        return {"success": True, "message": "All logs cleared"}
    except Exception as e:
        logger.error(f"Error clearing logs: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Fast MCP server on {host}:{port}")
    log_info("Fast MCP server starting", agent="System")

    uvicorn.run(
        "mcp.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info",
    )
