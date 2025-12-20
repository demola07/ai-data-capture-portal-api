# AWS EC2 Deployment Guide

## Overview

Fast, seamless containerized deployment to AWS EC2 with zero-downtime updates, automatic rollback, and health checks.

## Architecture

```
GitHub Actions → Build Docker Image → Push to GHCR → Deploy to EC2 → Health Check
                                                           ↓
                                                    Zero-Downtime Swap
```

## Prerequisites

### 1. AWS Setup

**EC2 Instance Requirements:**
- Ubuntu 22.04 LTS
- Minimum: t3.medium (2 vCPU, 4GB RAM)
- Docker installed
- Security group configured

**Required AWS Resources:**
- EC2 instance(s) tagged with:
  - `Environment: production`
  - `Application: ai-data-capture-api`
- IAM user with EC2 describe permissions
- SSH key pair for deployment

### 2. GitHub Secrets

Add these secrets to your GitHub repository:

```
AWS_ACCESS_KEY_ID          # AWS credentials for EC2 API access
AWS_SECRET_ACCESS_KEY      # AWS secret key
EC2_SSH_PRIVATE_KEY        # SSH private key for EC2 access
```

## Initial EC2 Setup

### Step 1: Launch EC2 Instance

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Run setup script
curl -fsSL https://raw.githubusercontent.com/demola07/ai-data-capture-portal-api/main/scripts/setup-ec2.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```

### Step 2: Configure Environment

```bash
# Edit environment file
sudo nano /opt/ai-data-capture-api/.env

# Add your configuration:
database_hostname=your-db-host
database_password=your-secure-password
secret_key=your-jwt-secret
# ... etc
```

### Step 3: Tag EC2 Instance

```bash
# Via AWS CLI
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags Key=Environment,Value=production \
         Key=Application,Value=ai-data-capture-api
```

Or via AWS Console:
1. Go to EC2 → Instances
2. Select your instance
3. Tags → Manage tags
4. Add tags as shown above

### Step 4: Configure Security Group

Allow these inbound rules:
- **Port 22**: SSH from GitHub Actions runner IP (or your VPN)
- **Port 8000**: HTTP from load balancer/users
- **Port 443**: HTTPS (if using SSL termination on EC2)

## Deployment Workflow

### Automatic Deployment

Push to `main` branch triggers automatic deployment:

```bash
git add .
git commit -m "feat: add new feature"
git push origin main
```

**Workflow steps:**
1. ✅ Build Docker image
2. ✅ Push to GitHub Container Registry
3. ✅ SSH to EC2 instances
4. ✅ Pull new image
5. ✅ Zero-downtime container swap
6. ✅ Health check verification
7. ✅ Automatic rollback on failure

### Manual Deployment

Trigger via GitHub Actions UI:
1. Go to Actions → Deploy to AWS EC2
2. Click "Run workflow"
3. Select branch
4. Click "Run workflow"

## Zero-Downtime Deployment Process

The deployment script performs these steps:

1. **Pull new image** from GHCR
2. **Start new container** on temporary port (8001)
3. **Wait for health check** (up to 60 seconds)
4. **Backup old container** with timestamp
5. **Stop old container**
6. **Rename new container** to production name
7. **Restart on production port** (8000)
8. **Verify final health**
9. **Remove backup** on success

**Downtime:** ~2-5 seconds during port swap

## Monitoring & Health Checks

### Container Health

```bash
# Check container status
docker ps -f name=ai-data-capture-api-app

# View health status
docker inspect ai-data-capture-api-app --format='{{.State.Health.Status}}'

# View logs
docker logs ai-data-capture-api-app --tail 100 -f
```

### Application Health

```bash
# Health endpoint
curl http://localhost:8000/health

# API root
curl http://localhost:8000/
```

### Resource Usage

```bash
# Container stats
docker stats ai-data-capture-api-app

# System resources
htop
```

## Rollback

### Automatic Rollback

If health checks fail, deployment automatically rolls back to previous version.

### Manual Rollback

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# List available images
docker images ghcr.io/demola07/ai-data-capture-portal-api

# Rollback to specific version
sudo /opt/ai-data-capture-api/rollback.sh main-abc1234
```

## Troubleshooting

### Deployment Fails

**Check GitHub Actions logs:**
1. Go to Actions → Latest workflow run
2. Expand failed step
3. Review error messages

**Common issues:**
- SSH key incorrect → Update `EC2_SSH_PRIVATE_KEY` secret
- EC2 not tagged → Add required tags
- Security group blocks SSH → Allow port 22
- Disk space full → Clean old images: `docker system prune -a`

### Container Won't Start

```bash
# View container logs
docker logs ai-data-capture-api-app --tail 200

# Check environment file
cat /opt/ai-data-capture-api/.env

# Verify image
docker images | grep ai-data-capture

# Test manually
docker run --rm -it \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health Check Fails

```bash
# Check if service is responding
curl -v http://localhost:8000/health

# Check database connectivity
docker exec ai-data-capture-api-app \
  python -c "from app.database import engine; engine.connect()"

# Review application logs
docker logs ai-data-capture-api-app | grep -i error
```

### Performance Issues

```bash
# Check resource limits
docker inspect ai-data-capture-api-app | jq '.[0].HostConfig.Memory'

# Increase workers (edit docker run command in deploy.sh)
# Change: --workers 2  to  --workers 4

# Monitor database connections
# Check slow queries in PostgreSQL
```

## Optimization Tips

### 1. Use Optimized Dockerfile

```bash
# In your repository, rename Dockerfile
mv Dockerfile Dockerfile.original
mv Dockerfile.optimized Dockerfile

# Commit and push
git add Dockerfile
git commit -m "chore: use optimized Dockerfile"
git push
```

**Benefits:**
- Faster builds with better caching
- Smaller image size
- Better performance with uvloop
- Proper signal handling with tini

### 2. Enable Build Cache

Already enabled in workflow via:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**Result:** Subsequent builds ~3-5x faster

### 3. Multi-Instance Deployment

For high availability, deploy to multiple EC2 instances:

1. Launch additional EC2 instances
2. Tag them with same tags
3. Workflow automatically deploys to all instances
4. Use load balancer to distribute traffic

### 4. Database Connection Pooling

Ensure your `.env` has:
```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

## Security Best Practices

### 1. Secrets Management

**Never commit secrets to Git**

Use AWS Secrets Manager:
```bash
# Store secret
aws secretsmanager create-secret \
  --name ai-data-capture/database-password \
  --secret-string "your-password"

# Retrieve in deployment
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id ai-data-capture/database-password \
  --query SecretString --output text)
```

### 2. SSH Key Rotation

Rotate SSH keys regularly:
```bash
# Generate new key
ssh-keygen -t ed25519 -C "github-actions-deploy"

# Add to EC2 authorized_keys
cat new-key.pub >> ~/.ssh/authorized_keys

# Update GitHub secret
# EC2_SSH_PRIVATE_KEY = contents of new-key
```

### 3. Image Scanning

Trivy scans are automatic in workflow. Review results:
1. Go to Security → Code scanning alerts
2. Review and fix vulnerabilities
3. Rebuild and redeploy

### 4. Network Security

- Use VPC with private subnets
- EC2 in private subnet, ALB in public
- Database in private subnet
- Use security groups, not NACLs

## Scaling

### Horizontal Scaling

```bash
# Launch more EC2 instances
# Tag them appropriately
# Workflow deploys to all automatically

# Add Application Load Balancer
aws elbv2 create-load-balancer \
  --name ai-data-capture-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx
```

### Vertical Scaling

```bash
# Stop instance
aws ec2 stop-instances --instance-ids i-xxx

# Change instance type
aws ec2 modify-instance-attribute \
  --instance-id i-xxx \
  --instance-type t3.large

# Start instance
aws ec2 start-instances --instance-ids i-xxx
```

## Cost Optimization

### 1. Use Spot Instances

For non-critical environments:
```bash
# Request spot instance
aws ec2 request-spot-instances \
  --spot-price "0.05" \
  --instance-count 1 \
  --launch-specification file://spec.json
```

### 2. Auto-Scaling

Create Auto Scaling Group:
- Min: 1 instance
- Desired: 2 instances
- Max: 4 instances
- Scale on CPU > 70%

### 3. Reserved Instances

For production, buy 1-year reserved instances:
- Save up to 40% vs on-demand
- Commit to instance type and region

## Monitoring & Alerts

### CloudWatch Integration

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure metrics
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### Set Up Alarms

```bash
# CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Backup & Disaster Recovery

### 1. Database Backups

Automated daily backups via RDS or:
```bash
# Manual backup
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup.sql

# Upload to S3
aws s3 cp backup.sql s3://your-backup-bucket/$(date +%Y%m%d).sql
```

### 2. EC2 Snapshots

```bash
# Create AMI
aws ec2 create-image \
  --instance-id i-xxx \
  --name "ai-data-capture-backup-$(date +%Y%m%d)" \
  --description "Automated backup"
```

### 3. Disaster Recovery Plan

1. Keep AMIs in multiple regions
2. Document recovery procedures
3. Test recovery quarterly
4. RTO: 15 minutes
5. RPO: 1 hour

## Performance Benchmarks

Expected performance on t3.medium:
- **Requests/sec**: 500-1000
- **Response time**: <100ms (p95)
- **Memory usage**: 300-500MB
- **CPU usage**: 20-40% (normal load)

## Support & Maintenance

### Regular Maintenance

**Weekly:**
- Review logs for errors
- Check disk space
- Monitor performance metrics

**Monthly:**
- Update dependencies
- Review security alerts
- Optimize database queries
- Clean old Docker images

**Quarterly:**
- Security audit
- Disaster recovery test
- Performance review
- Cost optimization review

## Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Settings](https://www.uvicorn.org/settings/)
