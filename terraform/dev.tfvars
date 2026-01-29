terraform_s3_bucket = "dev-ptr-ag-bnk-pmts-dispute-resol" # Application code deployment bucket (code sync from GitHub)
# Terraform state is stored in: dev-ptr-ag-bnk-pmts-dispute-resol-terraform-locks
# DynamoDB locking table: terraform-lock-dev
s3_document_bucket = "ptr-dspt-rsln-agt-dev"
project_name       = "dispute-resolution-dev"
environment        = "dev"
# agent_identifier is passed via -var in GitHub Actions workflow, not hardcoded here
domain_name = "disp-reccom-dev.orchestrateai.tech" # Optional: Set to your domain (e.g., "dev.dispute.example.com") or leave empty to use PUBLIC_IP
instance_type     = "t3.small" 