# GitHub Actions Secrets Required

Configure these secrets in your GitHub repository settings:
**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

## 🔐 Required Secrets

### 1. AWS Credentials (Environment-Specific)

**For PRODUCTION (main/master branch):**

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | Production AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | Production AWS Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

**For DEVELOPMENT (all other branches):**

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `DEV_AWS_ACCESS_KEY_ID` | Development AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| `DEV_AWS_SECRET_ACCESS_KEY` | Development AWS Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

**Shared AWS Configuration:**

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_REGION` | AWS region | `us-east-1` |

### 2. EC2 Configuration

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `EC2_HOST` | EC2 public IP or hostname | `54.123.45.67` |
| `APP_DIR` | Application directory on EC2 | `/home/ec2-user/ptr_ag_bnk_pmts_dispute_resol` |

### 3. GitHub Repository Access

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `GITHUB_PAT` | GitHub Personal Access Token with `repo` scope | `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |

**How to create a GitHub PAT:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: `EC2 Deployment - ptr_ag_bnk_pmts_dispute_resol`
4. Select scopes: **✓ repo** (Full control of private repositories)
5. Click "Generate token"
6. Copy the token (you won't be able to see it again!)
7. Add to GitHub Secrets as `GITHUB_PAT`

**Why this is needed:**
The startup script on EC2 clones the repository using this PAT to:
- Clone the repo on first deployment
- Pull latest changes on subsequent deployments
- Use the exact branch that triggered the workflow

---

## 🌿 Branch-Based Deployment Strategy

The workflow automatically selects credentials based on the branch:

- **`main` or `master` branch** → Uses `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (Production)
- **Any other branch** (e.g., `develop`, `feature/*`, `crew-ai-v3-new`) → Uses `DEV_AWS_ACCESS_KEY_ID` + `DEV_AWS_SECRET_ACCESS_KEY` (Development)

This allows you to:
- ✅ Deploy to production AWS account from `main` branch
- ✅ Deploy to development/staging AWS account from feature branches
- ✅ Maintain separate AWS environments with different credentials
- ✅ Prevent accidental production deployments from development branches

---

## 📝 How to Set Secrets

### Step 1: Get Your AWS Credentials

**Option A: Create Separate IAM Users for Production and Development (Recommended)**

**For Production:**
1. Go to AWS Console → IAM → Users → Create User
2. User name: `github-actions-deploy-prod`
3. Attach policies:
   - `AmazonEC2FullAccess` (for SSM access)
   - `AmazonSSMFullAccess` (for Systems Manager)
   - `AmazonS3FullAccess` (for deployment package upload)
   - `AmazonDynamoDBFullAccess` (for your tables)
   - Custom policy for Bedrock:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
4. Create access key → Save as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

**For Development:**
1. Repeat above steps with user name: `github-actions-deploy-dev`
2. Can use same or different AWS account (recommended: separate AWS account for dev)
3. Create access key → Save as `DEV_AWS_ACCESS_KEY_ID` and `DEV_AWS_SECRET_ACCESS_KEY`

**Option B: Use Existing AWS Credentials**

If you have AWS CLI configured:
```powershell
# View your credentials (Windows)
type %USERPROFILE%\.aws\credentials

# Or on Linux/Mac
cat ~/.aws/credentials
```

### Step 2: Add to GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:

#### Production AWS Credentials (for main/master branch)

**AWS_ACCESS_KEY_ID**

```text
Name: AWS_ACCESS_KEY_ID
Value: AKIAIOSFODNN7EXAMPLE
(Your actual production AWS access key)
```

**AWS_SECRET_ACCESS_KEY**

```text
Name: AWS_SECRET_ACCESS_KEY
Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
(Your actual production AWS secret key)
```

#### Development AWS Credentials (for all other branches)

**DEV_AWS_ACCESS_KEY_ID**

```text
Name: DEV_AWS_ACCESS_KEY_ID
Value: AKIAIOSFODNN7DEVEXAMPLE
(Your actual development AWS access key)
```

**DEV_AWS_SECRET_ACCESS_KEY**

```text
Name: DEV_AWS_SECRET_ACCESS_KEY
Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYDEVEXAMPLEKEY
(Your actual development AWS secret key)
```

#### Shared Configuration

**AWS_REGION**

```text
Name: AWS_REGION
Value: us-east-1
```

**EC2_HOST**

```text
Name: EC2_HOST
Value: dispresoldev.orchestrateai.tech
(Get from: terraform output ec2_public_ip)
```

**APP_DIR**

```text
Name: APP_DIR
Value: /home/ec2-user/ptr_ag_bnk_pmts_dispute_resol
```

---

**GITHUB_PAT**

```text
Name: GITHUB_PAT
Value: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
(Create from: GitHub → Settings → Developer settings → Personal access tokens)
```

---

## 📊 Total Secrets Required

**Minimum (8 secrets):**
- Production: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Development: `DEV_AWS_ACCESS_KEY_ID`, `DEV_AWS_SECRET_ACCESS_KEY`
- Shared: `AWS_REGION`, `EC2_HOST`, `APP_DIR`, `GITHUB_PAT`

---

## 🚀 Workflow Triggers

### Automatic Deploy

**Production Deployment (main/master branch):**
```bash
git push origin main
# Uses: AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY
```

**Development Deployment (any other branch):**
```bash
git push origin crew-ai-v3-new
# Uses: DEV_AWS_ACCESS_KEY_ID + DEV_AWS_SECRET_ACCESS_KEY
```

### Manual Deploy
1. Go to **Actions** tab in GitHub
2. Select **Deploy to AWS EC2** workflow
3. Click **Run workflow**
4. Choose branch
5. Click **Run workflow** button

---

## 🔍 What the Workflow Does

### Phase 1: Preparation
1. ✅ Checks out code
2. ✅ Configures AWS credentials
3. ✅ Creates `.env` file with secrets (includes AWS credentials)
4. ✅ Creates `.env.local` file with secrets (frontend)

### Phase 2: Deployment
5. ✅ Gets EC2 instance ID from IP address
6. ✅ Packages application files into tarball
7. ✅ Uploads package to temporary S3 bucket
8. ✅ Uses AWS Systems Manager (SSM) to deploy files to EC2

### Phase 3: Installation & Restart
9. ✅ Installs Python dependencies via SSM
10. ✅ Installs Node.js dependencies via SSM
11. ✅ Builds Next.js production bundle via SSM
12. ✅ Restarts all PM2 processes (mcp-server, backend, frontend) via SSM

### Phase 4: Verification
13. ✅ Performs health checks on all services (8000, 8001, 3000)
14. ✅ Cleans up temporary S3 bucket
15. ✅ Reports success or failure

---

## 📋 Important Notes

### ✅ Environment Variables in Production

**Backend `.env` on EC2:**
```bash
USE_MCP_HTTP=true
MCP_URL=http://localhost:8001          # Backend → MCP (same server)
CORS_ORIGINS=http://<EC2_IP>:3000     # Allow frontend origin
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<from-github-secrets>  # For backend API calls
AWS_SECRET_ACCESS_KEY=<from-github-secrets>
AWS_BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0
```

**Frontend `.env.local` on EC2:**
```bash
NEXT_PUBLIC_API_URL=http://54.123.45.67:8000  # ✓ EC2 IP (browser needs this!)
```

### ⚠️ Why NOT localhost for NEXT_PUBLIC_API_URL?

- ❌ `http://localhost:8000` - Browser thinks "my laptop"
- ✅ `http://EC2_PUBLIC_IP:8000` - Browser correctly points to EC2 server

Even though Next.js and backend are on same EC2, the JavaScript runs in the **user's browser**!

### ✅ Why localhost OK for MCP_URL?

- Backend (port 8000) calls MCP server (port 8001)
- Both on same EC2 instance
- Server-to-server communication within same machine
- `http://localhost:8001` works perfectly!

### 🔐 Deployment Method: AWS Systems Manager (SSM)

**Why SSM instead of SSH?**
- ✅ No SSH keys to manage
- ✅ Uses AWS IAM for authentication
- ✅ Audit trail in CloudTrail
- ✅ More secure (no open SSH port needed)
- ✅ Commands logged in CloudWatch

**Requirements:**
- EC2 must have `AmazonSSMManagedInstanceCore` IAM policy (Terraform includes this)
- SSM agent running on EC2 (Amazon Linux 2023 has it pre-installed)
- GitHub Actions IAM user needs `AmazonSSMFullAccess`

---

## 🔐 Security Best Practices

### ✅ DO:
- Use dedicated IAM user for GitHub Actions with minimal permissions
- Store AWS credentials in GitHub Secrets (encrypted)
- Use `.gitignore` to exclude `.env` files
- Rotate AWS access keys regularly
- Enable MFA on IAM user account
- Use AWS Systems Manager for secure deployments

### ❌ DON'T:
- Commit `.env` files with real secrets to git
- Hardcode AWS credentials in code
- Use root AWS account credentials
- Share AWS access keys in plaintext
- Commit `.env` files to the repository

---

## 🐛 Troubleshooting

### Deployment Fails at AWS Authentication
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are correct
- Check IAM user has required permissions
- Test locally: `aws sts get-caller-identity`

### Cannot Find EC2 Instance
- Verify `EC2_HOST` matches actual EC2 public IP
- Check instance is in `running` state
- Ensure instance is in the correct region (`AWS_REGION`)

### SSM Command Fails
- Verify SSM agent is running on EC2: `sudo systemctl status amazon-ssm-agent`
- Check EC2 IAM role has `AmazonSSMManagedInstanceCore` policy
- Test SSM connectivity: `aws ssm describe-instance-information`
- Check CloudWatch Logs for SSM errors

### Health Check Fails
- SSH to EC2 and check: `pm2 status`
- Check logs: `pm2 logs backend`
- Verify ports 8000, 8001, 3000 are open in security group
- Test manually: `curl http://EC2_IP:8000/health`

### Frontend Can't Connect to Backend
- Verify `NEXT_PUBLIC_API_URL` uses EC2 public IP, not localhost
- Check CORS settings in backend `.env`
- Verify security group allows inbound on port 8000

---

## 📚 References

- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Terraform Outputs](../terraform/outputs.tf) - Get EC2_HOST value
- [EC2 SSH Access](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AccessingInstancesLinux.html)
