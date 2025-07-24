# Gateway API CRDs Installation Guide

Gateway API is **not** part of core Kubernetes - it's a separate project that requires installing Custom Resource Definitions (CRDs).

## 🤔 Why Gateway API CRDs Are Needed

### What is Gateway API?
- **Next-generation ingress** for Kubernetes
- **Successor to Ingress API** with more features
- **Role-based configuration** (Infrastructure vs Application teams)
- **Advanced traffic management** (routing, load balancing, TLS)

### Why Not Built-in?
- **Separate project** from Kubernetes core
- **Faster development cycle** than core Kubernetes
- **Optional feature** - not all clusters need it
- **Backward compatibility** - doesn't break existing Ingress

## 🔍 Check if Gateway API CRDs Are Installed

### Quick Check:
```bash
# Check for Gateway API CRDs
kubectl get crd | grep gateway

# Should show something like:
# gateways.gateway.networking.k8s.io
# httproutes.gateway.networking.k8s.io
# referencegrants.gateway.networking.k8s.io
```

### Detailed Check:
```bash
# Check specific CRDs
kubectl get crd gateways.gateway.networking.k8s.io
kubectl get crd httproutes.gateway.networking.k8s.io
kubectl get crd referencegrants.gateway.networking.k8s.io

# Check API resources
kubectl api-resources | grep gateway
```

### If Not Installed:
```bash
# You'll see:
ubuntu@master:~$ kubectl get crd | grep gateway
ubuntu@master:~$ 
# (empty output means not installed)
```

## 🚀 Installation Methods

### Method 1: Automatic (Recommended)
Your deployment script now handles this automatically:
```bash
./kubernetes_deploy/scripts/deploy-with-tls.sh
```

### Method 2: Manual Installation
```bash
# Run the dedicated script
./kubernetes_deploy/scripts/install-gateway-api.sh
```

### Method 3: Direct kubectl
```bash
# Install Gateway API CRDs directly
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Wait for CRDs to be ready
kubectl wait --for condition=established --timeout=60s crd/gateways.gateway.networking.k8s.io
```

## 📦 What Gets Installed

### Core CRDs:
- **`gateways.gateway.networking.k8s.io`** - Gateway resources
- **`httproutes.gateway.networking.k8s.io`** - HTTP routing rules
- **`referencegrants.gateway.networking.k8s.io`** - Cross-namespace references

### Additional CRDs (Standard Channel):
- **`grpcroutes.gateway.networking.k8s.io`** - gRPC routing
- **`tlsroutes.gateway.networking.k8s.io`** - TLS routing
- **`tcproutes.gateway.networking.k8s.io`** - TCP routing
- **`udproutes.gateway.networking.k8s.io`** - UDP routing

## 🔧 Verification

### After Installation:
```bash
# Check CRDs are installed
kubectl get crd | grep gateway

# Expected output:
gateways.gateway.networking.k8s.io          2024-01-24T00:30:00Z
httproutes.gateway.networking.k8s.io        2024-01-24T00:30:00Z
referencegrants.gateway.networking.k8s.io   2024-01-24T00:30:00Z
```

### Test Gateway API:
```bash
# Check if you can create Gateway resources
kubectl explain gateway
kubectl explain httproute
kubectl explain referencegrant
```

## 🏗️ Integration with Cilium

### Why Cilium + Gateway API?
- **Cilium Gateway API support** - Native implementation
- **High performance** - eBPF-based data plane
- **Advanced features** - L7 policies, observability
- **No external load balancer** needed

### Cilium Gateway Class:
Your manifests use the Cilium gateway class:
```yaml
# gateway.yaml
spec:
  gatewayClassName: cilium
```

### Verify Cilium Gateway Support:
```bash
# Check if Cilium supports Gateway API
kubectl get gatewayclass cilium

# Should show:
NAME     CONTROLLER                     ACCEPTED   AGE
cilium   io.cilium/gateway-controller   True       1h
```

## 🚨 Troubleshooting

### CRDs Not Installing:
```bash
# Check cluster connectivity
kubectl cluster-info

# Check permissions
kubectl auth can-i create customresourcedefinitions

# Manual download and apply
curl -L https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml | kubectl apply -f -
```

### CRDs Stuck in Installing:
```bash
# Check CRD status
kubectl get crd gateways.gateway.networking.k8s.io -o yaml

# Check events
kubectl get events --all-namespaces | grep gateway

# Force delete and reinstall
kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
```

### Gateway Resources Not Working:
```bash
# Check if Cilium supports Gateway API
kubectl get gatewayclass

# Check Cilium pods
kubectl get pods -n kube-system | grep cilium

# Check Cilium configuration
kubectl get configmap cilium-config -n kube-system -o yaml | grep -i gateway
```

## 📋 Version Compatibility

### Gateway API Versions:
- **v1.0.0** - Stable release (recommended)
- **v0.8.x** - Beta releases
- **v0.7.x** - Alpha releases

### Cilium Compatibility:
- **Cilium 1.14+** - Full Gateway API v1.0.0 support
- **Cilium 1.13** - Gateway API v0.8.x support
- **Cilium 1.12** - Gateway API v0.7.x support

### Check Your Versions:
```bash
# Check Cilium version
kubectl get pods -n kube-system -l k8s-app=cilium -o jsonpath='{.items[0].spec.containers[0].image}'

# Check Gateway API version
kubectl get crd gateways.gateway.networking.k8s.io -o jsonpath='{.spec.versions[0].name}'
```

## 🎯 Best Practices

### Installation:
- ✅ **Use stable releases** (v1.0.0+)
- ✅ **Install before deploying** Gateway resources
- ✅ **Verify installation** before proceeding
- ✅ **Use automation** (scripts) for consistency

### Management:
- ✅ **Monitor CRD health** regularly
- ✅ **Plan upgrades** carefully
- ✅ **Test in staging** before production
- ✅ **Backup configurations** before changes

Your Gateway API CRDs are now properly managed and will be installed automatically! 🚀✅
