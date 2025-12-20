#!/bin/bash
set -e

# Nginx setup script for AI Data Capture API
# This allows using apidatacapture.store without :8000

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="api.ymrcounselling.com"

echo -e "${GREEN}Setting up Nginx reverse proxy for ${DOMAIN}${NC}"

# Install Nginx
echo -e "${YELLOW}Installing Nginx...${NC}"
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration
echo -e "${YELLOW}Creating Nginx configuration...${NC}"
sudo tee /etc/nginx/sites-available/ai-data-capture-api > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Increase client body size for file uploads
    client_max_body_size 50M;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (optional: bypass proxy for faster checks)
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# Enable the site
echo -e "${YELLOW}Enabling site...${NC}"
sudo ln -sf /etc/nginx/sites-available/ai-data-capture-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo -e "${YELLOW}Testing Nginx configuration...${NC}"
sudo nginx -t

# Restart Nginx
echo -e "${YELLOW}Restarting Nginx...${NC}"
sudo systemctl restart nginx
sudo systemctl enable nginx

echo -e "${GREEN}Nginx setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Ensure your DNS A record points to this server's IP"
echo "2. Wait for DNS propagation (5-30 minutes)"
echo "3. Test: curl http://${DOMAIN}/health"
echo "4. Setup SSL certificate:"
echo "   sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo ""
echo -e "${GREEN}After SSL setup, your API will be available at:${NC}"
echo "  https://${DOMAIN}/login"
echo "  https://${DOMAIN}/counsellors"
echo "  etc."
