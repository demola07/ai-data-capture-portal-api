# Deployment Flow and DNS Timing

## 🚀 Complete Deployment Process

### Step-by-Step Flow

1. **Run the deployment script**:
   ```bash
   cd kubernetes_deploy/scripts
   ./deploy-with-tls.sh
   ```

2. **Script automatically**:
   - Installs cert-manager (if needed)
   - Deploys all Kubernetes manifests
   - Creates the Gateway and requests external IP
   - Shows you the Gateway IP address

3. **You configure DNS** with the provided IP

4. **Certificate issued automatically** once DNS propagates

## 🌐 DNS Configuration Timing

### When DNS Configuration Happens
- **AFTER** the Gateway is deployed and gets an IP
- **DURING** script execution (script will pause and wait for you)
- **BEFORE** certificate can be issued

### DNS Records to Add
```
Type: A
Name: apidatacapture.store
Value: <GATEWAY_IP_FROM_SCRIPT>
TTL: 300

Type: A  
Name: www.apidatacapture.store
Value: <GATEWAY_IP_FROM_SCRIPT>
TTL: 300
```

## ⏱️ Timeline Expectations

| Event | Time | Notes |
|-------|------|-------|
| Gateway deployment | 1-2 minutes | Kubernetes creates resources |
| External IP assignment | 2-5 minutes | Cloud provider assigns IP |
| DNS configuration | Manual step | You add records in domain manager |
| DNS propagation | 5 minutes - 48 hours | Varies by provider and TTL |
| Certificate issuance | 1-2 minutes after DNS | Let's Encrypt validates domain |

## 🔄 What Happens Automatically

### cert-manager Will:
- ✅ Monitor the Certificate resource
- ✅ Create ACME challenge when DNS resolves
- ✅ Request certificate from Let's Encrypt
- ✅ Store certificate in Kubernetes secret
- ✅ Renew certificate before expiry (75 days)

### Gateway Will:
- ✅ Use the certificate automatically
- ✅ Terminate TLS traffic
- ✅ Route traffic to your application

## 🛠️ Manual Steps Required

### You Need To:
1. **Run the deployment script** - `./deploy-with-tls.sh`
2. **Configure DNS records** when prompted by script
3. **Wait for DNS propagation** (patience required!)

### You DON'T Need To:
- ❌ Install cert-manager manually
- ❌ Create certificates manually  
- ❌ Renew certificates manually
- ❌ Configure TLS in your application

## 🔍 Monitoring Commands

### Check Gateway Status
```bash
kubectl get gateway ai-data-capture-gateway -n ai-data-capture
```

### Check Certificate Status
```bash
kubectl get certificate apidatacapture-store-tls -n ai-data-capture
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture
```

### Check DNS Resolution
```bash
nslookup apidatacapture.store
dig apidatacapture.store
```

### Test HTTPS
```bash
curl -I https://apidatacapture.store
```

## 🚨 Common Issues

### Certificate Pending
**Cause**: DNS not propagated yet
**Solution**: Wait for DNS propagation, certificate will issue automatically

### Gateway No External IP
**Cause**: LoadBalancer service issue
**Solution**: Check cloud provider LoadBalancer configuration

### DNS Not Resolving
**Cause**: DNS records not configured or propagation delay
**Solution**: Verify DNS records in domain manager, wait for propagation

## 📞 Support Commands

### Get All Resources
```bash
kubectl get all -n ai-data-capture
```

### Check cert-manager Logs
```bash
kubectl logs -n cert-manager deployment/cert-manager -f
```

### Check Challenge Status
```bash
kubectl get challenge -n ai-data-capture
kubectl describe challenge -n ai-data-capture
```

This flow ensures a smooth deployment with automatic TLS certificate management! 🔐
