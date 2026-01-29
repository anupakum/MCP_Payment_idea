"""
DynamoDB client for accessing dispute resolution data.
Provides interfaces to customer cards/transactions and case management tables.
"""

import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import asyncio
from functools import wraps
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB compatibility.
    
    Args:
        obj: Object to convert (can be dict, list, or primitive)
        
    Returns:
        Object with floats converted to Decimal
    """
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))  # Convert to string first to avoid precision issues
    else:
        return obj


def async_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying async operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except ClientError as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(f"Throttling detected, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay)
            
        return wrapper
    return decorator


class DynamoDBClient:
    """Client for interacting with DynamoDB tables for dispute resolution."""

    # Table names
    CARDS_TRANSACTIONS_TABLE = "ptr_dispute_resol_customer_cards_and_transactions"
    CASE_DB_TABLE = "ptr_dispute_resol_case_db"

    def __init__(self, region: str = "us-east-1"):
        """Initialize DynamoDB client.
        
        Args:
            region: AWS region for DynamoDB access
        """
        self.region = region
        
        try:
            # Initialize DynamoDB client
            self.dynamodb = boto3.client('dynamodb', region_name=region)
            self.dynamodb_resource = boto3.resource('dynamodb', region_name=region)
            
            # Get table references
            self.cards_table = self.dynamodb_resource.Table(self.CARDS_TRANSACTIONS_TABLE)
            self.case_table = self.dynamodb_resource.Table(self.CASE_DB_TABLE)
            
            logger.info(f"DynamoDB client initialized for region: {region}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Error initializing DynamoDB client: {e}")
            raise

    @async_retry(max_attempts=3, delay=0.5)
    async def get_customer_cards(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve customer and associated cards.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Customer data with cards list, or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Use boto3.dynamodb.conditions.Key for proper query expression
            from boto3.dynamodb.conditions import Key
            
            # Query all records for this customer using partition key
            response = await loop.run_in_executor(
                None,
                lambda: self.cards_table.query(
                    KeyConditionExpression=Key('customer_id').eq(customer_id)
                )
            )
            
            items = response.get('Items', [])
            if items:
                # Group cards by card_number
                # composite_key format: {card_number}#{transaction_id}
                cards_dict = {}
                for item in items:
                    card_num = item.get('card_number')
                    if card_num not in cards_dict:
                        cards_dict[card_num] = {
                            'card_number': card_num,
                            'card_type': item.get('card_type'),
                            'card_status': item.get('card_status'),
                            'cardholder_name': item.get('cardholder_name'),
                            'expiry_date': item.get('expiry_date'),
                            'transactions': []
                        }
                    
                    # Add transaction if present
                    if item.get('transaction_id'):
                        cards_dict[card_num]['transactions'].append({
                            'transaction_id': item.get('transaction_id'),
                            'amount': float(item.get('amount', 0)),
                            'currency': item.get('currency'),
                            'transaction_date': item.get('transaction_date'),
                            'merchant': item.get('merchant'),
                            'description': item.get('description'),
                            'status': item.get('status')
                        })
                
                customer_data = {
                    'customer_id': customer_id,
                    'cardholder_name': items[0].get('cardholder_name'),
                    'cards': list(cards_dict.values())
                }
                
                logger.info(f"Found customer {customer_id} with {len(cards_dict)} cards")
                return customer_data
            else:
                logger.info(f"Customer {customer_id} not found")
                return None
                
        except ClientError as e:
            logger.error(f"DynamoDB error getting customer {customer_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting customer {customer_id}: {e}")
            raise

    @async_retry(max_attempts=3, delay=0.5)
    async def get_card_transactions(self, customer_id: str, card_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve card and associated transactions.
        
        Args:
            customer_id: Customer identifier
            card_number: Card number
            
        Returns:
            Card data with transactions list, or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Query specific card transactions using composite key prefix
            # composite_key format: {card_number}#{transaction_id}
            # Note: The actual DynamoDB structure doesn't have "CARD#" prefix
            composite_key_prefix = f"{card_number}#"
            
            logger.info(f"Querying for customer_id={customer_id}, composite_key prefix={composite_key_prefix}")
            
            # Use boto3.dynamodb.conditions.Key for proper query expression
            from boto3.dynamodb.conditions import Key
            
            response = await loop.run_in_executor(
                None,
                lambda: self.cards_table.query(
                    KeyConditionExpression=Key('customer_id').eq(customer_id) & Key('composite_key').begins_with(composite_key_prefix)
                )
            )
            
            items = response.get('Items', [])
            logger.info(f"Query returned {len(items)} items for card {card_number}")
            
            # Debug: print first item structure if available
            if items:
                logger.info(f"First item composite_key: {items[0].get('composite_key')}")
            
            if items:
                # First item has card details
                first_item = items[0]
                transactions = []
                
                for item in items:
                    if item.get('transaction_id'):
                        transactions.append({
                            'transaction_id': item.get('transaction_id'),
                            'amount': float(item.get('amount', 0)),
                            'currency': item.get('currency'),
                            'transaction_date': item.get('transaction_date'),
                            'merchant': item.get('merchant'),
                            'description': item.get('description'),
                            'status': item.get('status')
                        })
                
                card_data = {
                    'card_number': card_number,
                    'customer_id': customer_id,
                    'card_type': first_item.get('card_type'),
                    'card_status': first_item.get('card_status'),
                    'cardholder_name': first_item.get('cardholder_name'),
                    'expiry_date': first_item.get('expiry_date'),
                    'transactions': transactions
                }
                
                logger.info(f"Found card {card_number} with {len(transactions)} transactions")
                return card_data
            else:
                logger.info(f"Card {card_number} not found for customer {customer_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting card transactions: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error getting card transactions: {e}")
            raise

    @async_retry(max_attempts=3, delay=0.5)
    async def get_transaction(
        self, 
        transaction_id: str,
        customer_id: Optional[str] = None, 
        card_number: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve specific transaction details using TransactionIndex GSI.
        
        Args:
            transaction_id: Transaction identifier (required)
            customer_id: Customer identifier (optional, for validation)
            card_number: Card number (optional, for validation)
            
        Returns:
            Transaction data or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Use boto3.dynamodb.conditions.Key for proper query expression
            from boto3.dynamodb.conditions import Key
            
            # Query using TransactionIndex GSI
            response = await loop.run_in_executor(
                None,
                lambda: self.cards_table.query(
                    IndexName='TransactionIndex',
                    KeyConditionExpression=Key('transaction_id').eq(transaction_id)
                )
            )
            
            items = response.get('Items', [])
            if items:
                item = items[0]  # Transaction ID should be unique
                
                # Validate customer_id and card_number if provided
                if customer_id and item.get('customer_id') != customer_id:
                    logger.warning(f"Transaction {transaction_id} does not belong to customer {customer_id}")
                    return None
                    
                if card_number and item.get('card_number') != card_number:
                    logger.warning(f"Transaction {transaction_id} does not belong to card {card_number}")
                    return None
                
                transaction_data = {
                    'transaction_id': item.get('transaction_id'),
                    'customer_id': item.get('customer_id'),
                    'card_number': item.get('card_number'),
                    'card_type': item.get('card_type'),
                    'cardholder_name': item.get('cardholder_name'),
                    'amount': float(item.get('amount', 0)),
                    'currency': item.get('currency'),
                    'transaction_date': item.get('transaction_date'),
                    'merchant': item.get('merchant'),
                    'description': item.get('description'),
                    'status': item.get('status')
                }
                
                logger.info(f"Found transaction {transaction_id}")
                return transaction_data
            
            logger.info(f"Transaction {transaction_id} not found")
            return None
                
        except Exception as e:
            logger.error(f"Error getting transaction: {e}")
            raise

    def create_case(self, case_data: Dict[str, Any]) -> bool:
        """Create a new dispute case (synchronous for tool compatibility).
        
        Args:
            case_data: Complete case information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert floats to Decimal for DynamoDB compatibility
            converted_data = convert_floats_to_decimal(case_data)
            
            # Put item in case database table
            self.case_table.put_item(Item=converted_data)
            logger.info(f"Case {case_data.get('case_id')} created successfully")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB error creating case: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating case: {e}")
            return False

    @async_retry(max_attempts=3, delay=0.5)
    async def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve case by case ID.
        
        Args:
            case_id: Unique case identifier
            
        Returns:
            Case data or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.case_table.get_item(
                    Key={'case_id': case_id}
                )
            )
            
            if 'Item' in response:
                logger.info(f"Found case {case_id}")
                return response['Item']
            else:
                logger.info(f"Case {case_id} not found")
                return None
                
        except ClientError as e:
            logger.error(f"DynamoDB error getting case {case_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting case {case_id}: {e}")
            raise

    @async_retry(max_attempts=3, delay=0.5) 
    async def update_case(self, case_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing case.
        
        Args:
            case_id: Case identifier to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Convert floats to Decimal for DynamoDB
            updates = convert_floats_to_decimal(updates)
            
            # Build update expression
            update_expression = "SET "
            expression_values = {}
            expression_names = {}
            
            for key, value in updates.items():
                # Handle reserved keywords by using expression attribute names
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expression += f"{attr_name} = {attr_value}, "
                expression_names[attr_name] = key
                expression_values[attr_value] = value
            
            # Remove trailing comma and space
            update_expression = update_expression.rstrip(", ")
            
            # Add updated timestamp
            expression_names["#updated_at"] = "updated_at"
            expression_values[":updated_at"] = datetime.utcnow().isoformat()
            update_expression += ", #updated_at = :updated_at"
            
            await loop.run_in_executor(
                None,
                lambda: self.case_table.update_item(
                    Key={'case_id': case_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeNames=expression_names,
                    ExpressionAttributeValues=expression_values
                )
            )
            
            logger.info(f"Case {case_id} updated successfully")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB error updating case {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating case {case_id}: {e}")
            return False

    async def get_case_by_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve case by transaction ID using GSI.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Case data or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Use boto3.dynamodb.conditions.Key for proper query expression
            from boto3.dynamodb.conditions import Key
            
            # Query using TransactionIndex GSI
            response = await loop.run_in_executor(
                None,
                lambda: self.case_table.query(
                    IndexName='TransactionIndex',
                    KeyConditionExpression=Key('transaction_id').eq(transaction_id),
                    ScanIndexForward=False  # Latest first
                )
            )
            
            items = response.get('Items', [])
            if items:
                logger.info(f"Found case for transaction {transaction_id}")
                return items[0]  # Return most recent case for this transaction
            else:
                logger.info(f"No case found for transaction {transaction_id}")
                return None
                
        except ClientError as e:
            logger.error(f"DynamoDB error getting case by transaction {transaction_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting case by transaction {transaction_id}: {e}")
            return None

    async def get_open_case_for_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Check if an open/active case exists for a transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Open case data or None if no open case exists
        """
        try:
            case = await self.get_case_by_transaction(transaction_id)
            
            if not case:
                return None
            
            # Check if case is still open (not resolved/closed)
            status = case.get('dispute_status', '')
            closed_statuses = ['RESOLVED_CUSTOMER', 'RESOLVED_ACQUIRER', 'CLOSED', 'REJECTED_TIME_BARRED']
            
            if status not in closed_statuses:
                logger.info(f"Found open case {case.get('case_id')} for transaction {transaction_id}")
                return case
            else:
                logger.info(f"Case {case.get('case_id')} for transaction {transaction_id} is closed (status: {status})")
                return None
                
        except Exception as e:
            logger.error(f"Error checking for open case: {e}")
            return None

    async def list_cases_by_customer(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List cases for a specific customer.
        
        Args:
            customer_id: Customer identifier
            limit: Maximum number of cases to return
            
        Returns:
            List of case data dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Use boto3.dynamodb.conditions.Key for proper query expression
            from boto3.dynamodb.conditions import Key
            
            # Query cases by customer_id using CustomerIndex GSI
            response = await loop.run_in_executor(
                None,
                lambda: self.case_table.query(
                    IndexName='CustomerIndex',  # Correct GSI name from table definition
                    KeyConditionExpression=Key('customer_id').eq(customer_id),
                    Limit=limit,
                    ScanIndexForward=False  # Latest cases first
                )
            )
            
            cases = response.get('Items', [])
            logger.info(f"Found {len(cases)} cases for customer {customer_id}")
            return cases
            
        except ClientError as e:
            logger.error(f"DynamoDB error listing cases for customer {customer_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing cases for customer {customer_id}: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on DynamoDB connections.
        
        Returns:
            Health status information
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Test connection to both tables
            cards_table_status = await loop.run_in_executor(
                None,
                lambda: self.cards_table.table_status
            )
            
            case_table_status = await loop.run_in_executor(
                None,
                lambda: self.case_table.table_status
            )
            
            return {
                "status": "healthy",
                "region": self.region,
                "cards_table": {
                    "name": self.CARDS_TRANSACTIONS_TABLE,
                    "status": cards_table_status
                },
                "case_table": {
                    "name": self.CASE_DB_TABLE, 
                    "status": case_table_status
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "region": self.region
            }