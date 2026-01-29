#!/bin/bash
# Dispute Resolution System - Unix/Linux/Mac Startup Script
# This script clones the repository and starts backend (FastAPI) and frontend (Next.js) servers
#
# Environment Variables:
#   - DOMAIN_NAME: Optional domain name (e.g., "dispute.example.com"). If not set, PUBLIC_IP is used.
#   - USE_MCP_HTTP: Set to "true" to start MCP HTTP server on port 8001
#   - S3_BUCKET_NAME: S3 bucket for document storage

echo "========================================"
echo "Starting Dispute Resolution System"
echo "========================================"
echo ""

# ============================================================================
# GitHub Repository Configuration (Hardcoded)
# ============================================================================

USE_MCP_HTTP="true"
# ============================================================================
# Determine Host URL (DOMAIN_NAME or PUBLIC_IP)
# ============================================================================
if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "" ]; then
    # Use domain name if provided from Terraform
    HOST_URL="$DOMAIN_NAME"
    echo "✓ Using DOMAIN_NAME from Terraform: $HOST_URL"
else
    # Fall back to PUBLIC_IP from EC2 metadata
    echo "⚠️  DOMAIN_NAME not provided, fetching PUBLIC_IP from EC2 metadata..."
    TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
      -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

    PUBLIC_IP=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" \
      http://169.254.169.254/latest/meta-data/public-ipv4)

    HOST_URL="$PUBLIC_IP"
    echo "✓ Using PUBLIC_IP: $HOST_URL"
fi

echo ""
echo "========================================"
echo "🌐 Application URLs"
echo "========================================"
echo "Backend API will be: http://$HOST_URL:8000"
echo "Frontend UI will be: http://$HOST_URL:3000"
if [ "$USE_MCP_HTTP" = "true" ]; then
    echo "MCP Server will be: http://localhost:8001"
fi
echo "========================================"
echo ""
echo 'export HOST_URL='"$HOST_URL"'' >> ~/.bashrc
echo 'export USE_MCP_HTTP='"$USE_MCP_HTTP"'' >> ~/.bashrc
source ~/.bashrc
echo ""
# Persist environment variables for PM2/systemd on reboot
echo "Persisting application environment variables..."
APP_DIR=$(pwd)
sudo bash -c "cat > /etc/profile.d/pm2_app_env.sh << EOF
export HOST_URL=\"$HOST_URL\"
export USE_MCP_HTTP=\"$USE_MCP_HTTP\"
export UVLOOP_DISABLE=1
export PYTHONASYNCIODEBUG=1
export APP_DIR=\"$APP_DIR\"
EOF"
echo "✓ Environment variables persisted to /etc/profile.d/pm2_app_env.sh"
# ============================================================================
# Install System Dependencies (Python, Node.js, Git)
# ============================================================================
echo "========================================"
echo "Installing System Dependencies"
echo "========================================"

# Detect OS and install dependencies
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Detect Linux distribution (including Amazon Linux 2023 which is Fedora-like)
    if [ -f /etc/redhat-release ] || [ -f /etc/centos-release ] || [ -f /etc/fedora-release ] || grep -q "ID_LIKE.*fedora" /etc/os-release 2>/dev/null; then
        # Check if it's Amazon Linux 2023 specifically
        if grep -q "ID=\"amzn\"" /etc/os-release 2>/dev/null && grep -q "VERSION_ID=\"2023\"" /etc/os-release 2>/dev/null; then
            # Amazon Linux 2023
            echo "Detected Amazon Linux 2023"
            echo "Updating system packages..."
            sudo dnf update -y

            echo "Installing Git..."
            sudo dnf install -y git

            echo "Installing Python 3.11 (Amazon Linux 2023 compatible)..."
            sudo dnf install -y python3.11 python3.11-pip

            echo "Upgrading Node.js to LTS (22.x)..."
            # Remove existing Node.js 18.x first to avoid conflicts
            sudo dnf remove -y nodejs npm || true
            echo "Adding Node.js 22.x LTS repository..."
            curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
            sudo dnf install -y nodejs
        else
            # RHEL/CentOS/Fedora
            echo "Detected RHEL-based distribution"
            echo "Updating system packages..."
            sudo dnf update -y

            echo "Installing Git..."
            sudo dnf install -y git

            echo "Installing Python 3.13 (latest)..."
            sudo dnf install -y python3.13 python3.13-pip python3.13-venv || {
                echo "Python 3.13 not available, falling back to Python 3.11..."
                sudo dnf install -y python3.11 python3.11-pip python3.11-venv
            }

            echo "Installing Node.js LTS (22.x)..."
            sudo dnf install -y nodejs npm || {
                echo "Adding Node.js 22.x LTS repository..."
                curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
                sudo dnf install -y nodejs
            }
        fi

    elif [ -f /etc/debian_version ] || [ -f /etc/ubuntu-release ] || grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        # Debian/Ubuntu
        echo "Detected Debian-based distribution"
        echo "Updating system packages..."
        sudo apt-get update -y

        echo "Installing Git..."
        sudo apt-get install -y git

        echo "Installing Python 3.13 (latest)..."
        sudo apt-get install -y python3.13 python3.13-pip python3.13-venv || {
            echo "Python 3.13 not available, falling back to Python 3.11..."
            sudo apt-get install -y python3.11 python3.11-pip python3.11-venv
        }

        echo "Installing Node.js LTS (22.x)..."
        sudo apt-get install -y nodejs npm || {
            echo "Adding Node.js 22.x LTS repository..."
            curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
            sudo apt-get install -y nodejs
        }

    else
        echo "WARNING: Unknown Linux distribution, attempting generic installation..."
        echo "Installing common packages..."
        sudo yum install -y git python3.13 python3.13-pip python3.13-venv nodejs npm 2>/dev/null || \
        sudo apt-get install -y git python3.13 python3.13-pip python3.13-venv nodejs npm 2>/dev/null || {
            echo "Trying fallback to Python 3.11..."
            sudo yum install -y git python3.11 python3.11-pip python3.11-venv nodejs npm 2>/dev/null || \
            sudo apt-get install -y git python3.11 python3.11-pip python3.11-venv nodejs npm 2>/dev/null || {
                echo "ERROR: Could not install dependencies automatically"
                echo "Please manually install: git, python3.13 or python3.11, nodejs, npm"
                exit 1
            }
        }
    fi
else
    echo "WARNING: Unsupported OS ($OSTYPE). Assuming dependencies are already installed."
fi

echo "✓ System dependencies installation completed"

# ============================================================================
# Create Python Command Symlinks
# ============================================================================
echo ""
echo "========================================"
echo "Creating Python Command Symlinks"
echo "========================================"

# Create only python symlink (preserve python3 for system tools)
if command -v python3.11 &> /dev/null; then
    PYTHON_PATH=$(which python3.11)
    echo "Found Python 3.11 at: $PYTHON_PATH"

    # Only create python symlink (preserve python3 as system default)
    if [ ! -L /usr/bin/python ] || [ "$(readlink -f /usr/bin/python)" != "$(readlink -f $PYTHON_PATH)" ]; then
        echo "Creating python symlink..."
        sudo ln -sf "$PYTHON_PATH" /usr/bin/python
    fi

    echo "✓ Python symlink created"
    echo "  python -> $(readlink -f /usr/bin/python)"
    echo "  python3 -> left as system default"
elif command -v python3.13 &> /dev/null; then
    PYTHON_PATH=$(which python3.13)
    echo "Found Python 3.13 at: $PYTHON_PATH"

    # Only create python symlink (preserve python3 as system default)
    if [ ! -L /usr/bin/python ] || [ "$(readlink -f /usr/bin/python)" != "$(readlink -f $PYTHON_PATH)" ]; then
        echo "Creating python symlink..."
        sudo ln -sf "$PYTHON_PATH" /usr/bin/python
    fi

    echo "✓ Python symlink created"
    echo "  python -> $(readlink -f /usr/bin/python)"
    echo "  python3 -> left as system default"
else
    echo "WARNING: Could not find Python 3.11 or 3.13 for symlink creation"
fi

# Verify python commands work
echo ""
echo "Verifying Python commands..."
if command -v python3 &> /dev/null; then
    echo "✓ python3 command available: $(python3 --version 2>&1) (system default)"
else
    echo "❌ python3 command not working"
fi

if command -v python &> /dev/null; then
    echo "✓ python command available: $(python --version 2>&1)"
else
    echo "❌ python command not working"
fi

# Install PM2 globally
echo "Installing PM2 process manager..."
sudo npm install -g pm2

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install PM2"
    exit 1
fi

echo "✓ PM2 installed successfully"

# Enable PM2 startup on boot (autorestart after reboot)
echo "Configuring PM2 to auto-start on boot..."
sudo env PATH=$PATH pm2 startup systemd -u "$USER" --hp "$HOME" || true
echo "✓ PM2 startup configured"

# ============================================================================
# Check Python Version
# ============================================================================
echo ""
echo "========================================"
echo "Verifying Python Installation"
echo "========================================"

if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo "✓ Found Python 3.13 (latest)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "✓ Found Python 3.11 (fallback)"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo "✓ Found Python 3.10 (minimum requirement)"
else
    echo "ERROR: Python 3.10+ is required but not found after installation"
    echo "Installation may have failed. Please check system package manager."
    exit 1
fi

$PYTHON_CMD --version

# ============================================================================
# Remove Existing Repository and Clone Fresh
# ============================================================================
# echo ""
# echo "========================================"
# echo "Cleaning and Cloning Repository"
# echo "========================================"

# # Check if GITHUB_PAT is set (passed from GitHub Actions)
# if [ -z "$GITHUB_PAT" ]; then
#     echo "ERROR: GITHUB_PAT environment variable is not set"
#     echo "This should be passed from GitHub Actions workflow"
#     exit 1
# fi

# # Check if GITHUB_BRANCH is set (passed from GitHub Actions)
# if [ -z "$GITHUB_BRANCH" ]; then
#     echo "WARNING: GITHUB_BRANCH not set, defaulting to 'main'"
#     GITHUB_BRANCH="main"
# fi

# # Remove existing repository if present
# if [ -d "$APP_DIR" ]; then
#     echo "Removing existing repository at $APP_DIR..."
#     rm -rf "$APP_DIR"
#     echo "✓ Existing repository removed"
# fi

# echo "Cloning branch: $GITHUB_BRANCH"
# echo "Repository: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}.git"

# # Clone repository using PAT
# git clone -b "$GITHUB_BRANCH" \
#     "https://${GITHUB_PAT}@github.com/${GITHUB_ORG}/${GITHUB_REPO}.git" \
#     "$APP_DIR"

# if [ $? -ne 0 ]; then
#     echo "ERROR: Failed to clone repository"
#     exit 1
# fi

# echo "✓ Repository cloned successfully to $APP_DIR"

# Change to application directory
# cd "$APP_DIR"

# ============================================================================
# Setup Environment Files
# ============================================================================
echo ""
echo "========================================"
echo "Setting up Environment Files"
echo "========================================"
echo "Using HOST_URL: $HOST_URL"

# Setup backend .env file
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env

    # Remove sensitive AWS credentials from .env (use IAM role on EC2)
    echo "Removing AWS credentials from .env (EC2 should use IAM role)..."
    sed -i '/^AWS_ACCESS_KEY_ID=/d' .env
    sed -i '/^AWS_SECRET_ACCESS_KEY=/d' .env

    # Replace HOST_URL placeholder with actual value
    echo "Setting CORS_ORIGINS to http://$HOST_URL:3000..."
    sed -i "s|\${HOST_URL}|$HOST_URL|g" .env

    echo "✓ Backend .env file created (AWS credentials removed for EC2 security)"
elif [ -f ".env" ]; then
    echo "✓ Backend .env file already exists"
    # Update HOST_URL in existing .env file
    echo "Updating HOST_URL in existing .env file..."
    sed -i "s|\${HOST_URL}|$HOST_URL|g" .env
else
    echo "WARNING: .env.example file not found"
fi

# Setup frontend .env.local file
cd web
if [ ! -f ".env.local" ] && [ -f ".env.local.example" ]; then
    echo "Creating web/.env.local from .env.local.example..."
    cp .env.local.example .env.local

    # Replace HOST_URL placeholder with actual value
    echo "Setting NEXT_PUBLIC_API_URL to http://$HOST_URL:8000..."
    sed -i "s|\${HOST_URL}|$HOST_URL|g" .env.local

    echo "✓ Frontend .env.local file created"
elif [ -f ".env.local" ]; then
    echo "✓ Frontend .env.local file already exists"
    # Update HOST_URL in existing .env.local file
    echo "Updating HOST_URL in existing .env.local file..."
    sed -i "s|\${HOST_URL}|$HOST_URL|g" .env.local
else
    echo "WARNING: web/.env.local.example file not found"
fi
cd ..

# ============================================================================
# Setup Virtual Environment with correct Python version
# ============================================================================
# Remove old venv if it exists (might be wrong Python version)
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment (to ensure correct Python version)..."
    rm -rf .venv
fi

echo ""
echo "========================================"
echo "Creating Python Virtual Environment"
echo "========================================"
$PYTHON_CMD -m venv .venv

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "✓ Virtual environment created with $PYTHON_CMD"

# Activate virtual environment
source .venv/bin/activate

# Verify Python version in venv
echo "Python version in virtual environment:"
python --version

echo ""
echo "========================================"
echo "Installing Python Dependencies"
echo "========================================"
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Python dependencies"
    exit 1
fi

echo "✓ Python dependencies installed"

echo ""
echo "========================================"
echo "Installing Node.js Dependencies"
echo "========================================"
cd web
npm ci

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Node.js dependencies"
    exit 1
fi

echo "✓ Node.js dependencies installed"
cd ..

echo ""
echo "========================================"
echo "Starting Services with PM2"
echo "========================================"
echo ""

# Set environment variables to disable uvloop before starting services
echo "Setting environment variables to disable uvloop..."
export UVLOOP_DISABLE=1
export PYTHONASYNCIODEBUG=1
echo "✓ uvloop disabled via environment variables"

# Stop any existing PM2 processes
echo "Stopping any existing services..."
pm2 stop all 2>/dev/null || true
pm2 delete all 2>/dev/null || true

# Update ecosystem.config.js with current APP_DIR and HOST_URL
APP_DIR=$(pwd)
echo "Generating PM2 ecosystem config with APP_DIR=$APP_DIR..."
cat > ecosystem.config.js << EOF
// PM2 Ecosystem Configuration - Auto-generated by startup.sh
// Ensures services auto-restart on EC2 reboot with proper environment

module.exports = {
  apps: [
    {
      name: 'mcp-server',
      script: '$APP_DIR/.venv/bin/python',
      args: '-m mcp.http_server',
      cwd: '$APP_DIR',
      env: {
        UVLOOP_DISABLE: '1',
        PYTHONASYNCIODEBUG: '1',
        USE_MCP_HTTP: 'true',
        HOST_URL: '$HOST_URL'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    },
    {
      name: 'backend',
      script: '$APP_DIR/.venv/bin/python',
      args: '-m mcp.main',
      cwd: '$APP_DIR',
      env: {
        UVLOOP_DISABLE: '1',
        PYTHONASYNCIODEBUG: '1',
        USE_MCP_HTTP: 'true',
        HOST_URL: '$HOST_URL'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    },
    {
      name: 'frontend',
      script: 'npm',
      args: 'run dev',
      cwd: '$APP_DIR/web',
      env: {
        HOST_URL: '$HOST_URL'
      },
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100
    }
  ]
};
EOF
echo "✓ ecosystem.config.js generated"

# Start services using ecosystem config
if [ "$USE_MCP_HTTP" = "true" ]; then
    echo "Starting all services (MCP + Backend + Frontend)..."
    pm2 start ecosystem.config.js
else
    echo "Starting Backend and Frontend only (MCP HTTP disabled)..."
    pm2 start ecosystem.config.js --only backend,frontend
fi
echo "✓ All services started"

# Save PM2 process list for resurrection on reboot
echo ""
echo "Saving PM2 process list for auto-restart on reboot..."
pm2 save

# Enable PM2 to start on boot (systemd service)
echo "Ensuring PM2 systemd service is enabled..."
sudo systemctl enable pm2-$(whoami) 2>/dev/null || true

# Wait for services to initialize
echo "Waiting for services to initialize..."
sleep 5

echo ""
echo "========================================"
echo "✅ All services started with PM2!"
echo "========================================"
echo ""
echo "🌐 Application URLs:"
echo "   Backend API: http://${HOST_URL}:8000"
echo "   Frontend UI: http://${HOST_URL}:3000"
if [ "$USE_MCP_HTTP" = "true" ]; then
    echo "   MCP Server: http://localhost:8001"
fi
echo ""
if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "" ]; then
    echo "📌 Using custom domain: $DOMAIN_NAME"
else
    echo "📌 Using EC2 Public IP: $HOST_URL"
    echo "   💡 Tip: Set domain_name in tfvars to use a custom domain"
fi
echo ""
echo "========================================"
echo "PM2 Process Status"
echo "========================================"
pm2 status

echo ""
echo "========================================"
echo "Useful PM2 Commands"
echo "========================================"
echo "  pm2 status          - Check process status"
echo "  pm2 logs            - View all logs"
echo "  pm2 logs backend    - View backend logs only"
echo "  pm2 logs frontend   - View frontend logs only"
echo "  pm2 logs mcp-server - View MCP server logs only"
echo "  pm2 restart all     - Restart all services"
echo "  pm2 stop all        - Stop all services"
echo "  pm2 delete all      - Remove all services"
echo ""
echo "🔄 AUTO-RESTART: Services will automatically restart on EC2 reboot!"
echo "   PM2 systemd service: pm2-$(whoami)"
echo "   Process list saved to: ~/.pm2/dump.pm2"
echo ""
