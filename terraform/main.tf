terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Store state in S3 (recommended for team collaboration)
  # Uncomment and configure after creating S3 bucket
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "dispute-resolution/terraform.tfstate"
  #   region = "us-east-1"
  #   encrypt = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project       = "DisputeResolution"
      Environment   = var.environment
      ManagedBy     = "Terraform"
      Owner         = "Capgemini"
      agent_name    = var.agent_name
      agent_domain  = var.agent_domain
      featured_agent = var.featured_agent
      agent_owner   = var.agent_owner
    }
  }
}
