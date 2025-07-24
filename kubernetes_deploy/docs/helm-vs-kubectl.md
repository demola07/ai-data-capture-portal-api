# Helm vs kubectl: Deployment Comparison

This document compares the two approaches for deploying infrastructure components and provides recommendations.

## 📊 Comparison Table

| Feature | kubectl Direct | Helm Charts | Winner |
|---------|---------------|-------------|---------|
| **Package Management** | ❌ Manual | ✅ Automated | Helm |
| **Version Control** | ❌ Hard to track | ✅ Easy versioning | Helm |
| **Upgrades** | ❌ Manual process | ✅ `helm upgrade` | Helm |
| **Rollbacks** | ❌ Very difficult | ✅ `helm rollback` | Helm |
| **Configuration** | ❌ Scattered files | ✅ Values files | Helm |
| **Dependencies** | ❌ Manual ordering | ✅ Automatic | Helm |
| **Simplicity** | ✅ Direct commands | ❌ More complex | kubectl |
| **Learning Curve** | ✅ Lower | ❌ Higher | kubectl |
| **Production Ready** | ❌ Not ideal | ✅ Industry standard | Helm |
| **CI/CD Integration** | ❌ Harder | ✅ Excellent | Helm |

## 🎯 Recommendations

### **For Production: Use Helm** ✅
- **Better package management**
- **Easier upgrades and rollbacks**
- **Industry standard approach**
- **Better CI/CD integration**

### **For Development/Testing: Either works**
- **kubectl**: Faster for quick tests
- **Helm**: Better for consistent environments

## 🚀 Available Deployment Options

### **Option 1: Helm-based (Recommended)**
```bash
# Complete Helm-based deployment
./kubernetes_deploy/scripts/deploy-with-helm.sh

# Or infrastructure only
./kubernetes_deploy/scripts/install-with-helm.sh
```

### **Option 2: kubectl-based (Simple)**
```bash
# Original kubectl-based deployment
./kubernetes_deploy/scripts/deploy-with-tls.sh

# Or Gateway API only
./kubernetes_deploy/scripts/install-gateway-api.sh
```

## 🔧 Helm Benefits in Detail

### **1. Package Management**
```bash
# Easy to see what's installed
helm list --all-namespaces

# Easy to check versions
helm list -o yaml
```

### **2. Configuration Management**
```yaml
# cert-manager-values.yaml
replicaCount: 3
resources:
  limits:
    memory: 256Mi
prometheus:
  enabled: true
```

### **3. Upgrades**
```bash
# Upgrade cert-manager
helm upgrade cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --values kubernetes_deploy/helm/cert-manager-values.yaml

# Check upgrade history
helm history cert-manager -n cert-manager
```

### **4. Rollbacks**
```bash
# Rollback to previous version
helm rollback cert-manager 1 -n cert-manager

# Rollback to specific revision
helm rollback cert-manager 2 -n cert-manager
```

### **5. Environment Management**
```bash
# Different values for different environments
helm install cert-manager jetstack/cert-manager \
  --values values-production.yaml

helm install cert-manager jetstack/cert-manager \
  --values values-staging.yaml
```

## 📦 Helm Chart Details

### **cert-manager Helm Chart**
- **Repository**: `jetstack/cert-manager`
- **Version**: `v1.13.0`
- **Features**: CRD installation, monitoring, security contexts
- **Configuration**: Custom values file provided

### **Gateway API Helm Chart**
- **Repository**: `gateway-api/gateway-api`
- **Version**: `1.0.0`
- **Features**: CRD installation, version management
- **Configuration**: Standard installation

## 🔍 Migration Path

### **From kubectl to Helm**
If you've already deployed with kubectl:

```bash
# 1. Uninstall kubectl-based installations
kubectl delete -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# 2. Install with Helm
./kubernetes_deploy/scripts/install-with-helm.sh

# 3. Deploy application
kubectl apply -k kubernetes_deploy/manifests/
```

### **Adopting Existing Resources**
```bash
# Adopt existing cert-manager installation
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --set installCRDs=false \
  --dry-run
```

## 🏗️ CI/CD Integration

### **GitOps with Helm**
```yaml
# .github/workflows/deploy.yml
- name: Deploy with Helm
  run: |
    helm upgrade --install cert-manager jetstack/cert-manager \
      --namespace cert-manager \
      --values helm/cert-manager-values.yaml \
      --wait
```

### **ArgoCD Integration**
```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cert-manager
spec:
  source:
    repoURL: https://charts.jetstack.io
    chart: cert-manager
    targetRevision: v1.13.0
    helm:
      valueFiles:
      - values.yaml
```

## 🎯 Best Practices

### **Helm Best Practices**
- ✅ **Use values files** for configuration
- ✅ **Pin chart versions** in production
- ✅ **Test upgrades** in staging first
- ✅ **Monitor releases** with `helm list`
- ✅ **Backup values files** in Git

### **kubectl Best Practices**
- ✅ **Pin resource versions** (avoid `latest`)
- ✅ **Use kustomize** for configuration management
- ✅ **Document manual steps** thoroughly
- ✅ **Create upgrade scripts** for consistency

## 🚨 Troubleshooting

### **Helm Issues**
```bash
# Check Helm release status
helm status cert-manager -n cert-manager

# Debug failed installation
helm install cert-manager jetstack/cert-manager --debug --dry-run

# Check Helm history
helm history cert-manager -n cert-manager
```

### **Migration Issues**
```bash
# Check for resource conflicts
kubectl get all -n cert-manager
kubectl get crd | grep cert-manager

# Force cleanup if needed
kubectl delete namespace cert-manager --force --grace-period=0
```

## 📋 Summary

### **Choose Helm if:**
- ✅ **Production deployment**
- ✅ **Multiple environments**
- ✅ **Team collaboration**
- ✅ **CI/CD integration**
- ✅ **Long-term maintenance**

### **Choose kubectl if:**
- ✅ **Quick testing**
- ✅ **Learning/development**
- ✅ **Simple one-off deployments**
- ✅ **Minimal tooling requirements**

**Recommendation**: Use Helm for your production deployment of the AI Data Capture Portal! 🚀
