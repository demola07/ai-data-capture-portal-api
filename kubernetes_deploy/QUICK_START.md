# Quick Start Guide - Gateway API with TLS

Fast-track guide to deploy your application with Gateway API and automatic TLS.

## ⚡ Prerequisites Checklist

Before you begin, ensure you have:

- [x] Self-managed Kubernetes cluster running on AWS
- [x] `kubectl` configured and connected to your cluster
- [x] `helm` installed (v3.x)
- [x] Domain name registered (apidatacapture.store)
- [x] Application currently accessible via NodePort
- [x] AWS Security Group allows ports 80, 443

## 🚀 Quick Deployment (Automated)

### Option 1: One-Command Deployment

Run the automated deployment script:

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/scripts
./deploy-gateway-tls.sh
```

This script will:
1. ✅ Install Gateway API CRDs
2. ✅ Configure Cilium for Gateway API
3. ✅ Install cert-manager
4. ✅ Check DNS configuration
5. ✅ Deploy your application
6. ✅ Set up automatic TLS certificates

**Estimated time:** 5-10 minutes

---

## 📋 Manual Deployment (Step-by-Step)

If you prefer manual control, follow these steps:

### Step 1: Install Gateway API CRDs (1 min)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
```

Verify:
```bash
kubectl get crd | grep gateway
```

### Step 2: Enable Gateway API in Cilium (2 min)

```bash
# Enable Gateway API
kubectl -n kube-system patch configmap cilium-config --type merge -p '{"data":{"enable-gateway-api":"true"}}'

# Restart Cilium
kubectl -n kube-system rollout restart deployment/cilium-operator
kubectl -n kube-system rollout restart daemonset/cilium

# Wait for Cilium to be ready
kubectl -n kube-system wait --for=condition=ready pod -l k8s-app=cilium --timeout=180s
```

### Step 3: Install cert-manager (3 min)

```bash
# Add Helm repo
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
kubectl create namespace cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.0 \
  --set installCRDs=true

# Wait for cert-manager to be ready
kubectl -n cert-manager wait --for=condition=ready pod --all --timeout=300s
```

### Step 4: Configure DNS (5-60 min)

Get your cluster's public IP:
```bash
kubectl get nodes -o wide
```

Configure DNS A records at your DNS provider:
```
Type: A
Name: @
Value: <YOUR_CLUSTER_PUBLIC_IP>

Type: A  
Name: www
Value: <YOUR_CLUSTER_PUBLIC_IP>
```

Verify DNS:
```bash
dig apidatacapture.store +short
```

**⏰ Wait for DNS to propagate** (5-60 minutes)

### Step 5: Deploy Application (2 min)

```bash
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Apply all manifests
kubectl apply -k .

# Wait for deployment
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

### Step 6: Verify Certificate Issuance (2-5 min)

```bash
# Watch certificate status
kubectl -n ai-data-capture get certificate -w

# Check certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls
```

Wait for `Ready: True`

---

## ✅ Verification

After deployment, verify everything works:

### 1. Check All Resources

```bash
# Check pods
kubectl -n ai-data-capture get pods

# Check gateway
kubectl -n ai-data-capture get gateway

# Check certificate
kubectl -n ai-data-capture get certificate
```

### 2. Test HTTP to HTTPS Redirect

```bash
curl -I http://apidatacapture.store
```

Expected: `301 Moved Permanently` → HTTPS

### 3. Test HTTPS Access

```bash
curl -I https://apidatacapture.store
```

Expected: `200 OK` with valid TLS

### 4. Test API Endpoints

```bash
# Health check
curl https://apidatacapture.store/health

# API documentation
curl https://apidatacapture.store/docs
```

### 5. Verify TLS Certificate

```bash
echo | openssl s_client -servername apidatacapture.store -connect apidatacapture.store:443 2>/dev/null | openssl x509 -noout -dates
```

---

## 🐛 Common Issues

### Issue: Certificate Not Issuing

**Symptom:** Certificate stays in `Ready: False`

**Solution:**
```bash
# Check certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls

# Check challenges
kubectl -n ai-data-capture get challenges

# Check cert-manager logs
kubectl -n cert-manager logs -l app=cert-manager --tail=50
```

**Common causes:**
- DNS not propagated yet (wait longer)
- Port 80 blocked (check AWS Security Group)
- Gateway not ready (check gateway status)

### Issue: Gateway Not Ready

**Symptom:** Gateway shows `Programmed: False`

**Solution:**
```bash
# Check gateway status
kubectl -n ai-data-capture describe gateway ai-data-capture-gateway

# Check Cilium logs
kubectl -n kube-system logs -l app.kubernetes.io/name=cilium-operator | grep -i gateway
```

### Issue: DNS Not Resolving

**Symptom:** `dig apidatacapture.store` returns no results

**Solution:**
- Wait for DNS propagation (can take up to 48 hours, usually 5-60 minutes)
- Verify DNS records at your provider
- Check from different DNS servers: `dig @8.8.8.8 apidatacapture.store`

### Issue: 502 Bad Gateway

**Symptom:** HTTPS works but returns 502 error

**Solution:**
```bash
# Check pod status
kubectl -n ai-data-capture get pods

# Check pod logs
kubectl -n ai-data-capture logs -l app=ai-data-capture-api

# Check service endpoints
kubectl -n ai-data-capture get endpoints
```

---

## 📊 Monitoring Commands

### Check Application Status

```bash
# All resources
kubectl -n ai-data-capture get all

# Pod logs (follow)
kubectl -n ai-data-capture logs -l app=ai-data-capture-api -f

# Recent events
kubectl -n ai-data-capture get events --sort-by='.lastTimestamp' | tail -20
```

### Check Gateway Status

```bash
# Gateway details
kubectl -n ai-data-capture get gateway -o yaml

# HTTPRoute details
kubectl -n ai-data-capture get httproute -o yaml
```

### Check Certificate Status

```bash
# Certificate status
kubectl -n ai-data-capture get certificate

# Certificate details
kubectl -n ai-data-capture describe certificate apidatacapture-store-tls

# TLS secret
kubectl -n ai-data-capture get secret apidatacapture-store-tls-secret
```

---

## 🎯 What You Get

After successful deployment:

### ✅ Automatic TLS
- Free SSL/TLS certificates from Let's Encrypt
- Auto-renewal (90 days validity, renews at 75 days)
- Valid for `apidatacapture.store` and `www.apidatacapture.store`

### ✅ Gateway API
- Modern Kubernetes ingress (successor to Ingress)
- HTTP to HTTPS redirect
- Advanced routing capabilities
- Request/response header manipulation

### ✅ Production Features
- 3 replicas for high availability
- Health checks (liveness, readiness, startup)
- Auto-scaling (HPA configured for 3-10 replicas)
- Pod disruption budget
- Network policies
- Cilium L7 policies and rate limiting

### ✅ Security
- TLS 1.2+ encryption
- Security headers (X-Frame-Options, CSP, etc.)
- Non-root container
- Read-only root filesystem
- Network isolation

---

## 🔄 Update Application

To update your application:

```bash
# Update image tag in kustomization.yaml
cd /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Edit kustomization.yaml and change image tag
# Then apply changes
kubectl apply -k .

# Watch rollout
kubectl -n ai-data-capture rollout status deployment/ai-data-capture-api
```

---

## 🗑️ Cleanup

To remove everything:

```bash
# Delete application
kubectl delete -k /Users/ademolaadesina/projects/ai-data-capture-portal-api/kubernetes_deploy/manifests

# Delete cert-manager (optional)
helm uninstall cert-manager -n cert-manager
kubectl delete namespace cert-manager

# Delete Gateway API CRDs (optional)
kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
```

---

## 📚 Next Steps

1. **Set up monitoring** - Add Prometheus/Grafana
2. **Configure backups** - Backup secrets and data
3. **Set up CI/CD** - Automate deployments
4. **Add custom domain** - Configure additional domains
5. **Enable logging** - Centralized logging with ELK/Loki

---

## 🆘 Need Help?

- **Detailed Guide:** See [GATEWAY_TLS_SETUP.md](./GATEWAY_TLS_SETUP.md)
- **Deployment Guide:** See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Check Logs:** `kubectl -n ai-data-capture logs -l app=ai-data-capture-api`
- **Check Events:** `kubectl -n ai-data-capture get events --sort-by='.lastTimestamp'`

---

## 📞 Support Resources

- [Gateway API Docs](https://gateway-api.sigs.k8s.io/)
- [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/)
- [cert-manager Docs](https://cert-manager.io/docs/)
- [Let's Encrypt Docs](https://letsencrypt.org/docs/)

---

**🎉 Happy Deploying!**
