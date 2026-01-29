"""
Case Query Agent for retrieving and analyzing dispute cases.
"""

import logging
import asyncio

# Disable uvloop to prevent conflicts with nest_asyncio
# This ensures compatibility across platforms (Windows/Linux) and prevents "Can't patch loop" errors
logger = logging.getLogger(__name__)

# Disable uvloop explicitly if it's installed
try:
    import uvloop
    # Note: uvloop.uninstall() method doesn't exist in current versions
    # Just set default event loop policy instead
    logger.info("✓ uvloop detected, using default asyncio policy")
except ImportError:
    logger.info("✓ uvloop not installed, using default asyncio")
except Exception as e:
    logger.warning(f"Warning: Could not handle uvloop in case_query_agent: {e}")

# Set default event loop policy
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
logger.info("✓ Default asyncio event loop policy set")

# Apply nest_asyncio patch to allow nested event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
    logger.info("✓ nest_asyncio patch applied")
except ImportError:
    logger.info("✓ nest_asyncio not available, using standard asyncio")
except Exception as e:
    logger.warning(f"Warning: Could not apply nest_asyncio patch: {e}")

from typing import Dict, Any, Optional, List

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..llm_config import get_bedrock_llm_config
from mcp.tools import DynamoQueryCreatorTool, MCPHttpClientTool


class CaseQueryInput(BaseModel):
    """Input model for case queries."""
    case_id: Optional[str] = Field(None, description="Case ID to query")
    customer_id: Optional[str] = Field(None, description="Customer ID to query all cases")


class CaseLookupTool(BaseTool):
    """Tool for looking up case details by case ID."""
    
    name: str = "case_lookup"
    description: str = "Look up a dispute case by case ID and return detailed case information"
    db_client: Any = Field(default=None, exclude=True)
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)
    
    def _run(self, case_id: str) -> Dict[str, Any]:
        """Look up a case by ID."""
        try:
            import asyncio

            # Handle running loop properly (nest_asyncio patch already applied at module level)
            try:
                # Try to get running loop first
                loop = asyncio.get_running_loop()
                # With nest_asyncio applied, we can run_until_complete even in running loop
                case_data = loop.run_until_complete(self.db_client.get_case(case_id))
            except RuntimeError:
                # No running loop, create a new one and use run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                case_data = loop.run_until_complete(self.db_client.get_case(case_id))
            
            if case_data:
                return {
                    "success": True,
                    "case": case_data,
                    "message": f"Found case {case_id}"
                }
            else:
                return {
                    "success": False,
                    "message": f"No case found with ID: {case_id}"
                }
                
        except Exception as e:
            logger.error(f"Error looking up case {case_id}: {e}")
            return {
                "success": False,
                "message": f"Error retrieving case: {str(e)}"
            }


class CustomerCasesLookupTool(BaseTool):
    """Tool for looking up all cases for a customer."""
    
    name: str = "customer_cases_lookup"
    description: str = "Look up all dispute cases for a specific customer ID"
    db_client: Any = Field(default=None, exclude=True)
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)
    
    def _run(self, customer_id: str, limit: int = 50) -> Dict[str, Any]:
        """Look up all cases for a customer."""
        try:
            import asyncio

            # Handle running loop properly (nest_asyncio patch already applied at module level)
            try:
                # Try to get running loop first
                loop = asyncio.get_running_loop()
                # With nest_asyncio applied, we can run_until_complete even in running loop
                cases = loop.run_until_complete(
                    self.db_client.list_cases_by_customer(customer_id, limit)
                )
            except RuntimeError:
                # No running loop, create a new one and use run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                cases = loop.run_until_complete(
                    self.db_client.list_cases_by_customer(customer_id, limit)
                )
            
            return {
                "success": True,
                "cases": cases,
                "count": len(cases),
                "message": f"Found {len(cases)} case(s) for customer {customer_id}"
            }
                
        except Exception as e:
            logger.error(f"Error looking up cases for customer {customer_id}: {e}")
            return {
                "success": False,
                "cases": [],
                "count": 0,
                "message": f"Error retrieving cases: {str(e)}"
            }


class CaseQueryAgent:
    """Agent responsible for querying and analyzing dispute cases."""

    def __init__(self, db_client, use_mcp_http: bool = False, mcp_url: str = None):
        """Initialize the case query agent.
        
        Args:
            db_client: DynamoDB client instance
            use_mcp_http: If True, use HTTP-based MCP server, else direct Python calls
            mcp_url: URL of MCP HTTP server (default: http://localhost:8001)
        """
        self.db_client = db_client
        self.use_mcp_http = use_mcp_http
        
        # Initialize case lookup tools
        self.case_lookup_tool = CaseLookupTool(db_client)
        self.customer_cases_lookup_tool = CustomerCasesLookupTool(db_client)
        
        # Initialize MCP tool (HTTP or direct)
        if use_mcp_http:
            logger.info(f"Using HTTP-based MCP client tool (separate service at {mcp_url or 'http://localhost:8001'})")
            self.dynamo_query_tool = MCPHttpClientTool(mcp_url=mcp_url)
        else:
            logger.info("Using direct Python MCP tool (in-process)")
            self.dynamo_query_tool = DynamoQueryCreatorTool(db_client)
        
        # Get Bedrock LLM configuration (CrewAI native)
        bedrock_config = get_bedrock_llm_config(temperature=0.1)
        
        # Create the CrewAI agent with Bedrock
        self._agent = Agent(
            role="Case Query Specialist",
            goal="Retrieve and analyze dispute case information efficiently and accurately using database query tools",
            backstory=f"""You are an experienced case management specialist with deep knowledge of 
            dispute resolution systems and case tracking. You have been managing case databases
            for years and understand how to efficiently retrieve and present case information.
            You can query individual cases by case ID, retrieve all cases for a specific customer,
            and use custom database queries {'(via separate MCP HTTP server)' if use_mcp_http else '(in-process)'} 
            to analyze case patterns and trends. You are known for your accuracy, speed, and ability
            to present information clearly and concisely. You always verify case information and
            provide relevant context to help customers understand their dispute status.""",
            tools=[
                self.case_lookup_tool,
                self.customer_cases_lookup_tool,
                self.dynamo_query_tool
            ],
            llm=bedrock_config['model'],
            verbose=True,
            allow_delegation=False
        )

    def get_agent(self) -> Agent:
        """Return the CrewAI agent instance."""
        return self._agent

    async def get_case(self, case_id: str) -> Dict[str, Any]:
        """Retrieve a specific case by case ID.
        
        Args:
            case_id: Unique case identifier
            
        Returns:
            Dict containing case data or error information
        """
        logger.info(f"Retrieving case: {case_id}")
        
        try:
            result = self.case_lookup_tool._run(case_id)
            return result
                
        except Exception as e:
            logger.error(f"Error retrieving case {case_id}: {e}")
            return {
                "success": False,
                "message": f"Error retrieving case: {str(e)}"
            }

    async def get_customer_cases(self, customer_id: str, limit: int = 50) -> Dict[str, Any]:
        """Retrieve all cases for a customer.
        
        Args:
            customer_id: Customer identifier
            limit: Maximum number of cases to return
            
        Returns:
            Dict containing list of cases or error information
        """
        logger.info(f"Retrieving cases for customer: {customer_id}")
        
        try:
            result = self.customer_cases_lookup_tool._run(customer_id, limit)
            return result
                
        except Exception as e:
            logger.error(f"Error retrieving cases for customer {customer_id}: {e}")
            return {
                "success": False,
                "cases": [],
                "count": 0,
                "message": f"Error retrieving cases: {str(e)}"
            }
