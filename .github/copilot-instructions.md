# AI Coding Agent Instructions - Dispute Resolution System

## System Overview

Multi-agent dispute resolution system using **CrewAI Hierarchical Process** with AWS Bedrock (Claude 4.5 Haiku), FastAPI backend, and Next.js frontend.

**Stack**: Python 3.x + FastAPI + CrewAI + AWS Bedrock/DynamoDB + Next.js 14 + TypeScript + ShadCN UI

## Quick Start Commands (PowerShell)

```powershell
# Backend (port 8000 - main app)
python -m mcp.main

# Frontend (port 3000)
cd web; npm run dev

# Tests
pytest                          # All tests
pytest test_customer_cases.py   # Specific file

# Batch startup (starts all services)
.\startup.bat
```

**Environment Variables Required**:

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (or AWS credential chain)
- `AWS_REGION` (default: `us-east-1`)
- `AWS_BEDROCK_MODEL_ID` (default: `anthropic.claude-haiku-4-5-20251001-v1:0`)
- `USE_MCP_HTTP` (optional: `true` for separate MCP server on port 8001, default: `false` for in-process)

**For EC2 Deployment (startup.sh)**:

- `GITHUB_PAT` - Personal Access Token for cloning repository
- `GITHUB_BRANCH` - Branch name to deploy (passed from GitHub Actions)

## Architecture Patterns

### Agent Orchestration (Hierarchical Process)

**CrewAI Setup** (`crew_ai_app/crew.py`):

```python
Crew(
    agents=[verification_agent, dispute_decision_agent, case_query_agent],
    process=Process.hierarchical,  # Auto-creates manager for delegation
    manager_llm=bedrock_llm,
    memory=True
)
```

**Agent Delegation Flow**:

1. User request → FastAPI `/process` endpoint
2. Manager Agent analyzes intent (routing logic in `crew.py:process_request()`)
3. Delegates to specialized agent:
   - `VerificationAgent`: Customer/card/transaction validation
   - `DisputeDecisionAgent`: Business rule application + case creation
   - `CaseQueryAgent`: Case status/history queries
4. Returns structured dict (not string) with `{"success": bool, "data": {...}, "message": str}`

**Tool Pattern** (2 modes via `USE_MCP_HTTP`):

- **Direct Python** (default): `DynamoQueryCreatorTool(db_client)` - in-process calls
- **HTTP-based**: `MCPHttpClientTool(mcp_url)` - REST calls to separate MCP server on port 8001

Example in `DisputeDecisionAgent.__init__()`:

```python
if self.use_mcp_http:
    self.dynamo_tool = MCPHttpClientTool(mcp_url)
else:
    self.dynamo_tool = DynamoQueryCreatorTool(db_client)
```

### Business Rules (Hardcoded Constants)

**Location**: `crew_ai_app/agents/dispute_decision_agent.py`

```python
TIME_BARRED_DAYS = 600              # > 600 days → REJECTED_TIME_BARRED
AUTO_RESOLVE_AMOUNT_USD = 100.0     # ≤ $100 → RESOLVED_CUSTOMER + PERMANENT credit
                                     # > $100 → FORWARDED_TO_ACQUIRER + TEMPORARY credit
```

**Decision Logic** (`_determine_case_status()`):

1. Check age: `age_days > 600` → reject (no credit)
2. Check amount: `amount ≤ $100` → auto-resolve with permanent credit
3. Else: forward to acquirer with temporary credit

**Do not modify** these constants without business approval (no documentation file exists yet - rules are code-driven).

### DynamoDB Critical Patterns

**Tables**:

1. `ptr_dispute_resol_customer_cards_and_transactions` (PK: `customer_id`) - nested `cards[]` → `transactions[]`
2. `ptr_dispute_resol_case_db` (PK: `case_id`) - **REQUIRES** `TransactionIndex` GSI on `transaction_id`

**Float → Decimal Conversion** (`db/dynamo_client.py`):

```python
from crew_ai_app.db.dynamo_client import convert_floats_to_decimal
case_data = convert_floats_to_decimal(case_data)  # ALWAYS before put_item/update_item
```

**Why**: DynamoDB rejects Python `float` - must use `Decimal` for numbers. Failure = `ValidationException`.

**Async Retry Decorator**:

```python
@async_retry(max_attempts=3, delay=0.5)
async def create_case(self, case_data: Dict) -> bool:
    # Handles ProvisionedThroughputExceededException with exponential backoff
```

**Duplicate Prevention**:

```python
# Before creating case, check TransactionIndex GSI
existing = await db_client.get_open_case_for_transaction(transaction_id)
if existing:
    return {"success": False, "message": "Case already exists"}
```

**GSI Requirement**: If `TransactionIndex` missing, case queries fail silently. No terraform/docs exist yet - must create manually via AWS CLI/Console.

## LLM Configuration

**LiteLLM Integration** (`crew_ai_app/llm_config.py`):

- CrewAI uses **LiteLLM** (not LangChain) for AWS Bedrock
- Model format: `bedrock/<model_id>` (e.g., `bedrock/anthropic.claude-haiku-4-5-20251001-v1:0`)
- Shared config: `temperature=0.1` (deterministic), `max_tokens=4096`

**Agent LLM Setup**:

```python
llm_config = get_bedrock_llm_config()
agent = Agent(
    role="...",
    llm=llm_config['model'],           # "bedrock/..."
    llm_config=llm_config['llm_config']  # {temperature, max_tokens, aws_region_name}
)
```

## API Endpoints (FastAPI)

**Unified Endpoint** (`POST /process`) - **Recommended**:

```json
{
  "request": "Verify customer CUST001",
  "customer_id": "CUST001",
  "transaction_id": "TX123", // Optional context fields
  "case_id": "..."
}
```

**Legacy Direct Endpoints** (still supported):

- `POST /verify/customer` → `VerificationAgent`
- `POST /verify/txn` → `VerificationAgent` + `DisputeDecisionAgent`
- `POST /case/status` → `CaseQueryAgent`
- `POST /case/customer` → `CaseQueryAgent`

**Response Pattern**:

```json
{
  "success": true,
  "data": {...},
  "message": "Operation completed",
  "error": null  // Only present on failure
}
```

## Frontend Architecture

**Entry Point**: `app/page.tsx` → `components/ChatWindow.tsx` (main state machine)

**User Input Parsing** (`ChatWindow.tsx:handleSubmit()`):

```typescript
// Patterns:
"case status <case_id>"      → apiClient.getCaseStatus(case_id)
"my cases <customer_id>"     → apiClient.getCustomerCases(customer_id)
"<customer_id>"              → apiClient.verifyCustomer(customer_id) // Start flow
```

**API Client** (`lib/api-client.ts`): Typed wrapper around `fetch()`, base URL `http://localhost:8000`

**Data Masking** (`lib/mask-utils.ts`) - **REQUIRED** for all UI displays:

```typescript
maskCustomerId('CUST001')           → 'CU***01'
maskCardNumber('4111111111111111')  → '41***11'
maskTransactionId('TX123')          → 'TX***23'
maskAmount(150.00)                  → '$***00'
```

See `ChatWindow.tsx` lines 400-600 for implementation examples.

**ShadCN UI**: Import from `@/components/ui/*`, uses Tailwind + dark mode (`next-themes`)

## Code Conventions

**Python**:

- Type hints on public methods: `async def get_case(case_id: str) -> Optional[Dict[str, Any]]`
- Module-level logging: `logger = logging.getLogger(__name__)`
- Error returns: `{"success": False, "message": str, "error": str}`
- Async everything for DynamoDB (no sync wrappers)

**TypeScript/React**:

- `"use client"` directive on interactive components
- React Context for cross-component state (`lib/log-context.tsx` for agent logs)
- Tailwind utility classes (no CSS modules)

## Deployment to EC2

**Automated Deployment via GitHub Actions**:

1. **Setup (one-time)**:

   - Deploy Terraform infrastructure: `cd terraform; .\deploy.ps1 -Action apply`
   - Configure 8 GitHub Secrets (see `.github/SECRETS.md`):
     - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (production)
     - `DEV_AWS_ACCESS_KEY_ID`, `DEV_AWS_SECRET_ACCESS_KEY` (development)
     - `AWS_REGION`, `EC2_HOST`, `APP_DIR`
     - **`GITHUB_PAT`** (new) - Personal Access Token with `repo` scope
   - **S3 Bucket Architecture** (see `terraform/BUCKET_ARCHITECTURE.md`):
     - **Dev Environment**:
       - Application code: `dev-ptr-ag-bnk-pmts-dispute-resol`
       - Terraform state: `dev-ptr-ag-bnk-pmts-dispute-resol-terraform-locks`
       - DynamoDB lock: `terraform-lock-dev`
     - **Prod Environment**:
       - Application code: `ptr-ag-bnk-pmts-dispute-resol`
       - Terraform state: `ptr-ag-bnk-pmts-dispute-resol-terraform-locks`
       - DynamoDB lock: `terraform-lock-prod`

2. **Deploy**:

   ```bash
   git push origin main              # Production (uses AWS_ACCESS_KEY_ID)
   git push origin crew-ai-v3-new    # Development (uses DEV_AWS_ACCESS_KEY_ID)
   ```

3. **What Happens**:

   - GitHub Actions detects branch and selects AWS credentials
   - **Code Sync**: Syncs application files to S3 application bucket
   - **Terraform Init**: Uses separate terraform-locks bucket for state storage
   - Sends SSM command to EC2 with `GITHUB_PAT` and `GITHUB_BRANCH`
   - EC2 runs `startup.sh` which:
     - Clones repo if first-time deployment
     - Pulls latest changes if repo exists
     - Installs dependencies and starts services with PM2

4. **Verify**:

   ```bash
   # Check GitHub Actions logs
   # Health checks run automatically (ports 8000, 8001, 3000)

   # SSH to EC2 (optional)
   ssh -i your-key.pem ec2-user@<EC2_IP>
   pm2 status
   pm2 logs
   ```

**See**: `DEPLOYMENT_CHANGES.md` for detailed deployment architecture

## Common Pitfalls

1. **DynamoDB Floats**: Forgetting `convert_floats_to_decimal()` → `ValidationException: Type mismatch for key`
2. **Missing GSI**: Case lookup returns empty without `TransactionIndex` (no error message)
3. **MCP Mode Confusion**: Setting `USE_MCP_HTTP=true` but not starting `python -m mcp.http_server` → tools fail
4. **Port Conflicts**: Services on 8000 (main), 8001 (MCP HTTP), 3000 (Next.js) - check with `netstat -ano | findstr "8000"`
5. **Bedrock Credentials**: Agents hang indefinitely if AWS credentials invalid (no timeout configured)
6. **Missing GITHUB_PAT**: Deployment fails with "ERROR: GITHUB_PAT not set" → Add to GitHub Secrets

## Testing & Debugging

**Backend Logs**: Watch FastAPI startup for:

```
CrewAI instance initialized with DIRECT PYTHON MCP tools  // In-process mode
CrewAI instance initialized with HTTP-BASED MCP server at http://localhost:8001  // HTTP mode
```

**Frontend Debugging**:

- DevTools Network tab: Check requests to `localhost:8000/*`
- `LiveLogs` component (in `app/page.tsx`): Real-time agent activity
- `DetailedLogs` component: Full execution trace with timestamps

**Test Files**:

- `test_customer_cases.py` - Case creation/query tests
- `test_case_query_fix.py` - GSI query validation

## Key Files

**Backend**:

- `crew_ai_app/crew.py` - Crew setup + intelligent routing logic
- `crew_ai_app/agents/dispute_decision_agent.py` - Business rules (TIME_BARRED_DAYS, AUTO_RESOLVE_AMOUNT)
- `crew_ai_app/db/dynamo_client.py` - DynamoDB wrapper (convert_floats_to_decimal, @async_retry)
- `mcp/main.py` - FastAPI app + `/process` endpoint

**Frontend**:

- `web/components/ChatWindow.tsx` - UI state machine + command parsing
- `web/lib/api-client.ts` - Typed API wrapper
- `web/lib/mask-utils.ts` - Data masking utilities

## Modification Checklist

**Changing Business Rules**:

1. Edit constants in `DisputeDecisionAgent` (TIME_BARRED_DAYS, AUTO_RESOLVE_AMOUNT)
2. Update `_determine_case_status()` logic if needed
3. Add tests in `test_customer_cases.py`
4. Document in README or create `docs/CREDIT_POLICY.md`

**Adding New Agent**:

1. Create in `crew_ai_app/agents/` (inherit `Agent`)
2. Implement `get_agent()` method
3. Add tools (direct or HTTP mode support)
4. Register in `crew.py` agents list
5. Update routing logic in `crew.py:process_request()`

**New API Endpoint**:

1. Add route to `mcp/main.py` with Pydantic request model
2. Update `web/lib/api-client.ts` with typed method
3. Call from `ChatWindow.tsx` or other component

**DynamoDB Schema Changes**:

1. Update `dynamo_client.py` methods
2. Document GSI requirements (no automation exists yet)
3. Update tool descriptions in `dynamo_query_tool.py` if adding tables/indexes
