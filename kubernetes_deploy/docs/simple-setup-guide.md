# Simple Setup Guide - Direct EC2 Public IP

The simplest possible deployment for your AI Data Capture Portal using direct EC2 public IP addresses.

## 🎯 Why This Works

Since your EC2 instances are in a **public VPC with Internet Gateway**:
- ✅ **Direct internet access** - no NAT Gateway needed
- ✅ **Public IP addresses** - accessible from anywhere
- ✅ **Gateway API** handles TLS termination
- ✅ **No load balancer** overhead or complexity

## 🚀 Quick Deployment (3 Steps)

### Step 1: Configure Your Secrets
```bash
cd kubernetes_deploy/scripts

# Update email in cert-manager issuer
vim ../manifests/cert-manager-issuer.yaml
# Change: email: demolasobaki@gmail.com

# Encode your secrets
./encode-secrets.sh
```

### Step 2: Deploy Everything
```bash
./deploy-with-tls.sh
```

The script will:
- ✅ Install cert-manager automatically
- ✅ Deploy all your Kubernetes manifests  
- ✅ Detect your EC2 public IP
- ✅ Show you DNS configuration instructions

### Step 3: Configure DNS
Point your domain to your EC2 public IP:
```
Type: A
Name: apidatacapture.store
Value: <YOUR_EC2_PUBLIC_IP>

Type: A
Name: www.apidatacapture.store  
Value: <YOUR_EC2_PUBLIC_IP>
```

## 🔧 What Happens Behind the Scenes

### Network Flow
```
Internet → EC2 Public IP → Gateway (NodePort) → Service → Pods
    ↓
  Your Domain → apidatacapture.store
    ↓
  TLS Cert (Let's Encrypt) → HTTPS
```

### Port Configuration
- **HTTP**: Port 80 → NodePort (auto-assigned ~30000-32767)
- **HTTPS**: Port 443 → NodePort (auto-assigned ~30000-32767)
- **Gateway API** handles the port mapping automatically

## 🛡️ Security Requirements

### EC2 Security Group
Ensure your EC2 security group allows:
```
Type: HTTP
Port: 80
Source: 0.0.0.0/0

Type: HTTPS
Port: 443  
Source: 0.0.0.0/0

Type: Custom TCP
Port: 30000-32767  # NodePort range
Source: 0.0.0.0/0
```

### TLS Certificates
- ✅ **Automatic issuance** via Let's Encrypt
- ✅ **HTTP-01 challenge** through Gateway API
- ✅ **Auto-renewal** every 60 days
- ✅ **TLS termination** at Gateway level

## 🔍 Verification Commands

### Check Your Public IP
```bash
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

### Check Gateway Status
```bash
kubectl get gateway ai-data-capture-gateway -n ai-data-capture
kubectl get svc -n ai-data-capture
```

### Check Certificate Status
```bash
kubectl get certificate -n ai-data-capture
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture
```

### Test Your Application
```bash
# After DNS propagation
curl -I https://apidatacapture.store
```

## 🚨 Common Issues

### Certificate Not Issued
**Cause**: DNS not propagated to your EC2 IP
**Solution**: 
- Verify DNS: `nslookup apidatacapture.store`
- Wait for propagation (up to 48 hours)
- Check cert-manager logs: `kubectl logs -n cert-manager deployment/cert-manager`

### Gateway Not Accessible
**Cause**: Security group blocking traffic
**Solution**:
- Check EC2 security group allows ports 80/443
- Ensure NodePort range (30000-32767) is open
- Verify EC2 instance has public IP assigned

### Pods Not Starting
**Cause**: Secrets not configured
**Solution**:
- Run `./encode-secrets.sh` to configure secrets
- Check secret exists: `kubectl get secret -n ai-data-capture`

## 📊 Monitoring

### Check Application Health
```bash
# Pod status
kubectl get pods -n ai-data-capture

# Application logs
kubectl logs -n ai-data-capture deployment/ai-data-capture-api

# Gateway logs
kubectl logs -n kube-system -l app.kubernetes.io/name=cilium
```

### DNS Resolution
```bash
# Check if domain resolves to your IP
nslookup apidatacapture.store

# Test HTTP/HTTPS
curl -I http://apidatacapture.store
curl -I https://apidatacapture.store
```

## 🎯 Production Considerations

### Scaling
- **Single instance**: Direct IP approach works perfectly
- **Multiple instances**: Consider adding a load balancer later
- **High availability**: Use multiple AZs with ALB

### Backup
- **Database backups**: Regular automated backups
- **Configuration**: Keep manifests in version control
- **Certificates**: Automatic backup via cert-manager

### Monitoring
- **Application metrics**: Built into FastAPI
- **Infrastructure**: CloudWatch for EC2 metrics
- **Uptime**: External monitoring service

## 🎉 Success Indicators

When everything works:
1. ✅ **Pods running**: `kubectl get pods -n ai-data-capture`
2. ✅ **Certificate issued**: `kubectl get certificate -n ai-data-capture`
3. ✅ **DNS resolves**: `nslookup apidatacapture.store`
4. ✅ **HTTPS works**: `curl -I https://apidatacapture.store`
5. ✅ **Application responds**: Test your API endpoints

## 💡 Why This Approach is Great

- **🚀 Simple**: No complex load balancer setup
- **💰 Cost-effective**: No additional AWS charges
- **🔒 Secure**: TLS termination and automatic certificates
- **⚡ Fast**: Direct connection to your instance
- **🛠️ Easy to debug**: Fewer moving parts

Perfect for development, testing, and small production workloads! 🎯
