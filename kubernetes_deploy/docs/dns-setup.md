# DNS Configuration for apidatacapture.store

This guide covers the DNS setup required for your domain `apidatacapture.store` to work with your Kubernetes Gateway API.

## 🌐 **DNS Records Required**

### **1. Get Your Gateway External IP**

First, deploy your Gateway and get its external IP:

```bash
# Deploy the Gateway
kubectl apply -f kubernetes_deploy/gateway.yaml

# Wait for Gateway to get an external IP
kubectl get gateway ai-data-capture-gateway -n ai-data-capture -w

# Get the external IP address
kubectl get gateway ai-data-capture-gateway -n ai-data-capture -o jsonpath='{.status.addresses[0].value}'
```

### **2. Configure DNS Records**

In your domain provider's DNS management panel, create these records:

#### **A Record (Primary)**
```
Type: A
Name: @ (or leave blank for root domain)
Value: <GATEWAY_EXTERNAL_IP>
TTL: 300 (5 minutes)
```

#### **CNAME Record (Optional - for www)**
```
Type: CNAME
Name: www
Value: apidatacapture.store
TTL: 300
```

## 🔧 **AWS Route 53 Configuration (if using AWS)**

If your domain is managed by AWS Route 53:

```bash
# Get your hosted zone ID
aws route53 list-hosted-zones --query "HostedZones[?Name=='apidatacapture.store.'].Id" --output text

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "apidatacapture.store",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<GATEWAY_EXTERNAL_IP>"}]
      }
    }]
  }'
```

## 🔍 **Verify DNS Configuration**

### **1. Check DNS Propagation**

```bash
# Check A record
dig apidatacapture.store A

# Check from different DNS servers
dig @8.8.8.8 apidatacapture.store A
dig @1.1.1.1 apidatacapture.store A

# Check with nslookup
nslookup apidatacapture.store
```

### **2. Test HTTP Connectivity**

```bash
# Test HTTP (should redirect to HTTPS)
curl -v http://apidatacapture.store/health

# Test HTTPS (requires valid certificate)
curl -v https://apidatacapture.store/health
```

## 🔒 **SSL Certificate Setup**

### **Option 1: Let's Encrypt with cert-manager**

Install cert-manager and create a certificate:

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com  # Update with your email
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: cilium
EOF

# Create Certificate
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: apidatacapture-store-tls
  namespace: ai-data-capture
spec:
  secretName: ai-data-capture-tls-cert
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - apidatacapture.store
  - www.apidatacapture.store
EOF
```

### **Option 2: Manual Certificate**

If you have your own certificate:

```bash
# Create TLS secret with your certificate
kubectl create secret tls ai-data-capture-tls-cert \
  --cert=path/to/apidatacapture.store.crt \
  --key=path/to/apidatacapture.store.key \
  -n ai-data-capture
```

## 🚀 **Complete Deployment Steps**

### **1. Deploy Prerequisites**

```bash
# Install Gateway API CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Ensure Cilium Gateway API is enabled
helm upgrade cilium cilium/cilium \
  --namespace cilium-system \
  --set gatewayAPI.enabled=true \
  --set l7Proxy=true \
  --set envoy.enabled=true
```

### **2. Deploy Application**

```bash
# Deploy all kubernetes_deploy
kubectl apply -k kubernetes_deploy/

# Check deployment status
kubectl get all -n ai-data-capture
kubectl get gateway -n ai-data-capture
kubectl get httproute -n ai-data-capture
```

### **3. Configure DNS**

```bash
# Get Gateway IP
GATEWAY_IP=$(kubectl get gateway ai-data-capture-gateway -n ai-data-capture -o jsonpath='{.status.addresses[0].value}')
echo "Configure DNS A record: apidatacapture.store -> $GATEWAY_IP"
```

### **4. Test Everything**

```bash
# Wait for DNS propagation (can take up to 48 hours)
dig apidatacapture.store A

# Test HTTP redirect
curl -v http://apidatacapture.store/health

# Test HTTPS
curl -v https://apidatacapture.store/health

# Test API endpoints
curl -v https://apidatacapture.store/docs
```

## 🛠 **Troubleshooting**

### **DNS Issues**

```bash
# Check if domain resolves to correct IP
dig apidatacapture.store A +short

# Check DNS propagation globally
# Use online tools like whatsmydns.net or dnschecker.org
```

### **Gateway Issues**

```bash
# Check Gateway status
kubectl describe gateway ai-data-capture-gateway -n ai-data-capture

# Check Gateway logs
kubectl logs -n cilium-system -l k8s-app=cilium-operator | grep gateway
```

### **Certificate Issues**

```bash
# Check certificate status (if using cert-manager)
kubectl get certificate -n ai-data-capture
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture

# Check TLS secret
kubectl get secret ai-data-capture-tls-cert -n ai-data-capture
```

## 📋 **DNS Configuration Checklist**

- [ ] Gateway deployed and has external IP
- [ ] A record created: `apidatacapture.store` -> `<GATEWAY_IP>`
- [ ] DNS propagation verified with `dig` command
- [ ] HTTP redirect working (301/302 to HTTPS)
- [ ] HTTPS certificate configured and valid
- [ ] Application accessible at `https://apidatacapture.store`

## 🎯 **Expected Results**

Once everything is configured:

- ✅ `http://apidatacapture.store` redirects to HTTPS
- ✅ `https://apidatacapture.store/health` returns API health status
- ✅ `https://apidatacapture.store/docs` shows API documentation
- ✅ All API endpoints accessible via your domain

Your API will be live at: **https://apidatacapture.store** 🚀
