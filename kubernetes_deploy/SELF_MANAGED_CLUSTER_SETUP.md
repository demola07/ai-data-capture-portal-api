# Self-Managed Cluster Setup with Manual AWS LoadBalancer

Complete guide for deploying on a self-managed Kubernetes cluster (non-EKS) with manual AWS LoadBalancer.

## 📋 Your Setup

- **Cluster Type:** Self-managed (not EKS)
- **Nodes:** 1 control plane + 1 worker node
- **Cloud:** AWS EC2 instances
- **CNI:** Cilium
- **Challenge:** No AWS Cloud Controller Manager

---

## 🎯 Architecture

```
Internet
   ↓
AWS Network Load Balancer (Manual)
   ↓ (Port 80 → NodePort 30080)
   ↓ (Port 443 → NodePort 30443)
   ↓
Worker Node (EC2)
   ↓
Gateway API (Cilium) - NodePort Service
   ↓
FastAPI Pods
```

**Key Points:**
- ✅ NodePort service in Kubernetes
- ✅ Manual AWS NLB in front
- ✅ NodePort NOT exposed to internet (only to NLB)
- ✅ Production-ready with high availability

---

## 🚀 Deployment Steps

### Step 1: Deploy Application with NodePort

Your gateway.yaml is already configured for NodePort.

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Deploy everything
kubectl apply -k .

# Wait for deployment
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

### Step 2: Get NodePort Numbers

```bash
# Get the NodePort service created by Gateway
kubectl -n ai-data-capture get svc

# Look for service like: cilium-gateway-ai-data-capture-gateway
# Note the NodePort numbers (e.g., 80:30080/TCP, 443:30443/TCP)
```

**Example output:**
```
NAME                                      TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)
cilium-gateway-ai-data-capture-gateway   NodePort   10.96.123.45    <none>        80:30080/TCP,443:30443/TCP
```

**Note these ports:**
- HTTP: `30080` (or whatever is assigned)
- HTTPS: `30443` (or whatever is assigned)

### Step 3: Test NodePort Access

```bash
# Get worker node public IP
WORKER_IP=$(kubectl get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')

echo "Worker Node IP: $WORKER_IP"

# Test HTTP access (should work if security group allows)
curl -I http://$WORKER_IP:30080

# Test HTTPS access (will fail until certificate is issued)
curl -I -k https://$WORKER_IP:30443
```

---

## 🔧 Step 4: Create AWS Network Load Balancer

### Option A: Using AWS Console (Easier)

#### 4.1 Create Target Groups

**HTTP Target Group:**
1. Go to **EC2 → Target Groups → Create target group**
2. **Target type:** Instances
3. **Target group name:** `ai-data-capture-http-tg`
4. **Protocol:** TCP
5. **Port:** `30080` (your HTTP NodePort)
6. **VPC:** Select your cluster VPC
7. **Health check:**
   - Protocol: TCP
   - Port: 30080
8. **Register targets:**
   - Select your worker node(s)
   - Port: 30080
9. **Create**

**HTTPS Target Group:**
1. Repeat above steps with:
   - Name: `ai-data-capture-https-tg`
   - Port: `30443` (your HTTPS NodePort)
   - Health check port: 30443

#### 4.2 Create Network Load Balancer

1. Go to **EC2 → Load Balancers → Create Load Balancer**
2. Choose **Network Load Balancer**
3. **Basic Configuration:**
   - Name: `ai-data-capture-nlb`
   - Scheme: **Internet-facing**
   - IP address type: IPv4
4. **Network mapping:**
   - VPC: Select your cluster VPC
   - Availability Zones: Select at least 2 AZs with public subnets
5. **Listeners:**
   - **Listener 1:**
     - Protocol: TCP
     - Port: 80
     - Default action: Forward to `ai-data-capture-http-tg`
   - **Listener 2:**
     - Protocol: TCP
     - Port: 443
     - Default action: Forward to `ai-data-capture-https-tg`
6. **Tags (optional):**
   - Key: `Name`, Value: `ai-data-capture-nlb`
   - Key: `Environment`, Value: `production`
   - Key: `Application`, Value: `ai-data-capture`
7. **Create load balancer**

#### 4.3 Wait for Provisioning

Wait 2-5 minutes for the NLB to become active.

---

### Option B: Using AWS CLI (Faster)

```bash
# Set variables
CLUSTER_VPC_ID="vpc-xxxxx"  # Your VPC ID
SUBNET_1="subnet-xxxxx"     # Public subnet in AZ 1
SUBNET_2="subnet-yyyyy"     # Public subnet in AZ 2
WORKER_INSTANCE_ID="i-xxxxx"  # Your worker node instance ID
HTTP_NODEPORT="30080"       # Your HTTP NodePort
HTTPS_NODEPORT="30443"      # Your HTTPS NodePort

# Create HTTP target group
HTTP_TG_ARN=$(aws elbv2 create-target-group \
  --name ai-data-capture-http-tg \
  --protocol TCP \
  --port $HTTP_NODEPORT \
  --vpc-id $CLUSTER_VPC_ID \
  --health-check-protocol TCP \
  --health-check-port $HTTP_NODEPORT \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Create HTTPS target group
HTTPS_TG_ARN=$(aws elbv2 create-target-group \
  --name ai-data-capture-https-tg \
  --protocol TCP \
  --port $HTTPS_NODEPORT \
  --vpc-id $CLUSTER_VPC_ID \
  --health-check-protocol TCP \
  --health-check-port $HTTPS_NODEPORT \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Register worker node with target groups
aws elbv2 register-targets \
  --target-group-arn $HTTP_TG_ARN \
  --targets Id=$WORKER_INSTANCE_ID,Port=$HTTP_NODEPORT

aws elbv2 register-targets \
  --target-group-arn $HTTPS_TG_ARN \
  --targets Id=$WORKER_INSTANCE_ID,Port=$HTTPS_NODEPORT

# Create Network Load Balancer
NLB_ARN=$(aws elbv2 create-load-balancer \
  --name ai-data-capture-nlb \
  --type network \
  --scheme internet-facing \
  --subnets $SUBNET_1 $SUBNET_2 \
  --tags Key=Name,Value=ai-data-capture-nlb Key=Environment,Value=production \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Get NLB DNS name
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $NLB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "LoadBalancer DNS: $NLB_DNS"

# Create HTTP listener
aws elbv2 create-listener \
  --load-balancer-arn $NLB_ARN \
  --protocol TCP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$HTTP_TG_ARN

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $NLB_ARN \
  --protocol TCP \
  --port 443 \
  --default-actions Type=forward,TargetGroupArn=$HTTPS_TG_ARN

echo "✅ LoadBalancer created: $NLB_DNS"
```

---

## 🔒 Step 5: Configure Security Groups

### Worker Node Security Group

Update your worker node security group to:

**Remove (if exists):**
```
Source: 0.0.0.0/0
Ports: 30000-32767
❌ This exposes NodePort to internet!
```

**Add:**
```
# Allow traffic from NLB to NodePorts
Source: <NLB-Security-Group-ID>
Ports: 30080, 30443
Protocol: TCP
Description: Allow NLB to NodePort

# Or allow full NodePort range from NLB
Source: <NLB-Security-Group-ID>
Ports: 30000-32767
Protocol: TCP
Description: Allow NLB to all NodePorts
```

### NLB Security Group

The NLB automatically gets a security group. Verify it allows:

```
Inbound:
- Source: 0.0.0.0/0, Port: 80, Protocol: TCP
- Source: 0.0.0.0/0, Port: 443, Protocol: TCP

Outbound:
- All traffic
```

---

## 🌐 Step 6: Configure DNS

Get your NLB DNS name:

```bash
# From AWS Console: EC2 → Load Balancers → Your NLB → DNS name
# Or from CLI:
aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

### Configure DNS Records

**Option A: AWS Route53 (Recommended)**

```bash
HOSTED_ZONE_ID="Z1234567890ABC"  # Your hosted zone ID
NLB_DNS="ai-data-capture-nlb-xxxxx.elb.us-east-1.amazonaws.com"
NLB_HOSTED_ZONE="Z215JYRZR1TBD5"  # NLB hosted zone (varies by region)

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
```

**Option B: Other DNS Providers**

Create CNAME record:
```
Type: CNAME
Name: apidatacapture.store
Value: <NLB-DNS>
TTL: 300
```

---

## ✅ Step 7: Verify Setup

### 7.1 Check NLB Status

```bash
# Check NLB is active
aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].State.Code' \
  --output text
# Should show: active

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <HTTP-TG-ARN>

aws elbv2 describe-target-health \
  --target-group-arn <HTTPS-TG-ARN>
# Should show: healthy
```

### 7.2 Test LoadBalancer

```bash
# Get NLB DNS
NLB_DNS=$(aws elbv2 describe-load-balancers \
  --names ai-data-capture-nlb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test HTTP (should work immediately)
curl -I http://$NLB_DNS

# Test with Host header
curl -I -H "Host: apidatacapture.store" http://$NLB_DNS
```

### 7.3 Wait for DNS Propagation

```bash
# Check DNS resolution
dig apidatacapture.store +short

# Should resolve to NLB DNS or IP
```

### 7.4 Monitor Certificate Issuance

```bash
# Watch certificate status
kubectl -n ai-data-capture get certificate -w

# Once DNS is propagated, cert-manager will issue certificate
# This takes 2-5 minutes
```

### 7.5 Test Final Setup

```bash
# Test HTTP redirect
curl -I http://apidatacapture.store
# Should redirect to HTTPS

# Test HTTPS
curl -I https://apidatacapture.store
# Should return 200 OK

# Test API
curl https://apidatacapture.store/health
curl https://apidatacapture.store/docs
```

---

## 📊 Verification Checklist

### ✅ Kubernetes
- [ ] Pods running (3 replicas)
- [ ] Gateway created with NodePort service
- [ ] NodePort service accessible from worker node
- [ ] Certificate resource created
- [ ] ClusterIssuer created

### ✅ AWS LoadBalancer
- [ ] NLB created and active
- [ ] HTTP target group created (port 30080)
- [ ] HTTPS target group created (port 30443)
- [ ] Worker node registered in both target groups
- [ ] Target health: healthy
- [ ] NLB listeners configured (80, 443)

### ✅ Security Groups
- [ ] NLB security group allows 80, 443 from internet
- [ ] Worker node allows NodePort from NLB only
- [ ] Worker node does NOT allow NodePort from internet

### ✅ DNS & TLS
- [ ] DNS points to NLB
- [ ] DNS propagated
- [ ] Certificate issued (Ready: True)
- [ ] TLS secret created

### ✅ Access
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS accessible
- [ ] Valid TLS certificate
- [ ] API endpoints responding

---

## 🔍 Troubleshooting

### Issue: Targets Unhealthy

**Check NodePort accessibility:**
```bash
# SSH to worker node
ssh ec2-user@<worker-ip>

# Test locally
curl http://localhost:30080
curl -k https://localhost:30443
```

**Check security groups:**
```bash
# Verify NLB can reach worker node
# Worker SG should allow traffic from NLB SG on NodePort
```

### Issue: 502 Bad Gateway

**Check pods:**
```bash
kubectl -n ai-data-capture get pods
kubectl -n ai-data-capture logs -l app=ai-data-capture-api
```

**Check Gateway:**
```bash
kubectl -n ai-data-capture describe gateway ai-data-capture-gateway
```

### Issue: Certificate Not Issuing

**Verify DNS:**
```bash
dig apidatacapture.store +short
# Should resolve to NLB
```

**Check cert-manager:**
```bash
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
kubectl -n cert-manager logs -l app=cert-manager --tail=50
```

**Test HTTP-01 challenge:**
```bash
# Let's Encrypt needs port 80 accessible
curl http://apidatacapture.store/.well-known/acme-challenge/test
```

---

## 💰 Cost Breakdown

### AWS Network Load Balancer
```
Monthly Costs:
- NLB hourly: $0.0225/hour × 730 hours = ~$16.20/month
- LCU charge: ~$4-13/month (typical usage)
- Total: ~$20-30/month
```

### EC2 Instances (Your Existing Cost)
```
- Control plane: $X/month
- Worker node: $Y/month
- Total: Already paying for these
```

**Additional cost for production setup: ~$20-30/month for NLB**

---

## 🎯 Scaling Considerations

### Adding More Worker Nodes

When you add more worker nodes:

1. **Register new nodes with target groups:**
```bash
aws elbv2 register-targets \
  --target-group-arn <HTTP-TG-ARN> \
  --targets Id=<new-instance-id>,Port=30080

aws elbv2 register-targets \
  --target-group-arn <HTTPS-TG-ARN> \
  --targets Id=<new-instance-id>,Port=30443
```

2. **Update security groups:**
   - Add NLB → NodePort rule to new node's security group

3. **NLB automatically distributes traffic** across all healthy targets

### High Availability

For true HA:
- ✅ Deploy worker nodes in multiple AZs
- ✅ NLB distributes across AZs
- ✅ If one node fails, traffic goes to healthy nodes
- ✅ Add more replicas: `kubectl scale deployment ai-data-capture-api --replicas=5`

---

## 🔄 Alternative: Install AWS Cloud Controller Manager

If you want automatic LoadBalancer creation (like EKS), you can install AWS Cloud Controller Manager. However, this is complex and requires:

1. Node configuration changes
2. Kubelet restart with `--cloud-provider=external`
3. IAM role configuration
4. Cluster restart

**Not recommended** for a running cluster. Easier to use manual NLB approach.

---

## 📚 Summary

**Your Setup:**
```
✅ Self-managed K8s cluster (2 nodes)
✅ NodePort service in Kubernetes
✅ Manual AWS NLB in front
✅ Production-ready with HA
✅ Secure (NodePort not exposed to internet)
✅ Cost: ~$20-30/month for NLB
```

**Next Steps:**
1. Deploy application with NodePort
2. Create AWS NLB manually (Console or CLI)
3. Configure security groups
4. Point DNS to NLB
5. Wait for certificate issuance
6. Test and verify

**This is a production-ready setup used by many companies!**
