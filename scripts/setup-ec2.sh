#!/bin/bash
set -e

# EC2 Instance Setup Script for AI Data Capture API
# Run this script on a fresh EC2 instance to prepare it for deployments

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up EC2 instance for AI Data Capture API${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${YELLOW}Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
    echo -e "${GREEN}Docker installed${NC}"
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed${NC}"
else
    echo -e "${GREEN}Docker Compose already installed${NC}"
fi

# Install additional tools
echo -e "${YELLOW}Installing additional tools...${NC}"
sudo apt-get install -y \
    curl \
    wget \
    git \
    htop \
    vim \
    jq \
    unzip

# Create application directory
APP_DIR="/opt/ai-data-capture-api"
echo -e "${YELLOW}Creating application directory: ${APP_DIR}${NC}"
sudo mkdir -p ${APP_DIR}
sudo chown ubuntu:ubuntu ${APP_DIR}

# Create .env file template
echo -e "${YELLOW}Creating .env template...${NC}"
cat > ${APP_DIR}/.env.template << 'EOF'
# Database Configuration
database_hostname=your-db-host
database_port=5432
database_password=your-db-password
database_name=your-db-name
database_username=your-db-user

# JWT Configuration
secret_key=your-secret-key-here
algorithm=HS256
access_token_expire_minutes=30

# AWS Configuration
AWS_ACCESS_KEY=your-aws-access-key
AWS_SECRET_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name

# API Keys
GOOGLE_API_KEY=your-google-api-key
OPENAI_API_KEY=your-openai-api-key
AI_MODEL_PROVIDER=openai

# Email Configuration
DEFAULT_FROM_EMAIL=your-email@domain.com
EMAIL_PROVIDER=aws_ses

# SMS Configuration (Termii)
TERMII_API_KEY=your-termii-api-key
TERMII_SECRET_KEY=your-termii-secret-key
TERMII_SENDER_ID=your-sender-id
SMS_PROVIDER=termii

# WhatsApp Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
WHATSAPP_PROVIDER=twilio

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=info
EOF

echo -e "${YELLOW}Please copy .env.template to .env and fill in your values:${NC}"
echo "  sudo nano ${APP_DIR}/.env"

# Configure Docker daemon for better performance
echo -e "${YELLOW}Configuring Docker daemon...${NC}"
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
EOF

# Restart Docker
sudo systemctl restart docker
sudo systemctl enable docker

# Setup log rotation
echo -e "${YELLOW}Setting up log rotation...${NC}"
sudo tee /etc/logrotate.d/ai-data-capture-api > /dev/null <<EOF
${APP_DIR}/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
}
EOF

# Create systemd service for auto-start (optional)
echo -e "${YELLOW}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/ai-data-capture-api.service > /dev/null <<EOF
[Unit]
Description=AI Data Capture API Container
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker start ai-data-capture-api-app
ExecStop=/usr/bin/docker stop ai-data-capture-api-app
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Setup CloudWatch agent (optional)
# echo -e "${YELLOW}CloudWatch agent can be installed for monitoring${NC}"
# echo "Run: wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"

# Display versions
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Installed versions:"
docker --version
docker-compose --version
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure .env file: sudo nano ${APP_DIR}/.env"
echo "2. Tag this instance with:"
echo "   - Environment: production"
echo "   - Application: ai-data-capture-api"
echo "3. Ensure security group allows:"
echo "   - Port 22 (SSH) from GitHub Actions runner"
echo "   - Port 8000 (API) from load balancer/users"
echo "4. Deploy using GitHub Actions workflow"
echo ""
echo -e "${GREEN}Setup completed successfully!${NC}"
