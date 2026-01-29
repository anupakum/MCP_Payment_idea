terraform_s3_bucket = "ptr-ag-bnk-pmts-dispute-resol" # Application code deployment bucket (code sync from GitHub)
# Terraform state is stored in: ptr-ag-bnk-pmts-dispute-resol-terraform-locks
# DynamoDB locking table: terraform-lock-prod
s3_document_bucket = "ptr-dspt-rsln-agt-prod"
project_name       = "dispute-resolution-prod"
environment        = "prod"
# agent_identifier is passed via -var in GitHub Actions workflow, not hardcoded here
instance_type     = "t3.small" # Production uses larger instance
# enable_elastic_ip = true       # Production should have static IP
domain_name       = "disp-reccom-prod.orchestrateai.tech"         # Optional: Set to your domain (e.g., "dispute.example.com") or leave empty to use PUBLIC_IP
