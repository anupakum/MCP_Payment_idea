# Security Group for EC2 Instance
resource "aws_security_group" "dispute_ec2_sg" {
  name_prefix = "${var.project_name}-ec2-sg-"
  description = "Security group for dispute resolution EC2 instance"

  # SSH access
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Backend API - Main FastAPI (port 8000)
  ingress {
    description = "FastAPI Backend (Main)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Open to internet
  }

  # Backend API - MCP HTTP Server (port 8001)
  ingress {
    description = "MCP HTTP Server"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Open to internet
  }

  # Frontend - Next.js (port 3000)
  ingress {
    description = "Next.js Frontend"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Open to internet
  }

  # Outbound traffic - Required for DynamoDB, Bedrock, package downloads
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "${var.project_name}-${var.agent_identifier}-ec2-sg"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }

  lifecycle {
    create_before_destroy = true
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

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# EC2 Instance
resource "aws_instance" "dispute_server" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type
  key_name      = var.key_name

  # Attach IAM role for AWS service access (DynamoDB, Bedrock)
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  # Security group
  vpc_security_group_ids = [aws_security_group.dispute_ec2_sg.id]

  # Storage configuration
  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name           = "${var.project_name}-${var.agent_identifier}-root-volume"
      agent_name     = var.agent_name
      agent_domain   = var.agent_domain
      featured_agent = var.featured_agent
      agent_owner    = var.agent_owner
    }
  }

  # User data script - runs on first boot
  user_data = <<-EOF
              #!/bin/bash
              set -e  # Exit on error

              # Redirect all output to log file
              exec > >(tee /var/log/user-data.log) 2>&1

              echo "========================================"
              echo "Starting EC2 User Data Script (as root)"
              echo "Date: $(date)"
              echo "========================================"

              # Create app directory as root first (user_data runs as root)
              echo "Creating application directory..."
              mkdir -p /home/ec2-user/dispute-resolution
              chown -R ec2-user:ec2-user /home/ec2-user/dispute-resolution

              # Switch to ec2-user for ALL remaining operations
              echo "Switching to ec2-user for all operations..."
              sudo -u ec2-user -H bash << 'USERSCRIPT'
              set -e  # Exit on error for user script too

              echo "========================================"
              echo "Running as user: $(whoami)"
              echo "Home directory: $HOME"
              echo "========================================"

              # Set environment variables
              export USE_MCP_HTTP="true"
              export UVLOOP_DISABLE=1
              export PYTHONASYNCIODEBUG=1
              export S3_BUCKET_NAME="${var.s3_document_bucket}"
              export DOMAIN_NAME="${var.domain_name}"

              # Change to app directory
              cd /home/ec2-user/dispute-resolution

              # Sync files from S3 as ec2-user
              echo "Syncing files from S3 as ec2-user..."
              aws s3 sync s3://${var.terraform_s3_bucket}/ . --exclude ".git/*"

              if [ $? -ne 0 ]; then
                  echo "ERROR: Failed to sync from S3"
                  exit 1
              fi

              # Make startup.sh executable
              chmod +x startup.sh

              # Verify ownership
              echo "Verifying file ownership..."
              ls -la startup.sh

              # Run startup script as ec2-user
              echo "Running startup.sh as ec2-user..."
              bash startup.sh

              if [ $? -ne 0 ]; then
                  echo "ERROR: startup.sh failed with exit code $?"
                  exit 1
              fi

              echo "========================================"
              echo "User Script Completed Successfully"
              echo "Date: $(date)"
              echo "========================================"
              USERSCRIPT

              echo "========================================"
              echo "User Data Script Completed Successfully"
              echo "Date: $(date)"
              echo "========================================"
              EOF

  # Metadata options for security
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Require IMDSv2
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  tags = {
    Name           = "${var.project_name}-${var.agent_identifier}-server"
    Agent          = var.agent_identifier
    Environment    = var.environment
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }

  # Ensure IAM profile is created first
  depends_on = [aws_iam_instance_profile.ec2_profile]
}

# Elastic IP (optional - for static IP address)
resource "aws_eip" "dispute_eip" {
  count    = var.enable_elastic_ip ? 1 : 0
  instance = aws_instance.dispute_server.id
  domain   = "vpc"

  tags = {
    Name           = "${var.project_name}-${var.agent_identifier}-eip"
    Agent          = var.agent_identifier
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }

  # Ensure EC2 instance is created first
  depends_on = [aws_instance.dispute_server]
}
