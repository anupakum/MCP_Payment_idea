# Terraform Deployment - Dispute Resolution System

Simple EC2-based deployment for the dispute resolution system with CrewAI agents.

## 📋 Prerequisites

1. **AWS Account** with:
   - Access to AWS Bedrock (Claude Haiku 4.5 model: `anthropic.claude-haiku-4-5-20251001-v1:0`)
   - DynamoDB tables already created:
     - `ptr_dispute_resol_customer_cards_and_transactions`
     - `ptr_dispute_resol_case_db` (with `TransactionIndex` GSI)
   - Permissions for EC2, IAM, SSM, S3, DynamoDB, and Bedrock

2. **AWS CLI** installed and configured:
   ```powershell
   # Install AWS CLI v2
   # Download from https://aws.amazon.com/cli/

   # Configure with your credentials
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
   ```

3. **Terraform** installed (v1.0+):
   ```powershell
   # Download from https://www.terraform.io/downloads
   terraform --version
   ```

4. **GitHub Repository Access** (for CI/CD deployment):
   - Repository: `Capgemini-Innersource/ptr_ag_bnk_pmts_dispute_resol`
   - GitHub Secrets configured (see [../.github/SECRETS.md](../.github/SECRETS.md))

**Note**: EC2 SSH key pair is optional. The GitHub Actions workflow uses AWS Systems Manager (SSM) for deployment, not SSH.

## 🚀 Quick Start

### Step 1: Configure Variables

```powershell
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:
- `key_name` - Your EC2 key pair name (optional, only for direct SSH access)
- `allowed_ssh_cidr` - Your IP address for SSH (get it: `curl ifconfig.me` or use `0.0.0.0/0` for SSM-only access)
- `aws_region` - AWS region (default: `us-east-1`)
- `project_name` - Project identifier (default: `dispute-resolution`)
- `environment` - Environment name (e.g., `dev`, `staging`, `prod`)

### Step 2: Initialize Terraform

```powershell
terraform init
```

This downloads the AWS provider plugin.

### Step 3: Preview Changes

```powershell
terraform plan
```

Review what will be created:
- 1 EC2 instance (t3.medium, Amazon Linux 2023)
- 1 Security group (ports 22, 8000, 8001, 3000)
- 1 Elastic IP (static public IP)
- 1 IAM role with policies:
  - DynamoDB read/write access
  - AWS Bedrock invoke model access
  - CloudWatch Logs access
  - SSM Session Manager access (for remote management)

### Step 4: Deploy Infrastructure

```powershell
terraform apply
```

Type `yes` when prompted. Deployment takes ~2-3 minutes.

### Step 5: Get Connection Info

```powershell
terraform output
```

Copy the SSH command and public IP.

## 📦 What Gets Created

| Resource | Description | Cost (monthly) |
|----------|-------------|----------------|
| EC2 t3.medium | 2 vCPU, 4 GB RAM | ~$30 |
| EBS gp3 30GB | Root volume | ~$2.50 |
| Elastic IP | Static IP | ~$0 (while attached) |
| Security Group | Firewall rules | Free |
| IAM Role | AWS service access | Free |
| **Total** | | **~$32.50** |

## 🔐 Security Features

✅ **IAM Role with Least Privilege** - EC2 has only necessary permissions (DynamoDB, Bedrock, CloudWatch, SSM)
✅ **Encrypted EBS Volume** - Data at rest encryption (AES-256)
✅ **IMDSv2 Enforced** - Enhanced metadata security (prevents SSRF attacks)
✅ **SSM Session Manager** - Secure remote access without SSH keys
✅ **Security Groups** - Restrictive firewall rules (ports 22, 8000, 8001, 3000 only)
✅ **No Hardcoded Credentials** - IAM role provides temporary credentials automatically
✅ **VPC Default** - Network isolation in default VPC
✅ **CloudWatch Integration** - Centralized logging and monitoring

## 📝 Post-Deployment Steps

### Option A: Use GitHub Actions (Recommended)

After Terraform deployment, the easiest way to deploy your application is via GitHub Actions:

1. **Get EC2 Public IP**:
   ```powershell
   terraform output ec2_public_ip
   ```

2. **Configure GitHub Secrets** (see [../.github/SECRETS.md](../.github/SECRETS.md)):
   - Set `EC2_HOST` to the public IP from step 1
   - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (production)
   - Set `DEV_AWS_ACCESS_KEY_ID` and `DEV_AWS_SECRET_ACCESS_KEY` (development)
   - Set `AWS_REGION`, `APP_DIR`

3. **Push Code to GitHub**:
   ```bash
   # For production deployment
   git push origin main

   # For development deployment
   git push origin crew-ai-v3-new
   ```

   GitHub Actions will automatically:
   - Deploy code via SSM (no SSH needed)
   - Install dependencies
   - Build Next.js
   - Start PM2 services
   - Run health checks

### Option B: Manual SSH Setup

If you prefer manual deployment or need SSH access for debugging:

**Connect via SSH** (requires key pair):
```powershell
ssh -i ~/.ssh/your-key.pem ec2-user@<PUBLIC_IP>
```

**Or use AWS Systems Manager** (no key needed, more secure):
```powershell
# Get instance ID
terraform output instance_id

# Start SSM session
aws ssm start-session --target <INSTANCE_ID>
```

### 2. Clone Repository

```bash
git clone https://github.com/Capgemini-Innersource/ptr_ag_bnk_pmts_dispute_resol.git
cd ptr_ag_bnk_pmts_dispute_resol
```

### 3. Install Dependencies

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js
cd web
npm install
cd ..
```

### 4. Configure Environment

**For GitHub Actions Deployment** (Recommended):
- Environment files are automatically created from GitHub Secrets
- No manual configuration needed!

**For Manual Deployment**:

Create backend `.env`:
```bash
cat > .env << 'EOF'
# MCP Mode Configuration
USE_MCP_HTTP=true
MCP_URL=http://localhost:8001
MCP_PORT=8001
MCP_HOST=0.0.0.0

# AWS Configuration
AWS_REGION=us-east-1
# Note: On EC2, IAM role provides credentials automatically!
# Only set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY for local development

# FastAPI Configuration
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production
CORS_ORIGINS=http://localhost:3000

# Logging
LOG_LEVEL=INFO

# CrewAI with AWS Bedrock
AWS_BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0
AWS_BEDROCK_REGION=us-east-1
CREW_MAX_ITERATIONS=3
EOF
```

Create frontend `.env.local`:
```bash
cat > web/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://<EC2_PUBLIC_IP>:8000
NEXT_PUBLIC_ENV=production
EOF
```

**Replace `<EC2_PUBLIC_IP>` with your actual EC2 public IP!**

**Important**:
- ✅ On EC2: IAM role provides AWS credentials automatically (no keys needed)
- ✅ `NEXT_PUBLIC_API_URL` must use EC2 public IP (browser needs to access backend)
- ✅ `MCP_URL` can use localhost (server-to-server on same EC2)

### 5. Start Services

```bash
# Install PM2
sudo npm install -g pm2

# Start backend services
pm2 start "python -m mcp.http_server" --name mcp-server
pm2 start "python -m mcp.main" --name backend

# Start frontend
pm2 start "npm run start" --name frontend --cwd web

# Save configuration
pm2 save
pm2 startup  # Follow the command it outputs

# Check status
pm2 status
```

### 6. Verify Deployment

**From your local machine**:
```powershell
# Get EC2 public IP
$EC2_IP = terraform output -raw ec2_public_ip

# Test backend main API
curl http://${EC2_IP}:8000/health

# Test MCP server
curl http://${EC2_IP}:8001/health

# Test frontend
curl http://${EC2_IP}:3000

# Access application in browser
Start-Process "http://${EC2_IP}:3000"
```

**Expected responses**:
- ✅ Port 8000: `{"status":"healthy"}` (Backend API)
- ✅ Port 8001: `{"status":"healthy"}` (MCP Server)
- ✅ Port 3000: HTML page (Next.js Frontend)

## 🔧 Common Operations

### Automated Deployment (GitHub Actions)

**Deploy Updates**:
```bash
# Production deployment
git checkout main
git add .
git commit -m "Update application"
git push origin main

# Development deployment
git checkout crew-ai-v3-new
git add .
git commit -m "Update application"
git push origin crew-ai-v3-new
```

GitHub Actions automatically:
- Deploys via AWS Systems Manager (SSM)
- Installs dependencies
- Restarts services
- Runs health checks

**Monitor Deployment**:
- Go to GitHub → **Actions** tab
- View workflow run logs

### Manual Operations (SSH/SSM Access)

**View Logs**:
```bash
pm2 logs backend      # Backend logs
pm2 logs mcp-server   # MCP server logs
pm2 logs frontend     # Frontend logs
pm2 logs --lines 100  # Last 100 lines from all
pm2 monit            # Real-time monitoring
```

**Restart Services**:
```bash
pm2 restart backend
pm2 restart mcp-server
pm2 restart frontend
pm2 restart all
```

**Manual Update** (if not using GitHub Actions):
```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
pm2 restart all
```

**Stop Services**:
```bash
pm2 stop all
pm2 delete all
```

### Remote Commands via SSM (No SSH Needed)

**Run commands without SSH**:
```powershell
# Get instance ID
$INSTANCE_ID = terraform output -raw instance_id

# Send command via SSM
aws ssm send-command `
  --instance-ids $INSTANCE_ID `
  --document-name "AWS-RunShellScript" `
  --parameters "commands=['pm2 status']"
```

## 🗑️ Destroy Infrastructure

**WARNING**: This deletes everything!

```powershell
terraform destroy
```

Type `yes` to confirm.

## 📊 Monitoring

### Check EC2 Status
```powershell
aws ec2 describe-instances --instance-ids <INSTANCE_ID>
```

### CloudWatch Logs
```powershell
aws logs tail /aws/ec2/dispute-resolution --follow
```

### PM2 Monitoring
```bash
pm2 monit  # Real-time dashboard
```

## 🔄 Scaling Options (Future)

When ready to scale:
1. Add Application Load Balancer (`alb.tf`)
2. Create Auto Scaling Group (`asg.tf`)
3. Add SSL certificate (`acm.tf`)
4. Setup Route53 domain (`route53.tf`)

## 🐛 Troubleshooting

### GitHub Actions Deployment Fails

**Check Secrets Configuration**:
```powershell
# Verify secrets are set in GitHub
# Settings → Secrets and variables → Actions
```

Required secrets:
- `AWS_ACCESS_KEY_ID` (production) or `DEV_AWS_ACCESS_KEY_ID` (development)
- `AWS_SECRET_ACCESS_KEY` (production) or `DEV_AWS_SECRET_ACCESS_KEY` (development)
- `AWS_REGION`
- `EC2_HOST` (from `terraform output ec2_public_ip`)
- `APP_DIR`

**Check SSM Agent**:
```bash
# Connect via SSH first
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2_IP>

# Verify SSM agent is running
sudo systemctl status amazon-ssm-agent

# If not running:
sudo systemctl start amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
```

**Test SSM Connectivity**:
```powershell
aws ssm describe-instance-information --region us-east-1
```

### Can't Connect via SSH?

- Check `allowed_ssh_cidr` matches your current IP
- Verify security group allows port 22 from your IP
- Verify key pair exists: `aws ec2 describe-key-pairs`
- **Alternative**: Use SSM Session Manager (no SSH key needed):
  ```powershell
  aws ssm start-session --target <INSTANCE_ID>
  ```

### Services Won't Start?

**Check PM2 status**:
```bash
pm2 status
pm2 logs --lines 50
```

**Verify environment**:
```bash
# Check .env file exists
cat .env

# Verify IAM role credentials work
aws sts get-caller-identity
```

**Check user data script**:
```bash
# View cloud-init logs
sudo cat /var/log/cloud-init-output.log

# Check setup completion
cat /home/ec2-user/setup-complete.txt
```

### DynamoDB Access Denied?

**Verify tables exist**:
```bash
aws dynamodb list-tables --region us-east-1
```

**Check IAM role permissions**:
```bash
# Should show EC2 instance role
aws sts get-caller-identity

# Test DynamoDB access
aws dynamodb describe-table \
  --table-name ptr_dispute_resol_customer_cards_and_transactions \
  --region us-east-1
```

**Verify IAM policy**:
- Check `iam.tf` for correct table ARNs
- Ensure region matches (us-east-1)
- Verify `TransactionIndex` GSI exists on case_db table

### Bedrock Not Working?

**Check model access**:
1. AWS Console → Bedrock → Model access
2. Request access to `Claude 4.5 Haiku`
3. Wait for approval (~5 minutes)

**Test Bedrock**:
```bash
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --region us-east-1 \
  output.json
```

**Check IAM policy**:
- Verify `iam.tf` includes Bedrock invoke permissions
- Ensure model ARN is correct

### Health Checks Fail

**Test each service**:
```powershell
$EC2_IP = "<your-ec2-ip>"

# Backend
curl http://${EC2_IP}:8000/health

# MCP Server
curl http://${EC2_IP}:8001/health

# Frontend
curl http://${EC2_IP}:3000
```

**Check security group**:
```powershell
terraform output security_group_id

# Verify ports 8000, 8001, 3000 are open
aws ec2 describe-security-groups --group-ids <SG_ID>
```

**Check services are running**:
```bash
pm2 status
sudo netstat -tlnp | grep -E '8000|8001|3000'
```

## � CI/CD Integration

This Terraform deployment is designed to work seamlessly with GitHub Actions:

### Deployment Flow

```
1. Developer pushes code to GitHub
    ↓
2. GitHub Actions detects branch
    ├── main/master → Production credentials
    └── other → Development credentials
    ↓
3. GitHub Actions deploys via SSM
    ├── Packages application
    ├── Uploads to S3
    ├── Deploys to EC2 via SSM
    └── Restarts PM2 services
    ↓
4. Health checks verify deployment
    ✓ Backend (8000)
    ✓ MCP Server (8001)
    ✓ Frontend (3000)
```

### Complete Setup Workflow

1. **Deploy Infrastructure** (This Terraform):
   ```powershell
   cd terraform
   terraform apply
   ```

2. **Configure GitHub Secrets** (see [../.github/SECRETS.md](../.github/SECRETS.md)):
   - Get EC2 IP: `terraform output ec2_public_ip`
   - Set all 7 required secrets

3. **Push Code to Deploy**:
   ```bash
   git push origin main  # Production
   # or
   git push origin crew-ai-v3-new  # Development
   ```

4. **Monitor Deployment**:
   - GitHub → Actions tab
   - View workflow logs

## �📚 Additional Resources

### Documentation
- [GitHub Actions Workflow](../.github/workflows/README.md) - CI/CD pipeline documentation
- [GitHub Secrets Setup](../.github/SECRETS.md) - Required secrets configuration
- [Branch-Based Deployment](../.github/BRANCH_BASED_DEPLOYMENT.md) - Deployment strategy
- [Project README](../README.md) - Application architecture overview
- [Implementation Summary](../docs/IMPLEMENTATION_SUMMARY.md) - Feature documentation

### AWS Documentation
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [AWS Systems Manager](https://docs.aws.amazon.com/systems-manager/)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [DynamoDB](https://docs.aws.amazon.com/dynamodb/)

### Tools Documentation
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)

## 🤝 Support

### Quick Diagnostics

```powershell
# 1. Verify infrastructure
terraform show

# 2. Get instance details
terraform output

# 3. Check EC2 status
aws ec2 describe-instances --instance-ids $(terraform output -raw instance_id)

# 4. Test connectivity
$EC2_IP = terraform output -raw ec2_public_ip
curl http://${EC2_IP}:8000/health
```

### Common Issues

| Issue | Quick Fix | Documentation |
|-------|-----------|---------------|
| Deployment fails | Check GitHub Secrets | [SECRETS.md](../.github/SECRETS.md) |
| SSM not working | Verify agent running | [Troubleshooting](#troubleshooting) |
| Services down | Check PM2 status | [Common Operations](#common-operations) |
| Can't access app | Verify security group | [Security Features](#security-features) |

---

## 💡 Cost Optimization Tips

### Development/Testing
- **Stop EC2 when not in use**: Only pay for EBS storage (~$2.50/month)
  ```powershell
  aws ec2 stop-instances --instance-ids <INSTANCE_ID>
  ```
- **Use t3.small for lighter workloads**: ~$15/month (instead of t3.medium ~$30/month)
- **Use Spot Instances**: Save up to 75% (for non-critical environments)

### Production
- **Reserved Instances**: Save up to 72% with 1-3 year commitment
- **Compute Savings Plans**: Flexible pricing for consistent usage
- **Monitor unused resources**: Review CloudWatch metrics monthly

### Current Monthly Estimate
- EC2 t3.medium: **~$30**
- EBS gp3 30GB: **~$2.50**
- Elastic IP (attached): **$0**
- Data Transfer: **~$1-5** (depending on usage)
- **Total**: **~$33-38/month**

---

**Need help?** See [troubleshooting](#troubleshooting) or check [GitHub documentation](../.github/README.md) for CI/CD setup! 🚀
