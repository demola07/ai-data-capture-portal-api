# Kubernetes Cluster Setup and Deployment Scripts

Complete automation scripts for setting up self-managed Kubernetes clusters and deploying applications.

## 📁 Directory Structure

```
scripts/
├── setup-k8s-control-plane.sh  # 🆕 Control plane setup automation
├── setup-k8s-worker-node.sh    # 🆕 Worker node setup automation
├── validate-k8s-setup.sh       # 🆕 Pre-installation validation
├── k8s-utilities.sh            # 🆕 Cluster management utilities
├── helm/                       # Helm-based deployment (RECOMMENDED)
│   ├── deploy-with-helm.sh        # Complete Helm deployment
│   └── install-with-helm.sh       # Infrastructure only (cert-manager, Gateway API)
├── kubectl/                    # kubectl-based deployment (Simple)
│   ├── deploy-with-tls.sh         # Complete kubectl deployment
│   └── install-gateway-api.sh     # Gateway API CRDs only
├── utilities/                  # Helper scripts
│   ├── encode-secrets.sh          # Secret encoding utility
│   └── config-example.py          # Configuration example
└── README.md                  # This file
```

## 🏗️ Kubernetes Cluster Setup (NEW)

### **Step 1: Pre-Installation Validation**
```bash
# Validate your system before installation
sudo ./validate-k8s-setup.sh
```

### **Step 2: Setup Control Plane Node**
```bash
# Setup the first master node
sudo ./setup-k8s-control-plane.sh [pod-network-cidr] [apiserver-advertise-address]

# Examples:
sudo ./setup-k8s-control-plane.sh                    # Uses default 10.217.0.0/16
sudo ./setup-k8s-control-plane.sh 10.244.0.0/16     # Custom pod network
sudo ./setup-k8s-control-plane.sh 10.244.0.0/16 10.0.1.100  # With API server IP
```

### **Step 3: Setup Worker Nodes**
```bash
# On each worker node, use the join command from control plane setup
sudo ./setup-k8s-worker-node.sh "kubeadm join 10.0.1.100:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abcd1234..."
```

### **Step 4: Cluster Management**
```bash
# Generate new join tokens
./k8s-utilities.sh generate-join-token

# Check cluster status
./k8s-utilities.sh cluster-info

# Troubleshoot issues
./k8s-utilities.sh troubleshoot

# Reset a node (if needed)
sudo ./k8s-utilities.sh reset-node
```

## 🚀 Application Deployment Methods

### **Method 1: Helm-based (RECOMMENDED for Production)**

#### Complete Deployment:
```bash
cd kubernetes_deploy/scripts/helm/
./deploy-with-helm.sh
```

#### Infrastructure Only:
```bash
cd kubernetes_deploy/scripts/helm/
./install-with-helm.sh
```

**Features:**
- ✅ **Package management** - Easy upgrades and rollbacks
- ✅ **Configuration management** - Values files for different environments
- ✅ **Production-ready** - Industry standard approach
- ✅ **No duplication** - Uses existing manifests

### **Method 2: kubectl-based (Simple)**

#### Complete Deployment:
```bash
cd kubernetes_deploy/scripts/kubectl/
./deploy-with-tls.sh
```

#### Gateway API CRDs Only:
```bash
cd kubernetes_deploy/scripts/kubectl/
./install-gateway-api.sh
```

**Features:**
- ✅ **Simple** - Direct kubectl commands
- ✅ **Fast** - No additional tooling required
- ✅ **Educational** - Easy to understand what's happening

## 🔧 What Each Script Does

### **Helm Scripts**

#### `helm/deploy-with-helm.sh`
- Installs infrastructure with Helm (cert-manager, Gateway API)
- Creates application namespace
- **Uses existing `cert-manager-issuer.yaml`** (no duplication)
- Deploys application manifests
- Configures DNS and waits for certificates
- **Complete end-to-end deployment**

#### `helm/install-with-helm.sh`
- Adds Helm repositories
- Installs Gateway API CRDs with Helm
- Installs cert-manager with Helm
- **Infrastructure components only**

### **kubectl Scripts**

#### `kubectl/deploy-with-tls.sh`
- Installs Gateway API CRDs directly
- Installs cert-manager directly
- Updates ClusterIssuer with email
- Deploys application manifests
- Configures DNS and waits for certificates
- **Complete end-to-end deployment**

#### `kubectl/install-gateway-api.sh`
- Installs Gateway API CRDs only
- **Standalone utility script**
- Can be used independently

### **Utility Scripts**

#### `utilities/encode-secrets.sh`
- Encodes secrets for Kubernetes
- Interactive secret creation
- **Helper utility**

#### `utilities/config-example.py`
- Configuration examples
- **Reference only**

## 🎯 Which Method Should You Use?

### **Choose Helm if:**
- ✅ **Production deployment**
- ✅ **Multiple environments** (staging, production)
- ✅ **Team collaboration**
- ✅ **Long-term maintenance**
- ✅ **CI/CD integration**

### **Choose kubectl if:**
- ✅ **Quick testing**
- ✅ **Learning Kubernetes**
- ✅ **Simple one-off deployments**
- ✅ **Minimal tooling requirements**

## 🔍 Key Differences

| Feature | kubectl Method | Helm Method |
|---------|---------------|-------------|
| **Complexity** | Simple | More complex |
| **Upgrades** | Manual | `helm upgrade` |
| **Rollbacks** | Difficult | `helm rollback` |
| **Configuration** | Hardcoded | Values files |
| **Production Ready** | Basic | Advanced |
| **Duplication** | Some inline configs | Uses existing manifests |

## 🚨 Important Notes

### **No More Duplication**
- **Helm method now uses existing `cert-manager-issuer.yaml`**
- **No more inline ClusterIssuer creation**
- **Single source of truth for configurations**

### **Script Locations**
- **All scripts must be run from their respective directories**
- **Path references are relative to script location**
- **Scripts call each other correctly**

### **Dependencies**
- **Helm method requires Helm to be installed**
- **kubectl method only requires kubectl**
- **Both methods require cluster access**

## 🔧 Usage Examples

### **Production Deployment (Helm)**
```bash
# Navigate to helm directory
cd kubernetes_deploy/scripts/helm/

# Run complete deployment
./deploy-with-helm.sh

# Check Helm releases
helm list --all-namespaces

# Upgrade if needed
helm upgrade cert-manager jetstack/cert-manager -n cert-manager
```

### **Development/Testing (kubectl)**
```bash
# Navigate to kubectl directory
cd kubernetes_deploy/scripts/kubectl/

# Install Gateway API CRDs only
./install-gateway-api.sh

# Or run complete deployment
./deploy-with-tls.sh
```

### **Utilities**
```bash
# Navigate to utilities directory
cd kubernetes_deploy/scripts/utilities/

# Encode secrets
./encode-secrets.sh
```

## 📋 Migration Guide

### **From Old Structure**
If you were using the old scripts:

1. **For Helm deployment**: Use `helm/deploy-with-helm.sh`
2. **For kubectl deployment**: Use `kubectl/deploy-with-tls.sh`
3. **For utilities**: Use `utilities/` scripts

### **Script Mapping**
- `deploy-with-helm.sh` → `helm/deploy-with-helm.sh`
- `install-with-helm.sh` → `helm/install-with-helm.sh`
- `deploy-with-tls.sh` → `kubectl/deploy-with-tls.sh`
- `install-gateway-api.sh` → `kubectl/install-gateway-api.sh`
- `encode-secrets.sh` → `utilities/encode-secrets.sh`

Your scripts are now properly organized and duplication-free! 🚀✅
