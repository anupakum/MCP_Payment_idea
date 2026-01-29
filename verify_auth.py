
import boto3
import os
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def check_structure(key_name, value):
    if not value:
        print(f"[ERROR] {key_name} is EMPTY")
        return
    
    print(f"Checking {key_name}...")
    print(f"  Length: {len(value)}")
    print(f"  First char: '{value[0]}'")
    print(f"  Last char: '{value[-1]}'")
    
    if value.strip() != value:
        print(f"  [WARNING] Detected surrounding whitespace! Original: '{value}'")
    else:
        print(f"  [OK] No surrounding whitespace detected.")

def verify():
    # Load env manually
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    # Intentionally NOT stripping 'v' heavily to detect the issue
                    # But we remove the newline
                    v = v.rstrip('\n').rstrip('\r')
                    os.environ[k] = v

    region = os.environ.get("AWS_REGION", "us-east-1")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    print(f"Region: {region}")
    check_structure("AWS_ACCESS_KEY_ID", access_key)
    check_structure("AWS_SECRET_ACCESS_KEY", secret_key)
    
    print("\nAttempting STS GetCallerIdentity...")
    try:
        sts = boto3.client("sts", region_name=region)
        id_info = sts.get_caller_identity()
        print("[SUCCESS] Credentials are valid!")
        print(f"User: {id_info.get('Arn')}")
    except Exception as e:
        print(f"[FAILURE] Auth check failed: {e}")

if __name__ == "__main__":
    verify()
