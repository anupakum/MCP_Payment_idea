"""
Verification Agent for customer, card, and transaction validation.
"""

import logging
import asyncio

# Disable uvloop to prevent conflicts with asyncio
# This ensures compatibility across platforms (Windows/Linux) and prevents event loop issues
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
    logger.warning(f"Warning: Could not handle uvloop in verification_agent: {e}")

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

from typing import Dict, Any, List, Optional
from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..llm_config import get_bedrock_llm_config
from mcp.tools import DynamoQueryCreatorTool, MCPHttpClientTool


class CustomerVerificationInput(BaseModel):
    """Input model for customer verification."""
    customer_id: str = Field(description="Customer ID to verify")


class CardVerificationInput(BaseModel):
    """Input model for card verification."""
    customer_id: str = Field(description="Customer ID")
    card_number: str = Field(description="Card number to verify")


class TransactionVerificationInput(BaseModel):
    """Input model for transaction verification."""
    transaction_id: str = Field(description="Transaction ID to verify")
    customer_id: Optional[str] = Field(None, description="Customer ID (optional for validation)")
    card_number: Optional[str] = Field(None, description="Card number (optional for validation)")


class CustomerLookupTool(BaseTool):
    """Tool for looking up customer data."""

    name: str = "customer_lookup"
    description: str = "Look up customer by ID and return associated cards"
    db_client: Any = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)

    def _run(self, customer_id: str) -> Dict[str, Any]:
        """Execute customer lookup."""
        try:
            import asyncio

            # Handle running loop properly (nest_asyncio patch already applied at module level)
            try:
                # Try to get running loop first
                loop = asyncio.get_running_loop()
                # With nest_asyncio applied, we can run_until_complete even in running loop
                customer_data = loop.run_until_complete(self.db_client.get_customer_cards(customer_id))
            except RuntimeError:
                # No running loop, create a new one and use run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                customer_data = loop.run_until_complete(self.db_client.get_customer_cards(customer_id))

            if customer_data:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "cards": customer_data.get("cards", []),
                    "message": f"Found {len(customer_data.get('cards', []))} cards for customer"
                }
            else:
                return {
                    "success": False,
                    "message": "Customer not found, please retry"
                }
        except Exception as e:
            logger.error(f"Error looking up customer {customer_id}: {e}")
            return {
                "success": False,
                "message": f"Error retrieving customer data: {str(e)}"
            }


class CardLookupTool(BaseTool):
    """Tool for looking up card and associated transactions."""

    name: str = "card_lookup"
    description: str = "Look up card by customer and card number, return transactions"
    db_client: Any = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)

    def _run(self, customer_id: str, card_number: str) -> Dict[str, Any]:
        """Execute card lookup."""
        try:
            import asyncio

            # Handle running loop properly (nest_asyncio patch already applied at module level)
            try:
                # Try to get running loop first
                loop = asyncio.get_running_loop()
                # With nest_asyncio applied, we can run_until_complete even in running loop
                card_data = loop.run_until_complete(self.db_client.get_card_transactions(customer_id, card_number))
            except RuntimeError:
                # No running loop, create a new one and use run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                card_data = loop.run_until_complete(self.db_client.get_card_transactions(customer_id, card_number))

            if card_data:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "card_number": card_number,
                    "transactions": card_data.get("transactions", []),
                    "message": f"Found {len(card_data.get('transactions', []))} transactions for card"
                }
            else:
                return {
                    "success": False,
                    "message": "Card not found"
                }
        except Exception as e:
            logger.error(f"Error looking up card {card_number} for customer {customer_id}: {e}")
            return {
                "success": False,
                "message": f"Error retrieving card data: {str(e)}"
            }


class TransactionLookupTool(BaseTool):
    """Tool for looking up specific transaction details."""

    name: str = "transaction_lookup"
    description: str = "Look up transaction by transaction ID (optionally validate with customer/card)"
    db_client: Any = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)

    def _run(self, transaction_id: str, customer_id: Optional[str] = None, card_number: Optional[str] = None) -> Dict[str, Any]:
        """Execute transaction lookup."""
        try:
            import asyncio

            # Handle running loop properly (nest_asyncio patch already applied at module level)
            try:
                # Try to get running loop first
                loop = asyncio.get_running_loop()
                # With nest_asyncio applied, we can run_until_complete even in running loop
                transaction_data = loop.run_until_complete(self.db_client.get_transaction(
                    transaction_id, customer_id, card_number
                ))
            except RuntimeError:
                # No running loop, create a new one and use run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                transaction_data = loop.run_until_complete(self.db_client.get_transaction(
                    transaction_id, customer_id, card_number
                ))

            if transaction_data:
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "transaction": transaction_data,
                    "message": "Transaction found successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Transaction not found"
                }
        except Exception as e:
            logger.error(f"Error looking up transaction {transaction_id}: {e}")
            return {
                "success": False,
                "message": f"Error retrieving transaction data: {str(e)}"
            }


class VerificationAgent:
    """Agent responsible for verifying customers, cards, and transactions."""

    def __init__(self, db_client, use_mcp_http: bool = False, mcp_url: str = None):
        """Initialize the verification agent.

        Args:
            db_client: DynamoDB client instance
            use_mcp_http: If True, use HTTP-based MCP server, else direct Python calls
            mcp_url: URL of MCP HTTP server (default: http://localhost:8001)
        """
        self.db_client = db_client
        self.use_mcp_http = use_mcp_http

        # Initialize tools
        self.customer_lookup_tool = CustomerLookupTool(db_client)
        self.card_lookup_tool = CardLookupTool(db_client)
        self.transaction_lookup_tool = TransactionLookupTool(db_client)

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
            role="Verification Specialist",
            goal="Verify customer identities, validate card ownership, and confirm transaction details using advanced database query capabilities",
            backstory=f"""You are a meticulous verification specialist working for a financial institution.
            Your expertise lies in quickly and accurately validating customer information, ensuring that
            only legitimate customers can access their financial data. You have access to secure databases
            containing customer profiles, card details, and transaction histories. You can also create
            custom database queries using the DynamoDB Query Creator tool {'(via separate MCP HTTP server)' if use_mcp_http else '(in-process)'}
            to find specific information or perform complex data retrieval operations. Your primary concern
            is data security and accuracy - you never assume or guess information, and you always
            double-check your findings before providing responses.""",
            tools=[
                self.customer_lookup_tool,
                self.card_lookup_tool,
                self.transaction_lookup_tool,
                self.dynamo_query_tool  # Can be either stdio or direct
            ],
            llm=bedrock_config['model'],  # e.g., "anthropic.claude-haiku-4-5-20251001-v1:0"
            verbose=True,
            allow_delegation=False
        )

    def get_agent(self) -> Agent:
        """Return the CrewAI agent instance."""
        return self._agent

    async def verify_customer(self, customer_id: str) -> Dict[str, Any]:
        """Verify customer and return associated cards.

        Args:
            customer_id: Customer ID to verify

        Returns:
            Dict with verification result and card list if successful
        """
        logger.info(f"Verifying customer: {customer_id}")

        try:
            result = self.customer_lookup_tool._run(customer_id)
            logger.info(f"Customer verification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in customer verification: {e}")
            return {
                "success": False,
                "message": f"Verification error: {str(e)}"
            }

    async def verify_card(self, customer_id: str, card_number: str) -> Dict[str, Any]:
        """Verify card belongs to customer and return transactions.

        Args:
            customer_id: Customer ID
            card_number: Card number to verify

        Returns:
            Dict with verification result and transaction list if successful
        """
        logger.info(f"Verifying card {card_number} for customer {customer_id}")

        try:
            result = self.card_lookup_tool._run(customer_id, card_number)
            logger.info(f"Card verification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in card verification: {e}")
            return {
                "success": False,
                "message": f"Card verification error: {str(e)}"
            }

    async def verify_transaction(
        self,
        transaction_id: str,
        customer_id: Optional[str] = None,
        card_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify transaction exists (optionally for the given customer and card).

        Args:
            transaction_id: Transaction ID to verify (required)
            customer_id: Customer ID (optional, for validation)
            card_number: Card number (optional, for validation)

        Returns:
            Dict with verification result and transaction details if successful
        """
        logger.info(f"Verifying transaction {transaction_id}" +
                   (f" for customer {customer_id}" if customer_id else "") +
                   (f" card {card_number}" if card_number else ""))

        try:
            result = self.transaction_lookup_tool._run(transaction_id, customer_id, card_number)
            logger.info(f"Transaction verification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in transaction verification: {e}")
            return {
                "success": False,
                "message": f"Transaction verification error: {str(e)}"
            }