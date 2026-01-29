# EC2 Instance Outputs
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.dispute_server.id
}

output "ec2_public_ip" {
  description = "Public IP address of EC2 instance (Elastic IP if enabled, otherwise dynamic)"
  value       = var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip
}

output "ec2_private_ip" {
  description = "Private IP address of EC2 instance"
  value       = aws_instance.dispute_server.private_ip
}

# Application URLs
output "backend_main_url" {
  description = "Backend main API URL (FastAPI on port 8000)"
  value       = "http://${var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip}:8000"
}

output "backend_mcp_url" {
  description = "Backend MCP HTTP Server URL (port 8001)"
  value       = "http://${var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip}:8001"
}

output "frontend_url" {
  description = "Frontend URL (Next.js on port 3000)"
  value       = "http://${var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip}:3000"
}

# SSH Connection
output "ssh_command" {
  description = "SSH command to connect to EC2 instance"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip}"
}

output "ssm_command" {
  description = "AWS Systems Manager Session Manager command (alternative to SSH)"
  value       = "aws ssm start-session --target ${aws_instance.dispute_server.id}"
}

# Security Group
output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.dispute_ec2_sg.id
}

# IAM Role
output "iam_role_arn" {
  description = "IAM role ARN attached to EC2 instance"
  value       = aws_iam_role.ec2_role.arn
}

output "iam_role_name" {
  description = "IAM role name"
  value       = aws_iam_role.ec2_role.name
}

# Quick Start Guide
output "quick_start_guide" {
  description = "Quick start instructions"
  value = <<-EOT
    
    ========================================
    Dispute Resolution System - Deployed!
    ========================================
    
    1. Connect to EC2:
       ${format("ssh -i ~/.ssh/%s.pem ec2-user@%s", var.key_name, var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
    
    2. Clone your repository:
       git clone https://github.com/Capgemini-Innersource/ptr_ag_bnk_pmts_dispute_resol.git
       cd ptr_ag_bnk_pmts_dispute_resol
    
    3. Install dependencies:
       python3 -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
       cd web && npm install && cd ..
    
    4. Configure environment (create .env file):
       USE_MCP_HTTP=true
       AWS_REGION=${var.aws_region}
       (IAM role provides AWS credentials automatically)
    
    5. Start services with PM2:
       pm2 start "python -m mcp.http_server" --name mcp-server
       pm2 start "python -m mcp.main" --name backend
       pm2 start "npm run start" --name frontend --cwd web
       pm2 save && pm2 startup
    
    6. Access applications:
       Backend (Main):  ${format("http://%s:8000", var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
       Backend (MCP):   ${format("http://%s:8001", var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
       Frontend:        ${format("http://%s:3000", var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
    
    7. Test:
       curl ${format("http://%s:8000/health", var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
       curl ${format("http://%s:8001/health", var.enable_elastic_ip ? aws_eip.dispute_eip[0].public_ip : aws_instance.dispute_server.public_ip)}
    
    ========================================
  EOT
}
