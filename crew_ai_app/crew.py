"""
Main CrewAI setup for dispute resolution system.
Uses hierarchical process with Manager Agent as orchestrator.
"""

import logging
from typing import Dict, Any, Optional, List
from crewai import Crew, Process, Task

from .agents.manager_agent import DisputeManagerAgent
from .agents.verification_agent import VerificationAgent
from .agents.dispute_decision_agent import DisputeDecisionAgent
from .agents.case_query_agent import CaseQueryAgent
from .db.dynamo_client import DynamoDBClient
from .llm_config import get_llm_config

logger = logging.getLogger(__name__)


class DisputeResolutionCrew:
    """Main crew orchestrating dispute resolution workflow using hierarchical process.
    
    The Manager Agent acts as an intelligent orchestrator, routing requests to:
    - VerificationAgent: Customer/card/transaction verification
    - DisputeDecisionAgent: Dispute processing and case creation  
    - CaseQueryAgent: Case status and history queries
    """

    def __init__(self, aws_region: str = "us-east-1", use_mcp_http: bool = False, mcp_url: Optional[str] = None):
        """Initialize the dispute resolution crew with hierarchical orchestration.
        
        Args:
            aws_region: AWS region for DynamoDB access
            use_mcp_http: If True, agents use HTTP-based MCP server (separate service)
                          If False, agents use direct Python calls (in-process)
            mcp_url: URL of MCP HTTP server (default: http://localhost:8001)
        """
        self.db_client = DynamoDBClient(region=aws_region)
        self.use_mcp_http = use_mcp_http
        
        # Initialize Manager Agent (orchestrator)
        self.manager_agent = DisputeManagerAgent()
        
        # Initialize specialized agents
        self.verification_agent = VerificationAgent(
            db_client=self.db_client,
            use_mcp_http=use_mcp_http,
            mcp_url=mcp_url or "http://localhost:8001"
        )
        self.dispute_decision_agent = DisputeDecisionAgent(
            db_client=self.db_client,
            use_mcp_http=use_mcp_http,
            mcp_url=mcp_url or "http://localhost:8001"
        )
        self.case_query_agent = CaseQueryAgent(
            db_client=self.db_client,
            use_mcp_http=use_mcp_http,
            mcp_url=mcp_url or "http://localhost:8001"
        )
        
        # Get LLM config for the manager
        llm_config = get_llm_config()
        manager_llm = llm_config['model']
        
        # Setup crew with hierarchical process
        # In hierarchical mode, CrewAI automatically creates a manager agent
        # that delegates to the specialized agents based on tasks
        self.crew = Crew(
            agents=[
                self.verification_agent.get_agent(),
                self.dispute_decision_agent.get_agent(),
                self.case_query_agent.get_agent()
            ],
            tasks=[],  # Tasks will be created dynamically per request
            process=Process.hierarchical,  # HIERARCHICAL: Auto-creates manager for delegation
            manager_llm=manager_llm,  # LLM for the auto-created manager to use
            memory=True,  # Enable memory for context retention
            verbose=True
        )

    async def process_request(self, request_description: str) -> Dict[str, Any]:
        """Process any dispute resolution request using intelligent routing.
        
        Analyzes the request and routes to the appropriate agent method directly.
        This approach provides structured data instead of string results from CrewAI.
        
        Args:
            request_description: Natural language description of the request
            
        Returns:
            Dict containing result from the appropriate agent
        """
        try:
            logger.info(f"Processing request via intelligent routing: {request_description}")
            
            # Parse the request to extract intent and entities
            request_lower = request_description.lower()
            
            # Extract IDs using patterns
            import re
            
            # Extract customer ID (CUST followed by digits)
            customer_match = re.search(r'cust\d+', request_lower)
            customer_id = customer_match.group(0).upper() if customer_match else None
            
            # Extract case ID (UUID format: 8-4-4-4-12 hex digits)
            # This matches the standard UUID v4 format used by DynamoDB case IDs
            case_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', request_lower)
            case_id = case_match.group(0) if case_match else None
            
            # Extract transaction ID (TXN or TX followed by digits)
            txn_match = re.search(r'tx[n]?\d+', request_lower)
            transaction_id = txn_match.group(0).upper() if txn_match else None
            
            # Extract card number (sequence of 4-19 digits)
            card_match = re.search(r'\d{4,19}', request_description)
            card_number = card_match.group(0) if card_match else None
            
            # Determine intent and route to appropriate agent
            # IMPORTANT: Order matters! Check more specific patterns first
            
            if 'case' in request_lower and 'status' in request_lower and case_id:
                # Case status query
                logger.info(f"Routing to CaseQueryAgent for case status: {case_id}")
                result = await self.get_case_status(case_id)
                return {
                    "success": True if result else False,
                    "result": {"case": result} if result else None,
                    "message": "Case status retrieved" if result else "Case not found"
                }
            
            elif (('my cases' in request_lower or 'customer cases' in request_lower or 
                  ('all' in request_lower and 'case' in request_lower)) and customer_id):
                # Customer cases query - matches "my cases", "customer cases", "all cases for customer"
                logger.info(f"Routing to CaseQueryAgent for customer cases: {customer_id}")
                result = await self.get_customer_cases(customer_id)
                return {
                    "success": True,
                    "result": {"cases": result},
                    "message": f"Found {len(result)} cases for customer"
                }
            
            elif transaction_id and ('dispute' in request_lower or 'transaction' in request_lower):
                # Transaction dispute
                logger.info(f"Routing to DisputeDecisionAgent for transaction: {transaction_id}")
                result = await self.verify_transaction(transaction_id, customer_id, card_number)
                return {
                    "success": result.get("success", False),
                    "result": result,
                    "message": "Transaction dispute processed"
                }
            
            elif card_number and customer_id:
                # Card verification
                logger.info(f"Routing to VerificationAgent for card: {card_number}")
                result = await self.verify_card(customer_id, card_number)
                return {
                    "success": result.get("success", False),
                    "result": result,
                    "message": "Card verification completed"
                }
            
            elif customer_id and ('verify' in request_lower or 'show' in request_lower or 'cards' in request_lower) and 'case' not in request_lower:
                # Customer verification - only if NOT asking about cases
                logger.info(f"Routing to VerificationAgent for customer: {customer_id}")
                result = await self.verify_customer(customer_id)
                return {
                    "success": result.get("success", False),
                    "result": result,
                    "message": "Customer verification completed"
                }
            
            else:
                # Unable to determine intent
                logger.warning(f"Unable to route request: {request_description}")
                return {
                    "success": False,
                    "error": "Unable to understand request",
                    "message": "Please provide a customer ID, case ID, or transaction ID"
                }
                
        except Exception as e:
            logger.error(f"Error in process_request: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Error processing request"
            }

    async def verify_customer(self, customer_id: str) -> Dict[str, Any]:
        """Verify customer and return associated cards.
        
        Args:
            customer_id: Customer identifier to verify
            
        Returns:
            Dict containing verification status and card list if found
        """
        result = await self.verification_agent.verify_customer(customer_id)
        return result

    async def verify_card(self, customer_id: str, card_number: str) -> Dict[str, Any]:
        """Verify card belongs to customer and return transactions.
        
        Args:
            customer_id: Customer identifier
            card_number: Card number to verify
            
        Returns:
            Dict containing verification status and transaction list if found
        """
        result = await self.verification_agent.verify_card(customer_id, card_number)
        return result

    async def verify_transaction(
        self, 
        transaction_id: str,
        customer_id: Optional[str] = None, 
        card_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify transaction and trigger dispute decision process.
        
        Args:
            transaction_id: Transaction identifier to verify
            customer_id: Customer identifier (optional for validation)
            card_number: Card number (optional for validation)
            
        Returns:
            Dict containing verification status and transaction details
        """
        # First verify the transaction exists
        txn_result = await self.verification_agent.verify_transaction(
            transaction_id, customer_id, card_number
        )
        
        if not txn_result.get("success"):
            return txn_result
            
        # If transaction is valid, proceed with dispute decision
        dispute_result = await self.dispute_decision_agent.process_dispute(
            transaction_data=txn_result["transaction"]
        )
        
        return {
            "success": True,
            "transaction": txn_result["transaction"],
            "dispute_case": dispute_result
        }

    async def get_case_status(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve case status by case ID using Case Query Agent.
        
        Args:
            case_id: Unique case identifier
            
        Returns:
            Case data if found, None otherwise
        """
        result = await self.case_query_agent.get_case(case_id)
        if result.get("success"):
            return result.get("case")
        return None

    async def get_customer_cases(self, customer_id: str) -> List[Dict[str, Any]]:
        """Retrieve all cases for a customer using Case Query Agent.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            List of case data dictionaries
        """
        result = await self.case_query_agent.get_customer_cases(customer_id)
        return result.get("cases", [])


# Global crew instance for FastAPI integration
_crew_instance: Optional[DisputeResolutionCrew] = None


def get_crew_instance(aws_region: str = "us-east-1", use_mcp_http: bool = False, mcp_url: Optional[str] = None) -> DisputeResolutionCrew:
    """Get or create the global crew instance.
    
    Args:
        aws_region: AWS region for DynamoDB
        use_mcp_http: Whether to use HTTP-based MCP (separate service)
        mcp_url: URL of MCP HTTP server (default: http://localhost:8001)
        
    Returns:
        DisputeResolutionCrew instance
    """
    global _crew_instance
    if _crew_instance is None:
        _crew_instance = DisputeResolutionCrew(
            aws_region=aws_region,
            use_mcp_http=use_mcp_http,
            mcp_url=mcp_url
        )
    return _crew_instance