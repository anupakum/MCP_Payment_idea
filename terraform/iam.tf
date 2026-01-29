# IAM Role for EC2 Instance
resource "aws_iam_role" "ec2_role" {
  name_prefix = "${var.project_name}-ec2-role-"
  description = "IAM role for dispute resolution EC2 instance"

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
    Name           = "${var.project_name}-ec2-role"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }
}

# IAM Policy for DynamoDB Access
resource "aws_iam_policy" "dynamodb_policy" {
  name_prefix = "${var.project_name}-dynamodb-policy-"
  description = "Allow EC2 to access DynamoDB tables for dispute resolution"

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
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable"
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

  tags = {
    Name           = "${var.project_name}-dynamodb-policy"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }
}

# IAM Policy for Bedrock Access
resource "aws_iam_policy" "bedrock_policy" {
  name_prefix = "${var.project_name}-bedrock-policy-"
  description = "Allow EC2 to invoke AWS Bedrock models (Claude 4.5 Haiku)"

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
          var.bedrock_model_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name           = "${var.project_name}-bedrock-policy"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }
}

# IAM Policy for CloudWatch Logs (optional but recommended)
resource "aws_iam_policy" "cloudwatch_policy" {
  name_prefix = "${var.project_name}-cloudwatch-policy-"
  description = "Allow EC2 to write logs to CloudWatch"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/ec2/${var.project_name}*"
      }
    ]
  })

  tags = {
    Name           = "${var.project_name}-cloudwatch-policy"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }
}

# Attach DynamoDB policy to role
resource "aws_iam_role_policy_attachment" "dynamodb_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.dynamodb_policy.arn
}

# Attach Bedrock policy to role
resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

# Attach CloudWatch policy to role
resource "aws_iam_role_policy_attachment" "cloudwatch_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.cloudwatch_policy.arn
}

# Attach SSM managed policy (for AWS Systems Manager Session Manager - optional SSH alternative)
resource "aws_iam_role_policy_attachment" "ssm_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance Profile (links IAM role to EC2 instance)
resource "aws_iam_instance_profile" "ec2_profile" {
  name_prefix = "${var.project_name}-ec2-profile-"
  role        = aws_iam_role.ec2_role.name

  tags = {
    Name           = "${var.project_name}-ec2-profile"
    agent_name     = var.agent_name
    agent_domain   = var.agent_domain
    featured_agent = var.featured_agent
    agent_owner    = var.agent_owner
  }
}
