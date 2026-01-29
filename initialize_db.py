import boto3
import os
import time
import sys
import traceback

def init_db():
    log_lines = []
    
    def log(msg):
        log_lines.append(str(msg))

    try:
        # Load env
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ[k] = v

        AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
        dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)

        def create_table(table_name, key_schema, attr_defs, gsi=None):
            try:
                log(f"Creating table: {table_name}...")
                params = {
                    "TableName": table_name,
                    "KeySchema": key_schema,
                    "AttributeDefinitions": attr_defs,
                    "BillingMode": "PAY_PER_REQUEST"
                }
                if gsi:
                    params["GlobalSecondaryIndexes"] = gsi

                dynamodb.create_table(**params)
                log(f" -> Table {table_name} creation initiated.")
                
                # Wait for TABLE to be ACTIVE
                log(" -> Waiting for table to be active...")
                try:
                    waiver = boto3.resource('dynamodb', region_name=AWS_REGION).Table(table_name)
                    waiver.meta.client.get_waiter('table_exists').wait(TableName=table_name)
                    log(f" -> Table {table_name} is now ACTIVE.")
                except Exception as wait_err:
                    log(f" -> Warning waiting for table: {wait_err}")
                
            except dynamodb.exceptions.ResourceInUseException:
                log(f" -> Table {table_name} already exists.")
            except Exception as e:
                log(f" -> Error creating {table_name}: {e}")

        # 1. Cards and Transactions Table
        create_table(
            table_name="ptr_dispute_resol_customer_cards_and_transactions",
            key_schema=[
                {"AttributeName": "customer_id", "KeyType": "HASH"},
                {"AttributeName": "composite_key", "KeyType": "RANGE"}
            ],
            attr_defs=[
                {"AttributeName": "customer_id", "AttributeType": "S"},
                {"AttributeName": "composite_key", "AttributeType": "S"},
                {"AttributeName": "transaction_id", "AttributeType": "S"}
            ],
            gsi=[
                {
                    "IndexName": "TransactionIndex",
                    "KeySchema": [{"AttributeName": "transaction_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ]
        )

        # 2. Cases Table
        create_table(
            table_name="ptr_dispute_resol_case_db",
            key_schema=[
                {"AttributeName": "case_id", "KeyType": "HASH"}
            ],
            attr_defs=[
                {"AttributeName": "case_id", "AttributeType": "S"},
                {"AttributeName": "transaction_id", "AttributeType": "S"},
                {"AttributeName": "customer_id", "AttributeType": "S"}
            ],
            gsi=[
                {
                    "IndexName": "TransactionIndex",
                    "KeySchema": [{"AttributeName": "transaction_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                },
                {
                    "IndexName": "CustomerIndex",
                    "KeySchema": [{"AttributeName": "customer_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ]
        )

        log("\nSeeding Sample Data...")
        # Seed CUST001
        db = boto3.resource('dynamodb', region_name=AWS_REGION)
        table = db.Table("ptr_dispute_resol_customer_cards_and_transactions")

        # Sample Data
        items = [
            {
                "customer_id": "CUST001",
                "composite_key": "CARD#1234",
                "card_number": "1234",
                "cardholder_name": "John Doe",
                "card_type": "Visa",
                "card_status": "Active",
                "expiry_date": "12/28"
            },
            {
                "customer_id": "CUST001",
                "composite_key": "CARD#1234#TXN001",
                "card_number": "1234",
                "transaction_id": "TXN001",
                "amount": "99.00",
                "currency": "USD",
                "merchant": "Netflix",
                "description": "Monthly Subscription",
                "transaction_date": "2024-01-15T10:00:00Z",
                "status": "Posted",
                "cardholder_name": "John Doe",
                "card_type": "Visa"
            },
            {
                "customer_id": "CUST001",
                "composite_key": "CARD#1234#TXN002",
                "card_number": "1234",
                "transaction_id": "TXN002",
                "amount": "150.00",
                "currency": "USD",
                "merchant": "Amazon",
                "description": "Electronics",
                "transaction_date": "2024-01-20T14:30:00Z",
                "status": "Posted",
                "cardholder_name": "John Doe",
                "card_type": "Visa"
            }
        ]

        for item in items:
            try:
                table.put_item(Item=item)
                log(f" -> Added item: {item.get('composite_key')}")
            except Exception as e:
                log(f" -> Error adding item: {e}")

        log("\nDatabase Initialization Complete!")

    except Exception:
        log("CRITICAL ERROR")
        log(traceback.format_exc())
    
    finally:
        with open("db_init_log.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    init_db()
