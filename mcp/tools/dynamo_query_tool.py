"""
DynamoDB Query Creator Tool for MCP.
This tool allows agents to dynamically create and execute DynamoDB queries.
"""

from typing import Dict, Any, Optional, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
import json

logger = logging.getLogger(__name__)


class DynamoQueryInput(BaseModel):
    """Input model for DynamoDB query creation."""
    table_name: str = Field(description="DynamoDB table name to query")
    operation: str = Field(description="Operation type: 'query', 'get_item', 'scan', 'put_item', 'update_item'")
    key_condition: Optional[Dict[str, Any]] = Field(None, description="Key condition for query (e.g., {'customer_id': 'C123'})")
    filter_expression: Optional[Dict[str, Any]] = Field(None, description="Additional filter conditions")
    index_name: Optional[str] = Field(None, description="GSI name if querying an index")
    attributes_to_get: Optional[List[str]] = Field(None, description="Specific attributes to retrieve")
    limit: Optional[int] = Field(None, description="Maximum number of items to return")
    item_data: Optional[Dict[str, Any]] = Field(None, description="Item data for put_item operation")
    update_expression: Optional[Dict[str, Any]] = Field(None, description="Update expression for update_item")


class DynamoQueryCreatorTool(BaseTool):
    """
    MCP Tool for creating and executing DynamoDB queries dynamically.
    
    This tool allows agents to:
    - Build complex DynamoDB queries on the fly
    - Query multiple tables and indexes
    - Filter and transform results
    - Create, update, and retrieve items
    """
    
    name: str = "dynamo_query_creator"
    description: str = """
    Create and execute DynamoDB queries dynamically. 
    Supports: query, get_item, scan, put_item, update_item operations.
    Can query tables: 'ptr_dispute_resol_customer_cards_and_transactions', 'ptr_dispute_resol_case_db'.
    Can use indexes: 'TransactionIndex' (on transaction_id), 'CustomerIndex' (on customer_id).
    """
    db_client: Any = Field(default=None, exclude=True)
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, db_client, **kwargs):
        """Initialize the DynamoDB query creator tool.
        
        Args:
            db_client: DynamoDBClient instance for executing queries
        """
        super().__init__(**kwargs)
        object.__setattr__(self, 'db_client', db_client)
        logger.info("DynamoDB Query Creator Tool initialized")
    
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
        Execute a DynamoDB query based on the provided parameters.
        
        Args:
            table_name: Name of the DynamoDB table
            operation: Type of operation (query, get_item, scan, put_item, update_item)
            key_condition: Primary key condition (e.g., {'customer_id': 'C123'})
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
            logger.info(f"Executing DynamoDB {operation} on table {table_name}")
            logger.debug(f"Parameters: key_condition={key_condition}, index_name={index_name}")
            
            # Validate table name
            valid_tables = [
                "ptr_dispute_resol_customer_cards_and_transactions",
                "ptr_dispute_resol_case_db"
            ]
            if table_name not in valid_tables:
                return {
                    "success": False,
                    "error": f"Invalid table name. Must be one of: {valid_tables}"
                }
            
            # Get the appropriate table
            if table_name == "ptr_dispute_resol_customer_cards_and_transactions":
                table = self.db_client.cards_table
            else:
                table = self.db_client.case_table
            
            # Execute based on operation type
            if operation == "query":
                return self._execute_query(
                    table, key_condition, filter_expression, 
                    index_name, attributes_to_get, limit
                )
            elif operation == "get_item":
                return self._execute_get_item(table, key_condition)
            elif operation == "scan":
                return self._execute_scan(
                    table, filter_expression, attributes_to_get, limit
                )
            elif operation == "put_item":
                return self._execute_put_item(table, item_data)
            elif operation == "update_item":
                return self._execute_update_item(
                    table, key_condition, update_expression
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing DynamoDB query: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to execute DynamoDB query"
            }
    
    def _execute_query(
        self,
        table,
        key_condition: Dict[str, Any],
        filter_expression: Optional[Dict[str, Any]],
        index_name: Optional[str],
        attributes_to_get: Optional[List[str]],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a DynamoDB query operation."""
        try:
            from boto3.dynamodb.conditions import Key, Attr
            
            # Build key condition expression
            if not key_condition:
                return {"success": False, "error": "key_condition required for query"}
            
            # Build the key condition
            key_expr = None
            for key, value in key_condition.items():
                if isinstance(value, dict):
                    # Handle complex conditions like begins_with
                    if 'begins_with' in value:
                        key_expr = Key(key).begins_with(value['begins_with'])
                    elif 'between' in value:
                        key_expr = Key(key).between(value['between'][0], value['between'][1])
                else:
                    # Simple equality
                    if key_expr is None:
                        key_expr = Key(key).eq(value)
                    else:
                        key_expr = key_expr & Key(key).eq(value)
            
            # Build query parameters
            query_params = {
                'KeyConditionExpression': key_expr
            }
            
            if index_name:
                query_params['IndexName'] = index_name
            
            if attributes_to_get:
                query_params['ProjectionExpression'] = ', '.join(attributes_to_get)
            
            if limit:
                query_params['Limit'] = limit
            
            # Add filter expression if provided
            if filter_expression:
                filter_expr = None
                for key, value in filter_expression.items():
                    if filter_expr is None:
                        filter_expr = Attr(key).eq(value)
                    else:
                        filter_expr = filter_expr & Attr(key).eq(value)
                query_params['FilterExpression'] = filter_expr
            
            # Execute query
            response = table.query(**query_params)
            items = response.get('Items', [])
            
            logger.info(f"Query returned {len(items)} items")
            
            return {
                "success": True,
                "items": items,
                "count": len(items),
                "scanned_count": response.get('ScannedCount', len(items))
            }
            
        except Exception as e:
            logger.error(f"Error in query execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_get_item(
        self,
        table,
        key_condition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a DynamoDB get_item operation."""
        try:
            if not key_condition:
                return {"success": False, "error": "key_condition required for get_item"}
            
            response = table.get_item(Key=key_condition)
            
            if 'Item' in response:
                return {
                    "success": True,
                    "item": response['Item']
                }
            else:
                return {
                    "success": False,
                    "message": "Item not found"
                }
                
        except Exception as e:
            logger.error(f"Error in get_item execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_scan(
        self,
        table,
        filter_expression: Optional[Dict[str, Any]],
        attributes_to_get: Optional[List[str]],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a DynamoDB scan operation."""
        try:
            from boto3.dynamodb.conditions import Attr
            
            scan_params = {}
            
            if attributes_to_get:
                scan_params['ProjectionExpression'] = ', '.join(attributes_to_get)
            
            if limit:
                scan_params['Limit'] = limit
            
            if filter_expression:
                filter_expr = None
                for key, value in filter_expression.items():
                    if filter_expr is None:
                        filter_expr = Attr(key).eq(value)
                    else:
                        filter_expr = filter_expr & Attr(key).eq(value)
                scan_params['FilterExpression'] = filter_expr
            
            response = table.scan(**scan_params)
            items = response.get('Items', [])
            
            logger.info(f"Scan returned {len(items)} items")
            
            return {
                "success": True,
                "items": items,
                "count": len(items),
                "scanned_count": response.get('ScannedCount', len(items))
            }
            
        except Exception as e:
            logger.error(f"Error in scan execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_put_item(
        self,
        table,
        item_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a DynamoDB put_item operation."""
        try:
            if not item_data:
                return {"success": False, "error": "item_data required for put_item"}
            
            # Convert floats to Decimal for DynamoDB
            from crew_ai_app.db.dynamo_client import convert_floats_to_decimal
            converted_data = convert_floats_to_decimal(item_data)
            
            table.put_item(Item=converted_data)
            
            logger.info(f"Item created successfully")
            
            return {
                "success": True,
                "message": "Item created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in put_item execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_update_item(
        self,
        table,
        key_condition: Dict[str, Any],
        update_expression: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a DynamoDB update_item operation."""
        try:
            if not key_condition:
                return {"success": False, "error": "key_condition required for update_item"}
            
            if not update_expression:
                return {"success": False, "error": "update_expression required for update_item"}
            
            # Build update expression
            update_expr = "SET "
            expr_values = {}
            expr_names = {}
            
            for key, value in update_expression.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expr += f"{attr_name} = {attr_value}, "
                expr_names[attr_name] = key
                expr_values[attr_value] = value
            
            update_expr = update_expr.rstrip(", ")
            
            # Add timestamp
            from datetime import datetime
            expr_names["#updated_at"] = "updated_at"
            expr_values[":updated_at"] = datetime.utcnow().isoformat()
            update_expr += ", #updated_at = :updated_at"
            
            table.update_item(
                Key=key_condition,
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            
            logger.info("Item updated successfully")
            
            return {
                "success": True,
                "message": "Item updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in update_item execution: {e}")
            return {"success": False, "error": str(e)}
