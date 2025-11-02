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

### Step 4: Configure DNS

Point your domain to your Kubernetes cluster's public IP.

#### 4.1 Get Your Cluster's Public IP

```bash
# Get the public IP of one of your nodes
kubectl get nodes -o wide

# Or get the external IP directly
EXTERNAL_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
echo "Cluster Public IP: $EXTERNAL_IP"
```

#### 4.2 Configure DNS Records

Go to your DNS provider (e.g., Route53, Cloudflare, GoDaddy) and create:

**A Records:**
```
Type: A
Name: @
Value: <YOUR_CLUSTER_PUBLIC_IP>
TTL: 300

Type: A
Name: www
Value: <YOUR_CLUSTER_PUBLIC_IP>
TTL: 300
```

**Example for apidatacapture.store:**
```
apidatacapture.store        A    <YOUR_IP>
www.apidatacapture.store    A    <YOUR_IP>
```

#### 4.3 Verify DNS Propagation

```bash
# Check DNS resolution
dig apidatacapture.store +short
dig www.apidatacapture.store +short

# Or use nslookup
nslookup apidatacapture.store
```

**Wait for DNS to propagate** (can take 5-60 minutes depending on TTL).

---

### Step 5: Update Manifest Configuration

Before deploying, ensure your manifests have the correct domain.

#### 5.1 Verify Domain in HTTPRoute

Check `manifests/httproute.yaml`:
```yaml
hostnames:
- "apidatacapture.store"
```

#### 5.2 Verify Domain in Certificate

Check `manifests/certificate.yaml`:
```yaml
dnsNames:
- apidatacapture.store
- www.apidatacapture.store
```

#### 5.3 Verify Email in ClusterIssuer

Check `manifests/cert-manager-issuer.yaml`:
```yaml
email: demolasobaki@gmail.com  # Update if needed
```

---

### Step 6: Deploy Application with Gateway API

Now deploy all resources using kustomize:

```bash
# Navigate to manifests directory
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Preview what will be deployed
kubectl kustomize .

# Deploy all resources
kubectl apply -k .
```

**Verify deployment:**
```bash
# Check namespace
kubectl get namespace ai-data-capture

# Check all resources
kubectl -n ai-data-capture get all

# Check Gateway
kubectl -n ai-data-capture get gateway

# Check HTTPRoute
kubectl -n ai-data-capture get httproute

# Check Certificate
kubectl -n ai-data-capture get certificate

# Check ClusterIssuer
kubectl get clusterissuer
```

---

### Step 7: Monitor Certificate Issuance

cert-manager will automatically request a certificate from Let's Encrypt.

#### 7.1 Check Certificate Status

```bash
# Watch certificate status
kubectl -n ai-data-capture get certificate -w

# Check certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

**Expected progression:**
1. `Ready: False` - Certificate requested
2. `Ready: True` - Certificate issued

#### 7.2 Check CertificateRequest

```bash
# List certificate requests
kubectl -n ai-data-capture get certificaterequest

# Describe the request
kubectl -n ai-data-capture describe certificaterequest
```

#### 7.3 Check cert-manager Logs

If certificate issuance fails:
```bash
# Check cert-manager controller logs
kubectl -n cert-manager logs -l app=cert-manager --tail=100

# Check cert-manager webhook logs
kubectl -n cert-manager logs -l app=webhook --tail=100
```

#### 7.4 Verify TLS Secret Created

Once certificate is issued:
```bash
# Check if secret was created
kubectl -n ai-data-capture get secret apidatacapture-store-tls-secret

# View certificate details
kubectl -n ai-data-capture get secret apidatacapture-store-tls-secret -o yaml
```

---

### Step 8: Configure Gateway Service

The Gateway needs to be accessible from the internet.

#### 8.1 Check Gateway Service

```bash
# Get Gateway service
kubectl -n ai-data-capture get svc

# Describe Gateway service
kubectl -n ai-data-capture describe svc
```

#### 8.2 Expose Gateway via NodePort

Your `gateway.yaml` already has:
```yaml
annotations:
  io.cilium/service-type: "NodePort"
```

Check the NodePort assignments:
```bash
# Get NodePort for Gateway
kubectl -n ai-data-capture get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway
```

#### 8.3 Configure AWS Security Group

Ensure your EC2 instances' security group allows:
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
