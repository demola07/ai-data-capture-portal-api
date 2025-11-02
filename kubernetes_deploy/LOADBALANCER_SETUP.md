# LoadBalancer Setup Guide - Production Deployment

Complete guide for deploying with AWS LoadBalancer for high availability and security.

## 📋 Overview

### Why LoadBalancer?

**✅ Benefits:**
- **High Availability** - Traffic distributed across all nodes
- **Security** - No NodePort exposure (30000-32767 range)
- **Automatic Failover** - AWS handles node failures
- **Health Checks** - AWS monitors backend health
- **Single Entry Point** - One DNS record for all traffic
- **SSL Termination** - Can terminate SSL at LB or Gateway

**Architecture:**
```
Internet → AWS Load Balancer → Gateway API (Cilium) → FastAPI Pods
              (NLB/CLB)              (Port 80/443)
```

### LoadBalancer Types

**Network Load Balancer (NLB) - Recommended:**
- Layer 4 (TCP/UDP)
- Ultra-low latency
- Static IP support
- Preserves source IP
- Best for production

**Classic Load Balancer (CLB):**
- Layer 4/7
- Legacy option
- Works but less features

**Application Load Balancer (ALB):**
- Layer 7 (HTTP/HTTPS)
- Not directly supported by Gateway API
- Use NLB instead

---

## 🚀 Deployment Steps

### Step 1: Prerequisites

Ensure you have:
- ✅ AWS credentials configured
- ✅ IAM permissions for LoadBalancer creation
- ✅ VPC with public subnets
- ✅ Internet Gateway attached to VPC
- ✅ Kubernetes cluster with AWS Cloud Provider

#### 1.1 Verify AWS Cloud Provider

Check if your cluster has AWS cloud provider configured:

```bash
# Check if nodes have provider ID
kubectl get nodes -o jsonpath='{.items[*].spec.providerID}'

# Should show: aws:///us-east-1a/i-xxxxx
```

If not configured, you need to enable AWS cloud provider in your cluster.

#### 1.2 Required IAM Permissions

Your Kubernetes nodes need IAM permissions to create LoadBalancers:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVolumes",
        "ec2:CreateSecurityGroup",
        "ec2:CreateTags",
        "ec2:DescribeVolumesModifications",
        "ec2:ModifyInstanceAttribute",
        "ec2:ModifyVolume",
        "ec2:DescribeVpcs",
        "elasticloadbalancing:*",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### Step 2: Update Gateway Configuration

Your `gateway.yaml` has been updated to use LoadBalancer:

```yaml
annotations:
  io.cilium/service-type: "LoadBalancer"
  service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
  service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
```

**Additional LoadBalancer Annotations (Optional):**

```yaml
# Enable cross-zone load balancing
service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

# Enable connection draining
service.beta.kubernetes.io/aws-load-balancer-connection-draining-enabled: "true"
service.beta.kubernetes.io/aws-load-balancer-connection-draining-timeout: "60"

# Health check configuration
service.beta.kubernetes.io/aws-load-balancer-healthcheck-interval: "10"
service.beta.kubernetes.io/aws-load-balancer-healthcheck-timeout: "5"
service.beta.kubernetes.io/aws-load-balancer-healthcheck-unhealthy-threshold: "3"
service.beta.kubernetes.io/aws-load-balancer-healthcheck-healthy-threshold: "2"

# Enable access logs (requires S3 bucket)
service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-lb-logs"
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "gateway"

# Specify subnets (optional - auto-discovers by default)
service.beta.kubernetes.io/aws-load-balancer-subnets: "subnet-xxxxx,subnet-yyyyy"

# Enable proxy protocol v2 (for source IP preservation)
service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"

# SSL certificate at LB level (alternative to Gateway TLS termination)
# service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/xxxxx"
# service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "http"
# service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
```

---

### Step 3: Deploy with LoadBalancer

#### 3.1 Deploy Gateway API Components

Follow the standard Gateway API setup:

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

#### 3.2 Deploy Application

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Apply all manifests (now with LoadBalancer)
kubectl apply -k .

# Wait for deployment
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

#### 3.3 Wait for LoadBalancer Provisioning

AWS will create the LoadBalancer (takes 2-5 minutes):

```bash
# Watch LoadBalancer creation
kubectl -n ai-data-capture get svc -w

# Check Gateway service
kubectl -n ai-data-capture get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway
```

**Expected output:**
```
NAME                              TYPE           EXTERNAL-IP                                                              
cilium-gateway-ai-data-capture-gateway   LoadBalancer   a1234567890abcdef.elb.us-east-1.amazonaws.com
```

---

### Step 4: Get LoadBalancer DNS

Once the LoadBalancer is created:

```bash
# Get LoadBalancer hostname
LB_HOSTNAME=$(kubectl -n ai-data-capture get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')

echo "LoadBalancer Hostname: $LB_HOSTNAME"

# Get LoadBalancer IP (for NLB with static IP)
LB_IP=$(kubectl -n ai-data-capture get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')

echo "LoadBalancer IP: $LB_IP"
```

**Note:** NLB provides hostname, not direct IP. You'll need to resolve it.

---

### Step 5: Configure DNS

You have two options for DNS configuration:

#### Option A: CNAME to LoadBalancer (Recommended for NLB)

```
Type: CNAME
Name: apidatacapture.store
Value: <LB_HOSTNAME>
TTL: 300
```

**⚠️ Important:** Root domain CNAME may not be supported by all DNS providers.

**Solution:** Use ALIAS record (Route53) or ANAME/CNAME flattening:

**For AWS Route53:**
```
Type: A (Alias)
Name: apidatacapture.store
Value: <LB_HOSTNAME>
Alias: Yes
Alias Target: <Select your NLB>
```

**For Cloudflare:**
```
Type: CNAME
Name: apidatacapture.store
Value: <LB_HOSTNAME>
Proxy Status: Proxied (Orange Cloud)
```

#### Option B: A Record to LoadBalancer IP

If using NLB with static IP allocation:

```bash
# Resolve LoadBalancer IP
dig +short $LB_HOSTNAME

# Create A record
Type: A
Name: apidatacapture.store
Value: <RESOLVED_IP>
TTL: 300
```

**⚠️ Warning:** NLB IPs can change. Use ALIAS/CNAME when possible.

#### Configure www Subdomain

```
Type: CNAME
Name: www
Value: apidatacapture.store
TTL: 300
```

---

### Step 6: Verify LoadBalancer

#### 6.1 Check LoadBalancer in AWS Console

1. Go to **EC2 → Load Balancers**
2. Find LoadBalancer with tag: `kubernetes.io/service-name=ai-data-capture/cilium-gateway-ai-data-capture-gateway`
3. Verify:
   - **State:** Active
   - **Scheme:** internet-facing
   - **Type:** network (NLB)
   - **Availability Zones:** Multiple AZs
   - **Target Groups:** Healthy targets

#### 6.2 Check Target Health

```bash
# Get LoadBalancer ARN from AWS Console, then:
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN>
```

Expected: All targets should be `healthy`

#### 6.3 Test LoadBalancer Connectivity

```bash
# Test HTTP (before DNS)
curl -I http://$LB_HOSTNAME

# Test HTTPS (before DNS)
curl -I https://$LB_HOSTNAME

# Test with Host header
curl -I -H "Host: apidatacapture.store" http://$LB_HOSTNAME
```

---

### Step 7: Wait for DNS and Certificate

#### 7.1 Verify DNS Propagation

```bash
# Check DNS resolution
dig apidatacapture.store +short

# Should resolve to LoadBalancer hostname or IP
```

#### 7.2 Monitor Certificate Issuance

```bash
# Watch certificate status
kubectl -n ai-data-capture get certificate -w

# Check certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

**Note:** Certificate issuance requires:
- DNS pointing to LoadBalancer
- Port 80 accessible for HTTP-01 challenge
- LoadBalancer forwarding traffic to Gateway

---

### Step 8: Final Verification

#### 8.1 Test HTTP to HTTPS Redirect

```bash
curl -I http://apidatacapture.store
```

Expected: `301 Moved Permanently` → HTTPS

#### 8.2 Test HTTPS Access

```bash
curl -I https://apidatacapture.store
```

Expected: `200 OK` with valid TLS

#### 8.3 Test API Endpoints

```bash
# Health check
curl https://apidatacapture.store/health

# API documentation
curl https://apidatacapture.store/docs

# Full test
curl -v https://apidatacapture.store/api/v1/endpoint
```

#### 8.4 Verify TLS Certificate

```bash
echo | openssl s_client -servername apidatacapture.store -connect apidatacapture.store:443 2>/dev/null | openssl x509 -noout -text
```

---

## 🔒 Security Configuration

### 1. LoadBalancer Security Group

AWS automatically creates a security group for the LoadBalancer.

**Verify rules:**
```bash
# Get LoadBalancer security group
aws ec2 describe-security-groups \
  --filters "Name=tag:kubernetes.io/service-name,Values=ai-data-capture/cilium-gateway-*"
```

**Expected rules:**
- Inbound: 0.0.0.0/0 → Port 80 (HTTP)
- Inbound: 0.0.0.0/0 → Port 443 (HTTPS)
- Outbound: All traffic

### 2. Node Security Group

Update your node security group to allow traffic from LoadBalancer:

```bash
# Allow traffic from LB security group to node ports
# Source: <LB_SECURITY_GROUP>
# Ports: 80, 443 (or NodePort range if needed)
```

**Recommended:** Remove NodePort access from 0.0.0.0/0:
```bash
# Remove this rule (if exists):
# 0.0.0.0/0 → 30000-32767

# Add this rule:
# <LB_SECURITY_GROUP> → 30000-32767
```

### 3. Network Policies

Your manifests already include network policies. Verify:

```bash
kubectl -n ai-data-capture get networkpolicy
```

---

## 💰 Cost Considerations

### AWS LoadBalancer Costs

**Network Load Balancer (NLB):**
- **Hourly charge:** ~$0.0225/hour (~$16/month)
- **LCU charge:** ~$0.006/LCU-hour
- **Data processing:** Included in LCU
- **Total:** ~$20-30/month for small workloads

**Classic Load Balancer (CLB):**
- **Hourly charge:** ~$0.025/hour (~$18/month)
- **Data transfer:** $0.008/GB
- **Total:** ~$20-25/month

**Cost Optimization:**
- Use single LoadBalancer for multiple services
- Enable cross-zone load balancing carefully (adds cost)
- Monitor LCU usage
- Consider reserved capacity for predictable workloads

---

## 🔍 Monitoring and Troubleshooting

### Check LoadBalancer Status

```bash
# Get LoadBalancer details
kubectl -n ai-data-capture describe svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway

# Check events
kubectl -n ai-data-capture get events --sort-by='.lastTimestamp' | grep -i loadbalancer
```

### Common Issues

#### Issue: LoadBalancer Stuck in Pending

**Symptoms:**
```
EXTERNAL-IP: <pending>
```

**Causes:**
1. AWS cloud provider not configured
2. IAM permissions missing
3. No public subnets available
4. Subnet tags missing

**Solution:**
```bash
# Check cloud provider
kubectl get nodes -o jsonpath='{.items[*].spec.providerID}'

# Check events
kubectl -n ai-data-capture describe svc <service-name>

# Verify subnet tags (required for auto-discovery)
# Tag: kubernetes.io/role/elb = 1
```

#### Issue: Unhealthy Targets

**Symptoms:** Targets show as unhealthy in AWS Console

**Solution:**
```bash
# Check pod health
kubectl -n ai-data-capture get pods

# Check pod logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api

# Check service endpoints
kubectl -n ai-data-capture get endpoints

# Verify health check path
kubectl -n ai-data-capture get gateway ai-data-capture-gateway -o yaml
```

#### Issue: 502 Bad Gateway

**Symptoms:** LoadBalancer returns 502 error

**Causes:**
1. Pods not ready
2. Service misconfigured
3. Gateway not ready
4. Network policies blocking traffic

**Solution:**
```bash
# Check all components
kubectl -n ai-data-capture get all

# Check Gateway
kubectl -n ai-data-capture describe gateway ai-data-capture-gateway

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
curl http://ai-data-capture-api-service.ai-data-capture.svc.cluster.local/health
```

#### Issue: Certificate Not Issuing

**Symptoms:** Certificate stays in `Ready: False`

**Causes:**
1. DNS not pointing to LoadBalancer
2. Port 80 not accessible
3. LoadBalancer not forwarding to Gateway

**Solution:**
```bash
# Verify DNS
dig apidatacapture.store +short

# Test HTTP-01 challenge path
curl http://apidatacapture.store/.well-known/acme-challenge/test

# Check cert-manager logs
kubectl -n cert-manager logs -l app=cert-manager --tail=100

# Check challenges
kubectl -n ai-data-capture get challenges
kubectl -n ai-data-capture describe challenge
```

---

## 📊 LoadBalancer Monitoring

### CloudWatch Metrics

Monitor these metrics in AWS CloudWatch:

**NLB Metrics:**
- `ActiveFlowCount` - Active connections
- `NewFlowCount` - New connections per minute
- `ProcessedBytes` - Data processed
- `HealthyHostCount` - Healthy targets
- `UnHealthyHostCount` - Unhealthy targets
- `TCP_Target_Reset_Count` - Connection resets

**Set up alarms for:**
- UnHealthyHostCount > 0
- HealthyHostCount < 2
- High error rates

### Kubernetes Monitoring

```bash
# Check service metrics
kubectl -n ai-data-capture get svc -o wide

# Check endpoint status
kubectl -n ai-data-capture get endpoints

# Monitor pod metrics (requires metrics-server)
kubectl -n ai-data-capture top pods
```

---

## 🔄 Updating LoadBalancer Configuration

### Change LoadBalancer Type

To switch from CLB to NLB:

```bash
# Edit Gateway annotations
kubectl -n ai-data-capture annotate gateway ai-data-capture-gateway \
  service.beta.kubernetes.io/aws-load-balancer-type=nlb --overwrite

# Delete and recreate service (LoadBalancer will be recreated)
kubectl -n ai-data-capture delete svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway
kubectl apply -k /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests
```

**⚠️ Warning:** This will create a new LoadBalancer with a new DNS name. Update your DNS records.

### Add LoadBalancer Annotations

```bash
# Edit gateway.yaml and add annotations
kubectl apply -k /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests
```

---

## 🎯 Production Checklist

- [ ] AWS cloud provider configured
- [ ] IAM permissions granted
- [ ] VPC has public subnets with IGW
- [ ] Subnet tags configured (`kubernetes.io/role/elb=1`)
- [ ] Gateway configured with LoadBalancer
- [ ] LoadBalancer provisioned successfully
- [ ] DNS configured (ALIAS/CNAME to LB)
- [ ] DNS propagated globally
- [ ] Certificate issued (Ready: True)
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS accessible with valid TLS
- [ ] All targets healthy in AWS Console
- [ ] Security groups properly configured
- [ ] NodePort access removed from public
- [ ] CloudWatch alarms configured
- [ ] Access logs enabled (optional)
- [ ] Cross-zone load balancing configured

---

## 📚 Additional Resources

- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Kubernetes LoadBalancer Service](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer)
- [AWS NLB Documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/)
- [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/)

---

## 🆘 Need Help?

**Check logs:**
```bash
# Application logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api -f

# Gateway logs (Cilium)
kubectl -n kube-system logs -l app.kubernetes.io/name=cilium-operator | grep -i gateway

# cert-manager logs
kubectl -n cert-manager logs -l app=cert-manager -f
```

**Check AWS Console:**
- EC2 → Load Balancers
- EC2 → Target Groups
- CloudWatch → Metrics
- CloudWatch → Logs

---

**🎉 Your application is now highly available and secure with AWS LoadBalancer!**
