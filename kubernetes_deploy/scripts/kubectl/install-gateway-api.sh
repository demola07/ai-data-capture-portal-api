#!/bin/bash

# Install Gateway API CRDs
# This script installs the Gateway API Custom Resource Definitions (CRDs)
# Required for Gateway API functionality with Cilium

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

echo "🚀 Installing Gateway API CRDs for Kubernetes"
echo "=============================================="

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    print_info "Please ensure kubectl is configured and cluster is accessible"
    exit 1
fi

print_status "Connected to Kubernetes cluster"

# Check if Gateway API CRDs are already installed
print_info "Checking for existing Gateway API CRDs..."

if kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null; then
    print_warning "Gateway API CRDs are already installed"
    
    echo
    echo "📋 Installed Gateway API CRDs:"
    kubectl get crd | grep gateway.networking.k8s.io
    
    echo
    print_info "To reinstall, first remove existing CRDs:"
    print_info "kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml"
    exit 0
fi

# Install Gateway API CRDs
print_info "Installing Gateway API CRDs (standard channel)..."
print_info "Using Gateway API v1.0.0 (stable release)"

kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

print_info "Waiting for CRDs to be established..."

# Wait for each CRD to be ready
kubectl wait --for condition=established --timeout=60s crd/gateways.gateway.networking.k8s.io
kubectl wait --for condition=established --timeout=60s crd/httproutes.gateway.networking.k8s.io
kubectl wait --for condition=established --timeout=60s crd/referencegrants.gateway.networking.k8s.io

print_status "Gateway API CRDs installed successfully!"

echo
echo "📋 Installed Gateway API CRDs:"
kubectl get crd | grep gateway.networking.k8s.io

echo
echo "🔍 Verify installation:"
echo "kubectl get crd | grep gateway"
echo "kubectl api-resources | grep gateway"

echo
print_status "Gateway API is now ready for use with Cilium!"
print_info "You can now deploy your Gateway and HTTPRoute manifests"

echo
echo "📚 Next steps:"
echo "1. Deploy your application manifests: kubectl apply -k kubernetes_deploy/manifests/"
echo "2. Or run the full deployment script: ./kubernetes_deploy/scripts/deploy-with-tls.sh"
