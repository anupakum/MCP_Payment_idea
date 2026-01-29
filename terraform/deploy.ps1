# Terraform Deployment Script for Dispute Resolution System
# This script automates the deployment process

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('init', 'plan', 'apply', 'destroy', 'output', 'validate')]
    [string]$Action = 'plan',
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoApprove
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Dispute Resolution System - Terraform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the terraform directory
if (-not (Test-Path "main.tf")) {
    Write-Host "Error: This script must be run from the terraform directory" -ForegroundColor Red
    exit 1
}

# Check if Terraform is installed
try {
    $tfVersion = terraform --version
    Write-Host "✓ Terraform found: $($tfVersion.Split("`n")[0])" -ForegroundColor Green
} catch {
    Write-Host "✗ Terraform not found. Please install Terraform first." -ForegroundColor Red
    Write-Host "  Download from: https://www.terraform.io/downloads" -ForegroundColor Yellow
    exit 1
}

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version
    Write-Host "✓ AWS CLI found: $($awsVersion.Split("`n")[0])" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not found. Please install AWS CLI first." -ForegroundColor Red
    Write-Host "  Download from: https://aws.amazon.com/cli/" -ForegroundColor Yellow
    exit 1
}

# Check AWS credentials
try {
    $identity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ AWS credentials configured" -ForegroundColor Green
    } else {
        throw "Not configured"
    }
} catch {
    Write-Host "✗ AWS credentials not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Execute based on action
switch ($Action) {
    'init' {
        Write-Host "Initializing Terraform..." -ForegroundColor Cyan
        terraform init
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Terraform initialized successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Yellow
            Write-Host "  1. Copy terraform.tfvars.example to terraform.tfvars" -ForegroundColor White
            Write-Host "  2. Edit terraform.tfvars and set your key_name and allowed_ssh_cidr" -ForegroundColor White
            Write-Host "  3. Run: .\deploy.ps1 -Action plan" -ForegroundColor White
        }
    }
    
    'validate' {
        Write-Host "Validating Terraform configuration..." -ForegroundColor Cyan
        terraform validate
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Configuration is valid!" -ForegroundColor Green
        }
    }
    
    'plan' {
        # Check if terraform.tfvars exists
        if (-not (Test-Path "terraform.tfvars")) {
            Write-Host "Warning: terraform.tfvars not found!" -ForegroundColor Yellow
            Write-Host "Creating from template..." -ForegroundColor Yellow
            Copy-Item "terraform.tfvars.example" "terraform.tfvars"
            Write-Host ""
            Write-Host "Please edit terraform.tfvars and set your values:" -ForegroundColor Red
            Write-Host "  - key_name (required)" -ForegroundColor White
            Write-Host "  - allowed_ssh_cidr (recommended)" -ForegroundColor White
            Write-Host ""
            exit 1
        }
        
        Write-Host "Planning Terraform deployment..." -ForegroundColor Cyan
        terraform plan -out=tfplan
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Plan generated successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Review the plan above. To apply:" -ForegroundColor Yellow
            Write-Host "  .\deploy.ps1 -Action apply" -ForegroundColor White
        }
    }
    
    'apply' {
        if (-not (Test-Path "tfplan") -and -not $AutoApprove) {
            Write-Host "No plan file found. Generating plan first..." -ForegroundColor Yellow
            terraform plan -out=tfplan
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Plan generation failed!" -ForegroundColor Red
                exit 1
            }
        }
        
        Write-Host "Applying Terraform configuration..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "This will create:" -ForegroundColor Yellow
        Write-Host "  - EC2 instance (t3.medium)" -ForegroundColor White
        Write-Host "  - Security Group (ports 22, 8000, 8001, 3000)" -ForegroundColor White
        Write-Host "  - Elastic IP" -ForegroundColor White
        Write-Host "  - IAM Role and Policies" -ForegroundColor White
        Write-Host ""
        
        if ($AutoApprove) {
            terraform apply -auto-approve tfplan
        } else {
            terraform apply tfplan
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "✓ Deployment Successful!" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
            Write-Host ""
            
            # Show outputs
            Write-Host "Connection Information:" -ForegroundColor Cyan
            terraform output
            
            Write-Host ""
            Write-Host "Next Steps:" -ForegroundColor Yellow
            Write-Host "  1. SSH into your EC2 instance (see ssh_command above)" -ForegroundColor White
            Write-Host "  2. Clone your repository" -ForegroundColor White
            Write-Host "  3. Install dependencies and start services" -ForegroundColor White
            Write-Host ""
            Write-Host "See README.md for detailed deployment steps." -ForegroundColor Cyan
            
            # Clean up plan file
            if (Test-Path "tfplan") {
                Remove-Item "tfplan"
            }
        } else {
            Write-Host ""
            Write-Host "✗ Deployment failed!" -ForegroundColor Red
            Write-Host "Check the errors above and try again." -ForegroundColor Yellow
        }
    }
    
    'destroy' {
        Write-Host "WARNING: This will destroy all infrastructure!" -ForegroundColor Red
        Write-Host "This includes:" -ForegroundColor Yellow
        Write-Host "  - EC2 instance" -ForegroundColor White
        Write-Host "  - Elastic IP" -ForegroundColor White
        Write-Host "  - Security Group" -ForegroundColor White
        Write-Host "  - IAM Role and Policies" -ForegroundColor White
        Write-Host ""
        
        if (-not $AutoApprove) {
            $confirmation = Read-Host "Are you sure you want to destroy? Type 'yes' to confirm"
            if ($confirmation -ne 'yes') {
                Write-Host "Aborted." -ForegroundColor Yellow
                exit 0
            }
        }
        
        Write-Host ""
        Write-Host "Destroying infrastructure..." -ForegroundColor Red
        
        if ($AutoApprove) {
            terraform destroy -auto-approve
        } else {
            terraform destroy
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Infrastructure destroyed successfully." -ForegroundColor Green
        }
    }
    
    'output' {
        Write-Host "Terraform Outputs:" -ForegroundColor Cyan
        terraform output
    }
}

Write-Host ""
