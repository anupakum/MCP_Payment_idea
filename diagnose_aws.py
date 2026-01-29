
import boto3
import os
import json
import traceback

def run_diagnostic():
    output = []
    
    def log(msg):
        output.append(str(msg))

    try:
        # Load env
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value

        AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
        BEDROCK_REGION = os.environ.get("AWS_BEDROCK_REGION", "us-east-1")
        AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")

        log(f"--- AWS Diagnostic ---")
        log(f"Region: {AWS_REGION}")
        log(f"Bedrock Region: {BEDROCK_REGION}")
        log(f"Access Key Present: {'Yes' if AWS_ACCESS_KEY else 'No'}")

        if not AWS_ACCESS_KEY:
            log("ERROR: Missing AWS Credentials")
            return

        # 1. Test DynamoDB
        log("\n[1] Testing DynamoDB ...")
        try:
            dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)
            response = dynamodb.list_tables()
            tables = response.get("TableNames", [])
            log(f"[OK] Connection Successful")
            log(f"Found {len(tables)} tables: {tables}")
            
            required = ["ptr_dispute_resol_customers", "ptr_dispute_resol_customer_cards_and_transactions", "ptr_dispute_resol_cases"]
            missing = [t for t in required if t not in tables]
            if missing:
                log(f"[ERROR] MISSING TABLES: {missing}")
            else:
                log("[OK] All tables present")
        except Exception as e:
            log(f"[ERROR] DynamoDB Failed: {str(e)}")

        # 2. Test Bedrock
        log("\n[2] Testing Bedrock (Claude)...")
        model_id = os.environ.get("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        log(f"Model: {model_id}")
        
        try:
            bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
            body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 10, "messages": [{"role": "user", "content": "Hi"}]})
            resp = bedrock.invoke_model(modelId=model_id, body=body)
            log("[OK] Bedrock Invocation Successful")
        except Exception as e:
            log(f"[ERROR] Bedrock Failed: {str(e)}")

    except Exception:
        log("CRITICAL SCRIPT ERROR")
        log(traceback.format_exc())
    
    finally:
        with open("diagnostic_output.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))

if __name__ == "__main__":
    run_diagnostic()
