"""
Dispute Decision Agent for processing dispute cases based on business rules.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..llm_config import get_bedrock_llm_config
from mcp.tools import DynamoQueryCreatorTool, MCPHttpClientTool

logger = logging.getLogger(__name__)


class DisputeProcessingInput(BaseModel):
    """Input model for dispute processing."""
    transaction_data: Dict[str, Any] = Field(description="Transaction data to process for dispute")


class DisputeCaseCreationTool(BaseTool):
    """Tool for creating and managing dispute cases."""

    name: str = "dispute_case_creation"
    description: str = "Create and persist dispute cases in the case database"
    db_client: Any = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, db_client, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)

    def _run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dispute case."""
        try:
            case_id = str(uuid.uuid4())
            case_data["case_id"] = case_id
            case_data["created_at"] = datetime.utcnow().isoformat()
            case_data["updated_at"] = datetime.utcnow().isoformat()

            # Persist case to database
            success = self.db_client.create_case(case_data)

            if success:
                return {
                    "success": True,
                    "case_id": case_id,
                    "case_data": case_data,
                    "message": f"Case {case_id} created successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create case in database"
                }

        except Exception as e:
            logger.error(f"Error creating dispute case: {e}")
            return {
                "success": False,
                "message": f"Error creating case: {str(e)}"
            }


class DisputeDecisionAgent:
    """Agent responsible for making dispute decisions based on business rules."""

    # Business rule constants
    TIME_BARRED_DAYS = 600
    AUTO_RESOLVE_AMOUNT_USD = 100.0

    # Case status constants
    STATUS_REJECTED_TIME_BARRED = "REJECTED_TIME_BARRED"
    STATUS_RESOLVED_CUSTOMER = "RESOLVED_CUSTOMER"
    STATUS_FORWARDED_TO_ACQUIRER = "FORWARDED_TO_ACQUIRER"

    # Credit type constants
    CREDIT_TYPE_PERMANENT = "PERMANENT"  # For amounts ≤ $100
    CREDIT_TYPE_TEMPORARY = "TEMPORARY"  # For amounts > $100 pending investigation

    def __init__(self, db_client, use_mcp_http: bool = False, mcp_url: str = None):
        """Initialize the dispute decision agent.

        Args:
            db_client: DynamoDB client instance
            use_mcp_http: If True, use HTTP-based MCP server, else direct Python calls
            mcp_url: URL of MCP HTTP server (default: http://localhost:8001)
        """
        self.db_client = db_client
        self.use_mcp_http = use_mcp_http

        # Initialize tools
        self.case_creation_tool = DisputeCaseCreationTool(db_client)

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
            role="Dispute Resolution Specialist",
            goal="Apply business rules to determine dispute case outcomes and create appropriate case records using database query capabilities",
            backstory=f"""You are an experienced dispute resolution specialist with deep knowledge of
            payment card industry regulations and business rules. You have been handling financial disputes
            for years and understand the nuances of different dispute scenarios. Your decisions are based
            on established business rules: transactions older than 600 days are automatically time-barred,
            small amounts under $100 are resolved in favor of the customer with a PERMANENT credit for efficiency,
            and larger transactions above $100 receive a TEMPORARY credit while being forwarded to the acquirer
            for detailed investigation. The temporary credit protects the customer during the investigation period
            and may be reversed if the acquirer's investigation determines the transaction was valid. You can also
            create custom database queries {'(via separate MCP HTTP server)' if use_mcp_http else '(in-process)'}
            to retrieve historical dispute data or analyze patterns. You are known for your consistency,
            attention to detail, and adherence to regulatory compliance.""",
            tools=[
                self.case_creation_tool,
                self.dynamo_query_tool  # Can be either stdio or direct
            ],
            llm=bedrock_config['model'],  # e.g., "anthropic.claude-haiku-4-5-20251001-v1:0"
            verbose=True,
            allow_delegation=False
        )

    def get_agent(self) -> Agent:
        """Return the CrewAI agent instance."""
        return self._agent

    def _calculate_transaction_age_days(self, transaction_date: str) -> int:
        """Calculate the age of a transaction in days.

        Args:
            transaction_date: Transaction date in ISO format

        Returns:
            Number of days since the transaction
        """
        try:
            # Parse transaction date (assuming ISO format)
            txn_date = datetime.fromisoformat(transaction_date.replace('Z', '+00:00'))
            current_date = datetime.utcnow().replace(tzinfo=txn_date.tzinfo)

            age_days = (current_date - txn_date).days
            logger.info(f"Transaction age calculated: {age_days} days")
            return age_days

        except Exception as e:
            logger.error(f"Error calculating transaction age: {e}")
            # If we can't parse the date, assume it's recent to be safe
            return 0

    def _extract_amount_usd(self, transaction_data: Dict[str, Any]) -> float:
        """Extract transaction amount in USD.

        Args:
            transaction_data: Transaction details

        Returns:
            Transaction amount as float
        """
        try:
            # Try different possible amount field names
            amount_fields = ['amount_usd', 'amount', 'transaction_amount', 'value']

            for field in amount_fields:
                if field in transaction_data:
                    amount = transaction_data[field]
                    # Handle string amounts
                    if isinstance(amount, str):
                        # Remove currency symbols and convert
                        clean_amount = amount.replace('$', '').replace(',', '').strip()
                        return float(clean_amount)
                    # Handle numeric amounts
                    elif isinstance(amount, (int, float, Decimal)):
                        return float(amount)

            # If no amount field found, log warning and assume high amount
            logger.warning("No amount field found in transaction data")
            return 999999.0  # High amount to trigger manual review

        except Exception as e:
            logger.error(f"Error extracting amount: {e}")
            return 999999.0  # High amount to trigger manual review

    def _determine_case_status(self, transaction_data: Dict[str, Any]) -> tuple[str, str, Optional[str], Optional[float]]:
        """Determine the appropriate case status based on business rules.

        Args:
            transaction_data: Transaction details

        Returns:
            Tuple of (status, reason, credit_type, credit_amount)
        """
        # Extract transaction details
        transaction_date = transaction_data.get('transaction_date', transaction_data.get('date', ''))
        amount_usd = self._extract_amount_usd(transaction_data)

        # Calculate transaction age
        age_days = self._calculate_transaction_age_days(transaction_date)

        logger.info(f"Dispute decision factors - Age: {age_days} days, Amount: ${amount_usd}")

        # Apply business rules in order of precedence

        # Rule 1: Time-barred transactions (> 600 days) - No credit
        if age_days > self.TIME_BARRED_DAYS:
            return (
                self.STATUS_REJECTED_TIME_BARRED,
                f"Transaction is {age_days} days old, exceeding the {self.TIME_BARRED_DAYS} day limit",
                None,  # No credit
                None   # No amount
            )

        # Rule 2: Auto-resolve small amounts (≤ $100 USD and within time limit) - PERMANENT credit
        if age_days <= self.TIME_BARRED_DAYS and amount_usd <= self.AUTO_RESOLVE_AMOUNT_USD:
            return (
                self.STATUS_RESOLVED_CUSTOMER,
                f"Small amount dispute (${amount_usd}) resolved in customer's favor with permanent credit",
                self.CREDIT_TYPE_PERMANENT,
                amount_usd
            )

        # Rule 3: Forward larger amounts to acquirer (> $100 USD) - TEMPORARY credit
        return (
            self.STATUS_FORWARDED_TO_ACQUIRER,
            f"Amount ${amount_usd} forwarded to acquirer for investigation with temporary credit issued",
            self.CREDIT_TYPE_TEMPORARY,
            amount_usd
        )

    async def process_dispute(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a dispute case based on business rules.

        Args:
            transaction_data: Complete transaction details

        Returns:
            Dict containing case creation result and decision details
        """
        transaction_id = transaction_data.get('transaction_id', 'unknown')
        logger.info(f"Processing dispute for transaction: {transaction_id}")

        try:
            # Check if an open case already exists for this transaction
            existing_case = await self.db_client.get_open_case_for_transaction(transaction_id)

            if existing_case:
                logger.info(f"Open case already exists for transaction {transaction_id}: {existing_case.get('case_id')}")
                return {
                    "case_id": existing_case.get("case_id"),
                    "customer_id": existing_case.get("customer_id"),
                    "card_id": existing_case.get("card_id"),
                    "transaction_id": existing_case.get("transaction_id"),
                    "dispute_status": existing_case.get("dispute_status"),
                    "decision_reason": existing_case.get("decision_reason"),
                    "created_at": existing_case.get("created_at"),
                    "updated_at": existing_case.get("updated_at"),
                    "auto_decided": existing_case.get("auto_decided", False),
                    "requires_manual_review": existing_case.get("requires_manual_review", False),
                    "existing_case": True,
                    "message": "An open dispute case already exists for this transaction"
                }

            # No existing case, proceed with creating a new one
            # Determine case status based on business rules
            status, reason, credit_type, credit_amount = self._determine_case_status(transaction_data)

            # Credit Policy:
            # - Amounts ≤ $100: PERMANENT credit (customer keeps the money)
            # - Amounts > $100: TEMPORARY credit (may be reversed after acquirer investigation)
            # - Time-barred cases: No credit issued

            # Prepare case data
            case_data = {
                "customer_id": transaction_data.get("customer_id"),
                "card_id": transaction_data.get("card_id"),
                "transaction_id": transaction_data.get("transaction_id"),
                "transaction_date": transaction_data.get("transaction_date", transaction_data.get("date")),
                "transaction_amount": self._extract_amount_usd(transaction_data),
                "merchant": transaction_data.get("merchant", "Unknown"),
                "dispute_status": status,
                "decision_reason": reason,
                "auto_decided": True,
                "requires_manual_review": status == self.STATUS_FORWARDED_TO_ACQUIRER,
                "credit_type": credit_type,  # PERMANENT, TEMPORARY, or None
                "credit_amount": credit_amount,  # Amount credited or None
                "credit_issued": credit_type is not None  # Boolean flag
            }

            # Create the case
            result = self.case_creation_tool._run(case_data)

            if result["success"]:
                logger.info(f"Dispute case created successfully: {result['case_id']} with status {status}")
                if credit_type:
                    logger.info(f"Credit issued: {credit_type} credit of ${credit_amount}")

                # Return the full case data with the structure expected by the frontend
                return {
                    "case_id": result["case_id"],
                    "customer_id": case_data["customer_id"],
                    "card_id": case_data["card_id"],
                    "transaction_id": case_data["transaction_id"],
                    "dispute_status": status,
                    "decision_reason": reason,
                    "created_at": result["case_data"]["created_at"],
                    "updated_at": result["case_data"]["updated_at"],
                    "auto_decided": True,
                    "requires_manual_review": status == self.STATUS_FORWARDED_TO_ACQUIRER,
                    "credit_type": credit_type,
                    "credit_amount": credit_amount,
                    "credit_issued": credit_type is not None,
                    "existing_case": False
                }
            else:
                logger.error(f"Failed to create dispute case: {result['message']}")
                return {
                    "case_id": None,
                    "dispute_status": "ERROR",
                    "decision_reason": f"Failed to create dispute case: {result['message']}"
                }

        except Exception as e:
            logger.error(f"Error processing dispute: {e}")
            return {
                "success": False,
                "message": f"Error processing dispute: {str(e)}"
            }

    async def get_case_details(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed case information.

        Args:
            case_id: Unique case identifier

        Returns:
            Case details if found, None otherwise
        """
        try:
            case_data = await self.db_client.get_case(case_id)
            return case_data
        except Exception as e:
            logger.error(f"Error retrieving case {case_id}: {e}")
            return None