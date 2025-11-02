# Gateway API with TLS Setup Guide

Complete step-by-step guide to deploy your application with Gateway API and automatic TLS certificates.

## 📋 Overview

You currently have:
- ✅ Self-managed Kubernetes cluster on AWS
- ✅ Application running and accessible via NodePort
- ✅ Domain: `apidatacapture.store`
- ✅ Gateway API manifests ready

You need to:
- 🎯 Install Gateway API CRDs
- 🎯 Configure Cilium for Gateway API
- 🎯 Install cert-manager
- 🎯 Configure DNS
- 🎯 Deploy application with Gateway API
- 🎯 Obtain TLS certificates

---

## 🚀 Step-by-Step Deployment

### Step 1: Install Gateway API CRDs

Gateway API requires Custom Resource Definitions (CRDs) to be installed first.

```bash
# Install Gateway API v1.0.0 CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Verify installation
kubectl get crd | grep gateway
```

**Expected output:**
```
gatewayclasses.gateway.networking.k8s.io
gateways.gateway.networking.k8s.io
httproutes.gateway.networking.k8s.io
referencegrants.gateway.networking.k8s.io
```

---

### Step 2: Configure Cilium for Gateway API

Check if Cilium is already configured for Gateway API:

```bash
# Check Cilium configuration
kubectl -n kube-system get cm cilium-config -o yaml | grep -i gateway
```

If Gateway API is not enabled, enable it:

```bash
# Enable Gateway API in Cilium
kubectl -n kube-system patch configmap cilium-config --type merge -p '{"data":{"enable-gateway-api":"true"}}'

# Restart Cilium pods to apply changes
kubectl -n kube-system rollout restart deployment/cilium-operator
kubectl -n kube-system rollout restart daemonset/cilium
```

**Verify Cilium Gateway Controller:**
```bash
# Check if Cilium Gateway Controller is running
kubectl -n kube-system get pods -l app.kubernetes.io/name=cilium-operator

# Check logs
kubectl -n kube-system logs -l app.kubernetes.io/name=cilium-operator | grep -i gateway
```

---

### Step 3: Install cert-manager

cert-manager automates TLS certificate management with Let's Encrypt.

#### Option A: Using Helm (Recommended)

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Create cert-manager namespace
kubectl create namespace cert-manager

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.0 \
  --values kubernetes_deploy/helm/cert-manager-values.yaml

# Verify installation
kubectl -n cert-manager get pods
```

#### Option B: Using kubectl

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Verify installation
kubectl -n cert-manager get pods
```

**Wait for all pods to be Running:**
```bash
kubectl -n cert-manager wait --for=condition=ready pod --all --timeout=300s
```

**Verify cert-manager is working:**
```bash
# Check cert-manager webhook
kubectl -n cert-manager get validatingwebhookconfigurations
kubectl -n cert-manager get mutatingwebhookconfigurations
```

---

### Step 4: Create AWS Load Balancer (Self-Managed Cluster)

**Note:** Since you're using a self-managed Kubernetes cluster (not EKS), you need to manually create an AWS Network Load Balancer.

#### 4.1 Deploy Application First

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Deploy all resources
kubectl apply -k .

# Wait for deployment
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

#### 4.2 Get Gateway NodePort

The Gateway will create a NodePort service. Get the port numbers:

```bash
# Get Gateway service
kubectl -n ai-data-capture get svc

# Look for: cilium-gateway-ai-data-capture-gateway
# Note the NodePort numbers (e.g., 80:30123/TCP, 443:30456/TCP)

# Save the ports
HTTP_NODEPORT=$(kubectl -n ai-data-capture get svc cilium-gateway-ai-data-capture-gateway -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')
HTTPS_NODEPORT=$(kubectl -n ai-data-capture get svc cilium-gateway-ai-data-capture-gateway -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')

echo "HTTP NodePort: $HTTP_NODEPORT"
echo "HTTPS NodePort: $HTTPS_NODEPORT"
```

#### 4.3 Create AWS Network Load Balancer

**Option A: Using AWS Console**

1. **Create Target Groups:**
   - Go to **EC2 → Target Groups → Create target group**
   - **HTTP Target Group:**
     - Name: `ai-data-capture-http-tg`
     - Protocol: TCP
     - Port: `<HTTP_NODEPORT>` (e.g., 30123)
     - VPC: Your cluster VPC
     - Health check: TCP on same port
     - Register targets: Your worker node(s)
   
   - **HTTPS Target Group:**
     - Name: `ai-data-capture-https-tg`
     - Protocol: TCP
     - Port: `<HTTPS_NODEPORT>` (e.g., 30456)
     - VPC: Your cluster VPC
     - Health check: TCP on same port
     - Register targets: Your worker node(s)

2. **Create Network Load Balancer:**
   - Go to **EC2 → Load Balancers → Create Load Balancer**
   - Choose **Network Load Balancer**
   - Name: `ai-data-capture-nlb`
   - Scheme: **Internet-facing**
   - IP address type: IPv4
   - Network mapping: Select your VPC and at least 2 public subnets
   - **Listeners:**
     - Listener 1: TCP port 80 → Forward to `ai-data-capture-http-tg`
     - Listener 2: TCP port 443 → Forward to `ai-data-capture-https-tg`
   - Create load balancer

**Option B: Using AWS CLI**

```bash
# Set variables
VPC_ID="vpc-xxxxx"
SUBNET_1="subnet-xxxxx"
SUBNET_2="subnet-yyyyy"
WORKER_INSTANCE_ID="i-xxxxx"

# Create target groups
HTTP_TG_ARN=$(aws elbv2 create-target-group \
  --name ai-data-capture-http-tg \
  --protocol TCP \
  --port $HTTP_NODEPORT \
  --vpc-id $VPC_ID \
  --health-check-protocol TCP \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

HTTPS_TG_ARN=$(aws elbv2 create-target-group \
  --name ai-data-capture-https-tg \
  --protocol TCP \
  --port $HTTPS_NODEPORT \
  --vpc-id $VPC_ID \
  --health-check-protocol TCP \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Register worker node
aws elbv2 register-targets \
  --target-group-arn $HTTP_TG_ARN \
  --targets Id=$WORKER_INSTANCE_ID,Port=$HTTP_NODEPORT

aws elbv2 register-targets \
  --target-group-arn $HTTPS_TG_ARN \
  --targets Id=$WORKER_INSTANCE_ID,Port=$HTTPS_NODEPORT

# Create NLB
NLB_ARN=$(aws elbv2 create-load-balancer \
  --name ai-data-capture-nlb \
  --type network \
  --scheme internet-facing \
  --subnets $SUBNET_1 $SUBNET_2 \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Get NLB DNS
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $NLB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "LoadBalancer DNS: $NLB_DNS"

# Create listeners
aws elbv2 create-listener \
  --load-balancer-arn $NLB_ARN \
  --protocol TCP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$HTTP_TG_ARN

aws elbv2 create-listener \
  --load-balancer-arn $NLB_ARN \
  --protocol TCP \
  --port 443 \
  --default-actions Type=forward,TargetGroupArn=$HTTPS_TG_ARN
```

#### 4.4 Wait for LoadBalancer Provisioning

Wait 2-5 minutes for AWS to provision the NLB. Check status:

```bash
# Check in AWS Console: EC2 → Load Balancers
# Status should be: Active

# Or via CLI
aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].State.Code' \
  --output text
```

#### 4.5 Get LoadBalancer DNS Name

```bash
# From AWS Console: EC2 → Load Balancers → Your NLB → DNS name
# Example: ai-data-capture-nlb-1234567890.elb.us-east-1.amazonaws.com

# Or via CLI
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "LoadBalancer DNS: $NLB_DNS"
```

---

### Step 5: Configure DNS

Point your domain to the AWS Load Balancer.

#### 5.1 DNS Configuration Options

You have **two options** depending on your DNS provider:

**Option A: ALIAS Record (AWS Route53 Only) - RECOMMENDED**

If using AWS Route53, use an ALIAS record (no additional cost, better performance):

```bash
# Get your hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='apidatacapture.store.'].Id" \
  --output text | cut -d'/' -f3)

# Get NLB hosted zone ID (varies by region)
NLB_HOSTED_ZONE=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].CanonicalHostedZoneId' \
  --output text)

# Create ALIAS record
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "apidatacapture.store",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "'$NLB_HOSTED_ZONE'",
          "DNSName": "'$NLB_DNS'",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'

# Create www subdomain
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.apidatacapture.store",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "apidatacapture.store"}]
      }
    }]
  }'
```

**In Route53 Console:**
1. Go to **Route53 → Hosted Zones → apidatacapture.store**
2. **Create Record:**
   - Record name: (leave empty for root domain)
   - Record type: **A**
   - Toggle **Alias**: ON
   - Route traffic to: **Alias to Network Load Balancer**
   - Region: Your NLB region
   - Load Balancer: Select your NLB
   - Click **Create records**
3. **Create www subdomain:**
   - Record name: `www`
   - Record type: **CNAME**
   - Value: `apidatacapture.store`
   - TTL: 300
   - Click **Create records**

**Option B: CNAME Record (Other DNS Providers)**

For Cloudflare, GoDaddy, Namecheap, etc.:

**⚠️ Important:** Most DNS providers don't support CNAME for root domain. You have two sub-options:

**Sub-option B1: CNAME Flattening (Cloudflare, Cloudflare-like providers)**

If your provider supports CNAME flattening:

```
Record 1:
Type: CNAME
Name: @ (or apidatacapture.store)
Value: <NLB_DNS>
TTL: 300
Proxy: Enabled (if Cloudflare)

Record 2:
Type: CNAME
Name: www
Value: apidatacapture.store
TTL: 300
```

**Sub-option B2: A Records with Resolved IPs (Traditional providers)**

If your provider doesn't support CNAME for root:

```bash
# First, resolve the NLB DNS to IP addresses
dig +short $NLB_DNS

# Example output:
# 54.123.45.67
# 54.123.45.68
```

Then create A records for each IP:

```
Record 1:
Type: A
Name: @ (or apidatacapture.store)
Value: 54.123.45.67
TTL: 300

Record 2:
Type: A
Name: @ (or apidatacapture.store)
Value: 54.123.45.68
TTL: 300

Record 3:
Type: CNAME
Name: www
Value: apidatacapture.store
TTL: 300
```

**⚠️ Warning:** NLB IPs can change. ALIAS (Route53) or CNAME flattening is preferred.

#### 5.2 DNS Configuration Summary

| DNS Provider | Root Domain (apidatacapture.store) | www Subdomain |
|--------------|-----------------------------------|---------------|
| **AWS Route53** | A (ALIAS) → NLB | CNAME → apidatacapture.store |
| **Cloudflare** | CNAME → NLB (flattened) | CNAME → apidatacapture.store |
| **GoDaddy/Namecheap** | A → Resolved IPs | CNAME → apidatacapture.store |

#### 5.3 Verify DNS Propagation

```bash
# Check DNS resolution
dig apidatacapture.store +short
dig www.apidatacapture.store +short

# Should resolve to NLB IPs or NLB DNS (depending on record type)

# Check from different DNS servers
dig @8.8.8.8 apidatacapture.store +short
dig @1.1.1.1 apidatacapture.store +short

# Check global propagation
# Visit: https://www.whatsmydns.net/#A/apidatacapture.store
```

**Wait for DNS to propagate** (5-60 minutes, usually 5-15 minutes with low TTL).

---

### Step 6: Monitor Certificate Issuance

Once DNS is propagated, cert-manager will automatically request a certificate from Let's Encrypt.

#### 6.1 Check Certificate Status

```bash
# Watch certificate status
kubectl -n ai-data-capture get certificate -w

# Check certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

**Expected progression:**
1. `Ready: False` - Certificate requested
2. `Ready: True` - Certificate issued

#### 6.2 Check CertificateRequest

```bash
# List certificate requests
kubectl -n ai-data-capture get certificaterequest

# Describe the request
kubectl -n ai-data-capture describe certificaterequest
```

#### 6.3 Check cert-manager Logs

If certificate issuance fails:
```bash
# Check cert-manager controller logs
kubectl -n cert-manager logs -l app=cert-manager --tail=100

# Check cert-manager webhook logs
kubectl -n cert-manager logs -l app=webhook --tail=100
```

#### 6.4 Verify TLS Secret Created

Once certificate is issued:
```bash
# Check if secret was created
kubectl -n ai-data-capture get secret apidatacapture-store-tls-secret

# View certificate details
kubectl -n ai-data-capture get secret apidatacapture-store-tls-secret -o yaml
```

---

### Step 7: Test and Verify

Once DNS is propagated and certificate is issued, test your setup.

#### 7.1 Test LoadBalancer Connectivity

```bash
# Get NLB DNS
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test HTTP (should work immediately)
curl -I http://$NLB_DNS

# Test HTTPS (after certificate is issued)
curl -I https://$NLB_DNS

# Test with Host header
curl -I -H "Host: apidatacapture.store" http://$NLB_DNS
```

#### 7.2 Configure AWS Security Group

Ensure your worker node security group allows traffic from NLB:
- **Port 80** (HTTP) - for Let's Encrypt validation and HTTP redirect
- **Port 443** (HTTPS) - for secure traffic
- **NodePort range** (30000-32767) - if using NodePort

**Example AWS Security Group Rules:**
```
Type: HTTP
Protocol: TCP
Port: 80
Source: 0.0.0.0/0

Type: HTTPS
Protocol: TCP
Port: 443
Source: 0.0.0.0/0

Type: Custom TCP
Protocol: TCP
Port: 30000-32767
Source: 0.0.0.0/0
```

---

### Step 9: Test HTTP to HTTPS Redirect

Once DNS is propagated and certificate is issued:

```bash
# Test HTTP redirect (should redirect to HTTPS)
curl -I http://apidatacapture.store

# Test HTTPS access
curl -I https://apidatacapture.store

# Test API endpoint
curl https://apidatacapture.store/health

# Test with verbose output
curl -v https://apidatacapture.store/docs
```

**Expected behavior:**
- HTTP request → 301 redirect to HTTPS
- HTTPS request → 200 OK with valid TLS certificate

---

### Step 10: Verify TLS Certificate

Check the TLS certificate in your browser or via command line:

```bash
# Check certificate details
echo | openssl s_client -servername apidatacapture.store -connect apidatacapture.store:443 2>/dev/null | openssl x509 -noout -text

# Check certificate expiry
echo | openssl s_client -servername apidatacapture.store -connect apidatacapture.store:443 2>/dev/null | openssl x509 -noout -dates

# Verify certificate chain
curl -vI https://apidatacapture.store 2>&1 | grep -A 10 "SSL certificate"
```

**Expected output:**
- Issuer: Let's Encrypt
- Valid for: apidatacapture.store, www.apidatacapture.store
- Expiry: ~90 days from issuance

---

## 🔍 Verification Checklist

After deployment, verify everything is working:

### ✅ Infrastructure
- [ ] Gateway API CRDs installed
- [ ] Cilium Gateway Controller running
- [ ] cert-manager pods running

### ✅ DNS
- [ ] DNS A records configured
- [ ] DNS resolves to correct IP
- [ ] DNS propagated globally

### ✅ Kubernetes Resources
- [ ] Namespace created
- [ ] Deployment running (3 replicas)
- [ ] Service created
- [ ] Gateway created and ready
- [ ] HTTPRoute created
- [ ] ClusterIssuer created

### ✅ TLS Certificate
- [ ] Certificate resource created
- [ ] Certificate status: Ready=True
- [ ] TLS secret created
- [ ] Certificate valid for domain

### ✅ Network Access
- [ ] Security group allows ports 80, 443
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS accessible
- [ ] API endpoints responding

### ✅ Application
- [ ] Pods running and healthy
- [ ] Health check passing
- [ ] API documentation accessible at /docs

---

## 🐛 Troubleshooting

### Issue: Certificate Not Issuing

**Check certificate status:**
```bash
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

**Common causes:**
1. **DNS not propagated** - Wait for DNS to propagate
2. **Port 80 blocked** - Let's Encrypt needs port 80 for HTTP-01 challenge
3. **Gateway not ready** - Ensure Gateway is in Ready state

**Check HTTP-01 challenge:**
```bash
# Check if challenge is created
kubectl -n ai-data-capture get challenges

# Describe challenge
kubectl -n ai-data-capture describe challenge
```

**Manual test HTTP-01 challenge:**
```bash
# Let's Encrypt will try to access:
curl http://apidatacapture.store/.well-known/acme-challenge/test
```

### Issue: Gateway Not Ready

**Check Gateway status:**
```bash
kubectl -n ai-data-capture describe gateway ai-data-capture-gateway
```

**Check Cilium Gateway Controller:**
```bash
kubectl -n kube-system logs -l app.kubernetes.io/name=cilium-operator | grep -i gateway
```

**Verify GatewayClass:**
```bash
kubectl get gatewayclass cilium -o yaml
```

### Issue: DNS Not Resolving

**Check DNS configuration:**
```bash
# Check from different DNS servers
dig @8.8.8.8 apidatacapture.store
dig @1.1.1.1 apidatacapture.store

# Check DNS propagation globally
https://www.whatsmydns.net/#A/apidatacapture.store
```

### Issue: Application Not Accessible

**Check pod status:**
```bash
kubectl -n ai-data-capture get pods
kubectl -n ai-data-capture logs -l app=ai-data-capture-api
```

**Check service endpoints:**
```bash
kubectl -n ai-data-capture get endpoints
```

**Check Gateway service:**
```bash
kubectl -n ai-data-capture get svc
```

**Test from within cluster:**
```bash
# Create debug pod
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh

# Inside pod, test service
curl http://ai-data-capture-api-service.ai-data-capture.svc.cluster.local/health
```

### Issue: TLS Certificate Expired

cert-manager automatically renews certificates 15 days before expiry.

**Force renewal:**
```bash
# Delete certificate to force renewal
kubectl -n ai-data-capture delete certificate apidatacapture-store-tls

# Reapply certificate
kubectl apply -f manifests/certificate.yaml
```

---

## 📊 Monitoring

### Check Application Health

```bash
# Check pod status
kubectl -n ai-data-capture get pods

# Check pod logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api --tail=100 -f

# Check events
kubectl -n ai-data-capture get events --sort-by='.lastTimestamp'
```

### Check Gateway Metrics

```bash
# Check Gateway status
kubectl -n ai-data-capture get gateway ai-data-capture-gateway -o yaml

# Check HTTPRoute status
kubectl -n ai-data-capture get httproute ai-data-capture-api-route -o yaml
```

### Check Certificate Renewal

```bash
# Check certificate expiry
kubectl -n ai-data-capture get certificate apidatacapture-store-tls -o jsonpath='{.status.notAfter}'

# Check renewal status
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls | grep -A 5 "Renewal Time"
```

---

## 🔒 Security Considerations

### 1. Use Production Let's Encrypt

Your manifests use `letsencrypt-prod`. This is correct for production.

**Rate limits:**
- 50 certificates per domain per week
- 5 duplicate certificates per week

### 2. Secure Secrets

Ensure secrets are properly configured:
```bash
# Check secrets (values should be base64 encoded)
kubectl -n ai-data-capture get secret ai-data-capture-secret -o yaml
```

### 3. Network Policies

Your manifests include network policies. Verify they're applied:
```bash
kubectl -n ai-data-capture get networkpolicy
```

### 4. RBAC

Ensure service account has minimal permissions:
```bash
kubectl -n ai-data-capture get serviceaccount
kubectl -n ai-data-capture get role
kubectl -n ai-data-capture get rolebinding
```

---

## 🎯 Quick Commands Reference

### Deploy Everything
```bash
kubectl apply -k /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests
```

### Check Status
```bash
# All resources
kubectl -n ai-data-capture get all

# Certificate
kubectl -n ai-data-capture get certificate

# Gateway
kubectl -n ai-data-capture get gateway
```

### View Logs
```bash
# Application logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api -f

# cert-manager logs
kubectl -n cert-manager logs -l app=cert-manager -f
```

### Delete Everything
```bash
kubectl delete -k /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests
```

---

## 📝 Next Steps

After successful deployment:

1. **Set up monitoring** - Add Prometheus/Grafana
2. **Configure backups** - Backup secrets and certificates
3. **Set up CI/CD** - Automate deployments
4. **Add rate limiting** - Use Cilium L7 policies (already in manifests)
5. **Configure logging** - Centralized logging with ELK/Loki
6. **Set up alerts** - Alert on certificate expiry, pod failures

---

## 📚 Additional Resources

- [Gateway API Documentation](https://gateway-api.sigs.k8s.io/)
- [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs from all components
3. Verify DNS and network connectivity
4. Check cert-manager and Gateway API documentation

**Common log locations:**
- Application: `kubectl -n ai-data-capture logs -l app=ai-data-capture-api`
- cert-manager: `kubectl -n cert-manager logs -l app=cert-manager`
- Cilium: `kubectl -n kube-system logs -l k8s-app=cilium`
