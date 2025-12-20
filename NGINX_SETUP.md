# Nginx Reverse Proxy Setup

## Why You Need This

Without Nginx, you'd have to use:
- ❌ `apidatacapture.live:8000/login` (ugly, exposes port)

With Nginx, you can use:
- ✅ `https://apidatacapture.live/login` (clean, professional)

## How It Works

```
User Request
    ↓
https://apidatacapture.live/login (Port 443)
    ↓
Nginx (Reverse Proxy)
    ↓
FastAPI App (Port 8000)
    ↓
Response back through Nginx
    ↓
User receives response
```

## Setup Steps

### 1. Run Nginx Setup Script

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Download and run Nginx setup
curl -fsSL https://raw.githubusercontent.com/demola07/ai-data-capture-portal-api/main/scripts/setup-nginx.sh -o setup-nginx.sh
chmod +x setup-nginx.sh
./setup-nginx.sh
```

This installs:
- Nginx web server
- Certbot (for SSL certificates)
- Reverse proxy configuration

### 2. Configure DNS

**On Namecheap:**
1. Go to Domain List → Manage → Advanced DNS
2. Add **A Record**:
   ```
   Type: A Record
   Host: @ (for root domain)
   Value: YOUR_EC2_ELASTIC_IP
   TTL: Automatic
   ```
3. Add **A Record** for www:
   ```
   Type: A Record
   Host: www
   Value: YOUR_EC2_ELASTIC_IP
   TTL: Automatic
   ```

### 3. Wait for DNS Propagation

```bash
# Check DNS (wait until it shows your EC2 IP)
dig apidatacapture.live
dig www.apidatacapture.live

# Should show:
# apidatacapture.live. 300 IN A YOUR_EC2_IP
```

Usually takes 5-30 minutes.

### 4. Setup SSL Certificate (HTTPS)

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Get free SSL certificate from Let's Encrypt
sudo certbot --nginx -d apidatacapture.live -d www.apidatacapture.live

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose: Redirect HTTP to HTTPS (option 2)
```

Certbot will:
- Get SSL certificate
- Configure Nginx for HTTPS
- Auto-renew certificate every 90 days

### 5. Update Security Group

**Remove port 8000, add standard ports:**

```
Inbound Rules:
  - Port 22 (SSH): From your IP
  - Port 80 (HTTP): From 0.0.0.0/0
  - Port 443 (HTTPS): From 0.0.0.0/0
```

**Via AWS Console:**
1. EC2 → Security Groups → Select your SG
2. Inbound rules → Edit inbound rules
3. Remove: Port 8000
4. Add: Port 80 (HTTP) from 0.0.0.0/0
5. Add: Port 443 (HTTPS) from 0.0.0.0/0

**Via AWS CLI:**
```bash
# Get security group ID
SG_ID=$(aws ec2 describe-instances \
  --instance-ids i-YOUR-INSTANCE-ID \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Remove port 8000
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

# Add port 80
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Add port 443
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

## Testing

### Test HTTP (before SSL)
```bash
curl http://apidatacapture.live/health
curl http://apidatacapture.live/
```

### Test HTTPS (after SSL)
```bash
curl https://apidatacapture.live/health
curl https://apidatacapture.live/
```

### Test from Browser
```
https://apidatacapture.live/docs
```

Should show your FastAPI Swagger documentation.

## Frontend Configuration

Update your frontend `.env`:

```env
# Before (with port)
VITE_API_URL=http://apidatacapture.live:8000

# After (clean URL)
VITE_API_URL=https://apidatacapture.live
```

Now your frontend can make requests like:
```javascript
fetch('https://apidatacapture.live/login', {
  method: 'POST',
  // ...
})
```

## Nginx Configuration Details

The Nginx config (`/etc/nginx/sites-available/ai-data-capture-api`) does:

1. **Listens on port 80/443** (standard HTTP/HTTPS)
2. **Proxies to localhost:8000** (your FastAPI app)
3. **Adds security headers**
4. **Handles file uploads** (up to 50MB)
5. **Preserves client IP** (for logging)
6. **Sets proper timeouts**

## Troubleshooting

### Nginx won't start
```bash
# Check configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log

# Restart
sudo systemctl restart nginx
```

### 502 Bad Gateway
```bash
# Check if FastAPI app is running
docker ps | grep ai-data-capture

# Check app logs
docker logs ai-data-capture-api-app

# Restart app
docker restart ai-data-capture-api-app
```

### SSL certificate fails
```bash
# Ensure DNS is pointing to your server
dig apidatacapture.live

# Ensure port 80 is open
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443

# Try again
sudo certbot --nginx -d apidatacapture.live -d www.apidatacapture.live
```

### Certificate renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal

# Auto-renewal is enabled by default via cron
```

## Performance Optimization

### Enable Gzip Compression

Add to Nginx config:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### Enable Caching

Add to Nginx config:
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Rate Limiting

Add to Nginx config:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    # ... rest of config
}
```

## Monitoring

### Check Nginx Status
```bash
sudo systemctl status nginx
```

### View Access Logs
```bash
sudo tail -f /var/log/nginx/access.log
```

### View Error Logs
```bash
sudo tail -f /var/log/nginx/error.log
```

### Monitor Connections
```bash
# Active connections
sudo netstat -an | grep :80 | wc -l
sudo netstat -an | grep :443 | wc -l
```

## Security Best Practices

### 1. Hide Nginx Version
Add to `/etc/nginx/nginx.conf`:
```nginx
http {
    server_tokens off;
    # ...
}
```

### 2. Add Security Headers
Already included in setup script:
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

### 3. Enable HTTP/2
Automatically enabled by Certbot when using HTTPS.

### 4. Setup Firewall
```bash
# Enable UFW
sudo ufw enable

# Allow necessary ports
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443

# Check status
sudo ufw status
```

## Complete URL Structure

After setup, your API endpoints will be:

```
Authentication:
  https://apidatacapture.live/login
  https://apidatacapture.live/register

Counsellors:
  https://apidatacapture.live/counsellors
  https://apidatacapture.live/counsellors/{id}
  https://apidatacapture.live/counsellors/me

Health Check:
  https://apidatacapture.live/health

API Docs:
  https://apidatacapture.live/docs
  https://apidatacapture.live/redoc
```

Clean, professional URLs with no port numbers! 🎉
