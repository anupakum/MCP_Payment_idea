# Simple EC2 Deployment Plan - Dispute Resolution System

## 🎯 Simplified Architecture

**Your Requirements:**
- ✅ Backend + Frontend on **single EC2 instance**
- ✅ DynamoDB tables **already exist** (no Terraform needed)
- ⏸️ Load balancing - **defer to later**
- ⏸️ SSL/HTTPS - **defer to later**

---

## 🏗️ Minimal Infrastructure

```
Internet → EC2 Instance (Public IP)
           ├── Backend (Main):    0.0.0.0:8000 (FastAPI)
           ├── Backend (MCP):     0.0.0.0:8001 (Optional MCP HTTP Server)
           ├── Frontend:          0.0.0.0:3000 (Next.js)
           └── IAM Role → DynamoDB + Bedrock
```

**Single EC2 Instance:**
- **Type**: `t3.medium` (2 vCPU, 4 GB RAM)
- **OS**: Amazon Linux 2023 or Ubuntu 22.04
- **Storage**: 30 GB gp3 EBS
- **Public IP**: Auto-assigned
- **Security Group**: Ports 22 (SSH), 8000 (backend), 8001 (MCP - optional), 3000 (frontend)

**Note**: Port 8001 only needed if you set `USE_MCP_HTTP=true` in your environment.

---

## 📁 Minimal Terraform Files Needed

```
terraform/
├── main.tf           # Provider + backend config
├── variables.tf      # Input variables (region, instance type, etc.)
├── ec2.tf            # EC2 instance + security group
├── iam.tf            # IAM role for DynamoDB + Bedrock access
├── outputs.tf        # EC2 public IP
└── terraform.tfvars  # Your actual values (gitignored)
```

**That's it! Only 5 files.**

---

## 💰 Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **EC2 t3.medium** | On-demand, 730 hrs/month | ~$30 |
| **EBS Storage** | 30 GB gp3 | ~$2.50 |
| **Data Transfer** | 100 GB outbound | ~$9 |
| **Elastic IP** | 1 static IP (optional) | $3.60 if unused |
| **DynamoDB** | Existing (you manage) | $0 |
| **Bedrock** | Pay-per-use | ~$15 (1M tokens) |
| **Total** | | **~$51.50/month** |

**vs ECS Fargate (~$152/month)** = **67% cheaper!**

---

## 🚀 Deployment Workflow

### Step 1: Create Terraform Configuration

I'll generate these files:
1. `main.tf` - AWS provider setup
2. `variables.tf` - Configurable parameters
3. `ec2.tf` - EC2 instance + security group
4. `iam.tf` - IAM role for AWS service access
5. `outputs.tf` - EC2 public IP output

### Step 2: Deploy Infrastructure

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

**Output**: EC2 public IP address (e.g., `54.123.45.67`)

### Step 3: Connect to EC2 & Setup Environment

```powershell
# SSH into EC2 (use PEM key from AWS)
ssh -i "your-key.pem" ec2-user@54.123.45.67

# On EC2: Install dependencies
sudo yum update -y
sudo yum install -y python3.11 python3.11-pip nodejs npm git

# Clone your repo (or upload via SCP)
git clone https://github.com/Capgemini-Innersource/ptr_ag_bnk_pmts_dispute_resol.git
cd ptr_ag_bnk_pmts_dispute_resol

# Install Python packages
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Node packages
cd web
npm install
cd ..
```

### Step 4: Configure Environment Variables

```bash
# Create .env file on EC2 (NO hardcoded credentials!)
cat > .env << 'EOF'
# MCP Mode - Default: HTTP mode (runs both 8000 and 8001)
USE_MCP_HTTP=true
# To use Direct Python mode (single process, port 8000 only), set to false

# MCP HTTP Server configuration
MCP_URL=http://localhost:8001
MCP_PORT=8001

# AWS - Uses IAM role, NO credentials needed!
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0
AWS_BEDROCK_REGION=us-east-1

# FastAPI
PORT=8000
HOST=0.0.0.0

# Frontend CORS
CORS_ORIGINS=http://localhost:3000

# Logging
LOG_LEVEL=INFO
EOF
```

**IMPORTANT**: IAM role provides credentials automatically - no keys needed!

**Default Mode**: HTTP-based MCP (`USE_MCP_HTTP=true`)
- Runs **both** port 8000 (main) and port 8001 (MCP server)
- To use Direct Python mode (single process), change to `USE_MCP_HTTP=false`

### Step 5: Run Applications with PM2 (Process Manager)

```bash
# Install PM2 for process management
sudo npm install -g pm2

# Start Backend - Default: HTTP Mode (both ports 8000 and 8001)
pm2 start "python -m mcp.http_server" --name mcp-server     # Port 8001
pm2 start "python -m mcp.main" --name dispute-backend       # Port 8000

# Alternative: Direct Python Mode (if USE_MCP_HTTP=false)
# pm2 start "python -m mcp.main" --name dispute-backend

# Start frontend
cd web
pm2 start "npm run start" --name dispute-frontend

# Check status
pm2 status

# Save PM2 config for auto-restart
pm2 save
pm2 startup  # Follow the command it outputs
```

### Step 6: Access Your Application

```
Backend (Main):  http://54.123.45.67:8000
Backend (MCP):   http://54.123.45.67:8001
Frontend:        http://54.123.45.67:3000

Test:
curl http://54.123.45.67:8000/health
curl http://54.123.45.67:8001/health
```

---

## 📋 Terraform File Details

### 1. `main.tf` - Provider Configuration

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Store state in S3 (recommended for team)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "dispute-resolution/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "DisputeResolution"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

### 2. `variables.tf` - Configuration Inputs

```hcl
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"  # 2 vCPU, 4 GB RAM
}

variable "key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  # You'll set this in terraform.tfvars
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (your IP)"
  type        = string
  default     = "0.0.0.0/0"  # INSECURE! Change to your IP
}

variable "dynamodb_tables" {
  description = "Existing DynamoDB table names"
  type = object({
    customer_table = string
    case_table     = string
  })
  default = {
    customer_table = "ptr_dispute_resol_customer_cards_and_transactions"
    case_table     = "ptr_dispute_resol_case_db"
  }
}
```

### 3. `ec2.tf` - EC2 Instance & Security Group

```hcl
# Security Group for EC2
resource "aws_security_group" "dispute_ec2_sg" {
  name_prefix = "dispute-ec2-sg-"
  description = "Security group for dispute resolution EC2"

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Backend API (Main FastAPI)
  ingress {
    description = "FastAPI Backend"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to internet
  }

  # Backend API (MCP HTTP Server - optional)
  ingress {
    description = "MCP HTTP Server (optional)"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to internet
  }

  # Frontend
  ingress {
    description = "Next.js Frontend"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to internet
  }

  # Outbound traffic (for DynamoDB, Bedrock, etc.)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "dispute-resolution-ec2-sg"
  }
}

# Get latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 Instance
resource "aws_instance" "dispute_server" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type
  key_name      = var.key_name

  # Attach IAM role for AWS service access
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  # Security group
  vpc_security_group_ids = [aws_security_group.dispute_ec2_sg.id]

  # Storage
  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  # User data script (runs on first boot)
  user_data = <<-EOF
              #!/bin/bash
              # Update system
              yum update -y

              # Install Python 3.11
              yum install -y python3.11 python3.11-pip

              # Install Node.js 18
              curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
              yum install -y nodejs

              # Install git
              yum install -y git

              # Install PM2 globally
              npm install -g pm2

              # Create app directory
              mkdir -p /home/ec2-user/app
              chown ec2-user:ec2-user /home/ec2-user/app

              echo "Instance setup complete!" > /home/ec2-user/setup-complete.txt
              EOF

  tags = {
    Name = "dispute-resolution-server"
  }
}

# Elastic IP (optional - for static IP)
resource "aws_eip" "dispute_eip" {
  instance = aws_instance.dispute_server.id
  domain   = "vpc"

  tags = {
    Name = "dispute-resolution-eip"
  }
}
```

### 4. `iam.tf` - IAM Role for EC2

```hcl
# IAM Role for EC2 instance
resource "aws_iam_role" "ec2_role" {
  name_prefix = "dispute-ec2-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "dispute-resolution-ec2-role"
  }
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "dynamodb_policy" {
  name_prefix = "dispute-dynamodb-policy-"
  description = "Allow EC2 to access DynamoDB tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_tables.customer_table}",
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_tables.customer_table}/index/*",
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_tables.case_table}",
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_tables.case_table}/index/*"
        ]
      }
    ]
  })
}

# IAM Policy for Bedrock access
resource "aws_iam_policy" "bedrock_policy" {
  name_prefix = "dispute-bedrock-policy-"
  description = "Allow EC2 to invoke Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
        ]
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "dynamodb_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.dynamodb_policy.arn
}

resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

# Instance profile (links role to EC2)
resource "aws_iam_instance_profile" "ec2_profile" {
  name_prefix = "dispute-ec2-profile-"
  role        = aws_iam_role.ec2_role.name
}
```

### 5. `outputs.tf` - Output Values

```hcl
output "ec2_public_ip" {
  description = "Public IP address of EC2 instance"
  value       = aws_eip.dispute_eip.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.dispute_server.id
}

output "backend_url" {
  description = "Backend API URL"
  value       = "http://${aws_eip.dispute_eip.public_ip}:8000"
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "http://${aws_eip.dispute_eip.public_ip}:3000"
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i your-key.pem ec2-user@${aws_eip.dispute_eip.public_ip}"
}
```

### 6. `terraform.tfvars.example` - Example Configuration

```hcl
# Copy this to terraform.tfvars and fill in your values
# (terraform.tfvars should be in .gitignore)

aws_region = "us-east-1"
environment = "dev"
instance_type = "t3.medium"

# REQUIRED: Create an EC2 key pair in AWS Console first!
key_name = "your-ec2-keypair-name"

# RECOMMENDED: Restrict to your IP only
# Get your IP: curl ifconfig.me
allowed_ssh_cidr = "YOUR.IP.ADDRESS.HERE/32"
```

---

## 🔐 Security Notes

### ✅ **SECURE (Using IAM Role)**
```bash
# .env file on EC2 - NO credentials!
AWS_REGION=us-east-1
```

EC2 automatically gets credentials from IAM role.

### ❌ **INSECURE (Hardcoded Keys)**
```bash
# NEVER do this on EC2!
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Additional Security:
1. **Change `allowed_ssh_cidr`** to your IP only (not `0.0.0.0/0`)
2. **Use Session Manager** instead of SSH (no port 22 needed)
3. **Enable CloudWatch logging** for audit trail
4. **Setup WAF** when you add load balancer later

---

## 🔄 Future Enhancements (Later)

When you're ready, easily add:

### 1. Load Balancer (ALB)
```hcl
# Add to terraform/alb.tf
resource "aws_lb" "main" {
  # Route traffic to EC2:8000 and EC2:3000
}
```

### 2. SSL Certificate (ACM + Route53)
```hcl
# Add to terraform/acm.tf
resource "aws_acm_certificate" "cert" {
  domain_name = "disputes.yourcompany.com"
}
```

### 3. Auto Scaling Group
```hcl
# Replace single EC2 with ASG
resource "aws_autoscaling_group" "asg" {
  min_size = 1
  max_size = 3
}
```

### 4. RDS Database
```hcl
# If you want to move away from DynamoDB
resource "aws_db_instance" "postgres" {
  engine = "postgres"
}
```

---

## 📝 Quick Start Commands

```powershell
# 1. Create EC2 key pair in AWS Console
# Download .pem file to C:\Users\vvikram\.ssh\dispute-key.pem

# 2. Create terraform.tfvars
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your key name and IP

# 3. Deploy infrastructure
terraform init
terraform plan
terraform apply

# 4. Get EC2 IP
terraform output ec2_public_ip

# 5. SSH to EC2
ssh -i ~/.ssh/dispute-key.pem ec2-user@<EC2_IP>

# 6. Deploy application (on EC2)
git clone <your-repo>
cd ptr_ag_bnk_pmts_dispute_resol
source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && cd ..

# 7. Start services with PM2 (default: HTTP mode with both ports)
pm2 start "python -m mcp.http_server" --name mcp-server
pm2 start "python -m mcp.main" --name backend
pm2 start "npm run start" --name frontend --cwd web
pm2 save
pm2 startup

# 8. Test
curl http://<EC2_IP>:8000/health
```

---

## ❓ Next Steps

**Do you want me to:**

1. ✅ Generate all 6 Terraform files ready to use?
2. ✅ Create a deployment script (`deploy.ps1`) to automate everything?
3. ✅ Update your `.env.example` to remove hardcoded credentials?
4. ✅ Create a `.gitignore` for Terraform files?
5. ✅ Add health check endpoint to your FastAPI app?

Let me know and I'll create everything for you!
