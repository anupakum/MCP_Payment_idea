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
  default     = "t3.medium" # 2 vCPU, 4 GB RAM - good for CrewAI agents

  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Instance type must be from t3 family for cost optimization."
  }
}

variable "key_name" {
  description = "EC2 key pair name for SSH access (must exist in AWS)"
  type        = string
  default     = "test-ec2"
  # Set this in terraform.tfvars
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into EC2 instance"
  type        = string
  default     = "0.0.0.0/0" # SECURITY WARNING: Change to your IP address!

  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0))
    error_message = "Must be a valid CIDR block (e.g., 1.2.3.4/32)."
  }
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

variable "enable_elastic_ip" {
  description = "Whether to allocate an Elastic IP (static IP)"
  type        = bool
  default     = false
}

variable "dynamodb_tables" {
  description = "Existing DynamoDB table names (already created)"
  type = object({
    customer_table = string
    case_table     = string
  })
  default = {
    customer_table = "ptr_dispute_resol_customer_cards_and_transactions"
    case_table     = "ptr_dispute_resol_case_db"
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "dispute-resolution"
}

variable "agent_identifier" {
  description = "Agent identifier to append to EC2 instance name (e.g., agent1, john, test)"
  type        = string
  default     = "default"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.agent_identifier))
    error_message = "Agent identifier must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "bedrock_model_arn" {
  description = "ARN pattern for Bedrock Claude model"
  type        = string
  default     = "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "terraform_s3_bucket" {
  description = "S3 bucket name for Terraform state storage"
  type        = string
}

variable "s3_document_bucket" {
  description = "S3 bucket name for document storage in S3Client"
  type        = string
}

variable "domain_name" {
  description = "Optional domain name for the application (e.g., dispute.example.com). If not provided, PUBLIC_IP will be used."
  type        = string
  default     = ""
}

# Agent Metadata Tags
variable "agent_name" {
  description = "Name of the agent/application"
  type        = string
  default     = "Disputes Resolution"
}

variable "agent_domain" {
  description = "Domain/category of the agent"
  type        = string
  default     = "Banking"
}

variable "featured_agent" {
  description = "Whether this is a featured agent"
  type        = string
  default     = "No"
}

variable "agent_owner" {
  description = "Owner(s) of the agent"
  type        = string
  default     = "Suhas/Viplove/Vikram"
}
