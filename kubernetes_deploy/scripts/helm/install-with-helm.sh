#!/bin/bash

# Install infrastructure components using Helm
# This is the recommended approach for production deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Configuration
EMAIL="demolasobaki@gmail.com"
DOMAIN="apidatacapture.store"

echo "🚀 Installing Infrastructure Components with Helm"
echo "================================================="

# Check prerequisites
print_info "Checking prerequisites..."

# Check helm
if ! command -v helm &> /dev/null; then
    print_error "Helm is not installed"
    print_info "Install Helm: https://helm.sh/docs/intro/install/"
    exit 1
fi

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

print_status "Prerequisites check passed"

# Step 1: Add Helm repositories
echo
echo "📦 Step 1: Adding Helm repositories..."

print_info "Adding cert-manager repository..."
helm repo add jetstack https://charts.jetstack.io

print_info "Updating Helm repositories..."
helm repo update

print_status "Helm repositories added and updated"

# Step 2: Install Gateway API CRDs
echo
echo "🌐 Step 2: Installing Gateway API CRDs..."

if kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null; then
    print_warning "Gateway API CRDs already installed, skipping..."
else
    print_info "Installing Gateway API CRDs directly with kubectl..."
    print_info "Using Gateway API v1.0.0 (stable release)"
    
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
    
    print_info "Waiting for Gateway API CRDs to be ready..."
    kubectl wait --for condition=established --timeout=60s crd/gateways.gateway.networking.k8s.io
    kubectl wait --for condition=established --timeout=60s crd/httproutes.gateway.networking.k8s.io
    kubectl wait --for condition=established --timeout=60s crd/referencegrants.gateway.networking.k8s.io
    
    print_status "Gateway API CRDs installed successfully"
fi

# Step 3: Install cert-manager
echo
echo "🔐 Step 3: Installing cert-manager..."

if helm list -n cert-manager | grep -q cert-manager; then
    print_warning "cert-manager already installed, skipping..."
else
    print_info "Creating cert-manager namespace..."
    kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
    
    print_info "Installing cert-manager with Helm..."
    helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version v1.13.0 \
        --set installCRDs=true \
        --set global.leaderElection.namespace=cert-manager \
        --set prometheus.enabled=true \
        --set webhook.timeoutSeconds=30
    
    print_info "Waiting for cert-manager to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-cainjector -n cert-manager
    
    print_status "cert-manager installed successfully"
fi

# Step 4: Verify installations
echo
echo "🔍 Step 4: Verifying installations..."

print_info "Checking Gateway API CRDs..."
kubectl get crd | grep gateway.networking.k8s.io

print_info "Checking cert-manager pods..."
kubectl get pods -n cert-manager

print_info "Checking Helm releases..."
helm list --all-namespaces

print_status "All components installed and verified successfully!"

echo
echo "📋 Installation Summary:"
echo "========================"
echo "✅ Gateway API CRDs: Installed via kubectl (official method)"
echo "✅ cert-manager: Installed via Helm"
echo
echo "🔧 Helm Management Commands:"
echo "# List all releases"
echo "helm list --all-namespaces"
echo
echo "# Upgrade cert-manager"
echo "helm upgrade cert-manager jetstack/cert-manager -n cert-manager"
echo
echo "# Rollback if needed"
echo "helm rollback cert-manager 1 -n cert-manager"
echo
echo "# Uninstall (if needed)"
echo "helm uninstall cert-manager -n cert-manager"
echo "kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml"
echo
echo "🚀 Next steps:"
echo "1. Deploy your application: kubectl apply -k kubernetes_deploy/manifests/"
echo "2. Or run: ./kubernetes_deploy/scripts/deploy-with-tls.sh"
