# LoadBalancer Quick Start - Production Deployment

Fast-track guide for deploying with AWS LoadBalancer for high availability and security.

## 🎯 What Changed

Your manifests have been updated to use **AWS LoadBalancer** instead of NodePort:

### ✅ Updated Files
- **`gateway.yaml`** - Now uses LoadBalancer service type
- **`service.yaml`** - NodePort service commented out (security)

### 🔒 Security Improvements
- ❌ No NodePort exposure (30000-32767 range)
- ✅ Single LoadBalancer entry point
- ✅ AWS-managed security groups
- ✅ Automatic DDoS protection (AWS Shield)

### 🚀 High Availability Benefits
- ✅ Automatic failover across nodes
- ✅ Health checks every 10 seconds
- ✅ Multi-AZ distribution
- ✅ Zero-downtime updates

---

## ⚡ Quick Deployment

### Prerequisites

1. **AWS Cloud Provider** configured in your cluster
2. **IAM permissions** for LoadBalancer creation
3. **VPC with public subnets** and Internet Gateway
4. **kubectl, helm, aws CLI** installed

### One-Command Deployment

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/scripts
./deploy-with-loadbalancer.sh
```

This script will:
1. Install Gateway API CRDs
2. Configure Cilium for Gateway API
3. Install cert-manager
4. Verify AWS/VPC configuration
5. Deploy application with LoadBalancer
6. Provide DNS configuration instructions

**Estimated time:** 10-15 minutes

---

## 📋 Manual Deployment Steps

If you prefer manual control:

### Step 1: Verify Prerequisites (2 min)

```bash
# Check AWS cloud provider
kubectl get nodes -o jsonpath='{.items[*].spec.providerID}'
# Should show: aws:///us-east-1a/i-xxxxx

# Check AWS credentials
aws sts get-caller-identity

# Check VPC has Internet Gateway
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=<your-vpc-id>"
```

### Step 2: Install Gateway API Components (5 min)

```bash
# Install Gateway API CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Enable Gateway API in Cilium
kubectl -n kube-system patch configmap cilium-config --type merge -p '{"data":{"enable-gateway-api":"true"}}'
kubectl -n kube-system rollout restart deployment/cilium-operator
kubectl -n kube-system rollout restart daemonset/cilium

# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update
kubectl create namespace cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.0 \
  --set installCRDs=true
```

### Step 3: Deploy Application (2 min)

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Deploy with LoadBalancer
kubectl apply -k .

# Wait for deployment
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

### Step 4: Get LoadBalancer DNS (2-5 min)

Wait for AWS to provision the LoadBalancer:

```bash
# Watch LoadBalancer creation
kubectl -n ai-data-capture get svc -w

# Get LoadBalancer hostname
LB_HOSTNAME=$(kubectl -n ai-data-capture get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')

echo "LoadBalancer: $LB_HOSTNAME"
```

### Step 5: Configure DNS (5-60 min)

#### Option A: AWS Route53 (Recommended)

```bash
# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='apidatacapture.store.'].Id" --output text | cut -d'/' -f3)

# Create ALIAS record
aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "apidatacapture.store",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z215JYRZR1TBD5",
        "DNSName": "'$LB_HOSTNAME'",
        "EvaluateTargetHealth": false
      }
    }
  }]
}'
```

#### Option B: Other DNS Providers

Create CNAME or A record:
```
Type: CNAME (or A with resolved IP)
Name: apidatacapture.store
Value: <LB_HOSTNAME>
TTL: 300
```

### Step 6: Verify (2-5 min)

```bash
# Check DNS propagation
dig apidatacapture.store +short

# Check certificate issuance
kubectl -n ai-data-capture get certificate -w

# Test HTTPS
curl -I https://apidatacapture.store
```

---

## 🔍 Verification Checklist

After deployment:

### ✅ Infrastructure
- [ ] Gateway API CRDs installed
- [ ] Cilium Gateway Controller running
- [ ] cert-manager pods running
- [ ] AWS cloud provider configured

### ✅ LoadBalancer
- [ ] LoadBalancer service created
- [ ] LoadBalancer has external hostname
- [ ] LoadBalancer is Active in AWS Console
- [ ] Target groups show healthy targets

### ✅ Application
- [ ] Pods running (3 replicas)
- [ ] Gateway status: Programmed=True
- [ ] HTTPRoute created
- [ ] Service endpoints available

### ✅ DNS & TLS
- [ ] DNS points to LoadBalancer
- [ ] DNS propagated globally
- [ ] Certificate issued (Ready=True)
- [ ] TLS secret created

### ✅ Access
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS accessible
- [ ] API endpoints responding
- [ ] Health check passing

---

## 💰 Cost Breakdown

### AWS Network Load Balancer
```
Monthly Costs:
- Base charge: ~$16.20/month ($0.0225/hour)
- LCU charge: ~$4-13/month (typical usage)
- Total: ~$20-30/month

What You Get:
✅ High availability
✅ Automatic failover
✅ Health checks
✅ DDoS protection (AWS Shield)
✅ Managed service (no maintenance)
✅ Multi-AZ distribution
```

**ROI:** The cost is minimal compared to:
- Security risks of NodePort
- Cost of downtime
- Engineer time for manual HA setup

---

## 🔒 Security Configuration

### LoadBalancer Security Group

AWS automatically creates a security group for the LoadBalancer:

```
Inbound Rules:
- 0.0.0.0/0 → Port 80 (HTTP)
- 0.0.0.0/0 → Port 443 (HTTPS)

Outbound Rules:
- All traffic
```

### Node Security Group

Update your node security group to **only** allow traffic from LoadBalancer:

```bash
# Remove this rule (if exists):
# 0.0.0.0/0 → 30000-32767  ❌ INSECURE!

# Add this rule:
# <LB-SECURITY-GROUP> → 30000-32767  ✅ SECURE!
```

**Important:** Nodes should NOT be directly accessible from internet.

---

## 🐛 Troubleshooting

### Issue: LoadBalancer Stuck in Pending

**Check cloud provider:**
```bash
kubectl get nodes -o jsonpath='{.items[*].spec.providerID}'
```

**Check events:**
```bash
kubectl -n ai-data-capture describe svc
```

**Common causes:**
- AWS cloud provider not configured
- IAM permissions missing
- No public subnets available
- Subnet tags missing: `kubernetes.io/role/elb=1`

### Issue: Unhealthy Targets

**Check pod health:**
```bash
kubectl -n ai-data-capture get pods
kubectl -n ai-data-capture logs -l app=ai-data-capture-api
```

**Check in AWS Console:**
- EC2 → Load Balancers → Your LB
- Target Groups → Check health status
- Verify health check path and port

### Issue: Certificate Not Issuing

**Verify DNS:**
```bash
dig apidatacapture.store +short
# Should resolve to LoadBalancer hostname or IP
```

**Check cert-manager:**
```bash
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
kubectl -n cert-manager logs -l app=cert-manager --tail=50
```

**Common causes:**
- DNS not pointing to LoadBalancer
- Port 80 not accessible
- LoadBalancer not forwarding to Gateway

---

## 📊 Monitoring

### Check LoadBalancer Status

```bash
# Service status
kubectl -n ai-data-capture get svc

# Gateway status
kubectl -n ai-data-capture get gateway

# Pod status
kubectl -n ai-data-capture get pods
```

### AWS Console Monitoring

**Load Balancers:**
- EC2 → Load Balancers → Your NLB
- Check: State, DNS name, Availability Zones

**Target Groups:**
- EC2 → Target Groups
- Check: Healthy/Unhealthy targets, Health checks

**CloudWatch Metrics:**
- ActiveFlowCount
- HealthyHostCount
- UnHealthyHostCount
- ProcessedBytes

### Set Up Alarms

```bash
# Example: Alert on unhealthy targets
aws cloudwatch put-metric-alarm \
  --alarm-name ai-data-capture-unhealthy-targets \
  --alarm-description "Alert when targets are unhealthy" \
  --metric-name UnHealthyHostCount \
  --namespace AWS/NetworkELB \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

---

## 🔄 Rollback to NodePort

If you need to rollback (not recommended for production):

```bash
# Edit gateway.yaml
kubectl -n ai-data-capture annotate gateway ai-data-capture-gateway \
  io.cilium/service-type=NodePort --overwrite

# Uncomment NodePort service in service.yaml
# Then apply
kubectl apply -k manifests/

# Update DNS to point to node IPs
```

---

## 📚 Additional Resources

- **Detailed Guide:** [LOADBALANCER_SETUP.md](./LOADBALANCER_SETUP.md)
- **Comparison:** [NODEPORT_VS_LOADBALANCER.md](./NODEPORT_VS_LOADBALANCER.md)
- **General Setup:** [GATEWAY_TLS_SETUP.md](./GATEWAY_TLS_SETUP.md)

---

## 🎯 Next Steps

After successful deployment:

1. **Monitor LoadBalancer**
   - Set up CloudWatch alarms
   - Monitor costs in AWS Cost Explorer

2. **Optimize Configuration**
   - Enable cross-zone load balancing
   - Configure access logs
   - Tune health check parameters

3. **Security Hardening**
   - Review security groups
   - Enable AWS WAF (optional)
   - Configure rate limiting

4. **Backup and DR**
   - Document LoadBalancer configuration
   - Test failover scenarios
   - Plan for disaster recovery

5. **CI/CD Integration**
   - Automate deployments
   - Implement blue-green deployments
   - Set up monitoring and alerting

---

## 🆘 Need Help?

**Check logs:**
```bash
# Application logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api -f

# Gateway logs
kubectl -n kube-system logs -l app.kubernetes.io/name=cilium-operator | grep -i gateway

# cert-manager logs
kubectl -n cert-manager logs -l app=cert-manager -f
```

**Check AWS:**
- EC2 Console → Load Balancers
- EC2 Console → Target Groups
- CloudWatch → Metrics
- CloudWatch → Logs

**Common Commands:**
```bash
# Full status check
kubectl -n ai-data-capture get all
kubectl -n ai-data-capture get gateway,httproute,certificate

# Events
kubectl -n ai-data-capture get events --sort-by='.lastTimestamp'

# Describe resources
kubectl -n ai-data-capture describe gateway ai-data-capture-gateway
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

---

**🎉 Your application is now production-ready with AWS LoadBalancer!**

**Key Benefits:**
- ✅ High availability with automatic failover
- ✅ Secure (no NodePort exposure)
- ✅ Automatic TLS certificates
- ✅ Professional DNS setup
- ✅ AWS-managed infrastructure
