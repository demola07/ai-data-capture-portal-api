#!/bin/bash

#############################################################################
# AI Data Capture Portal - Gateway API with TLS Deployment Script
#############################################################################
# This script automates the deployment of the application with Gateway API
# and automatic TLS certificate management via cert-manager.
#
# Usage: ./deploy-gateway-tls.sh [OPTIONS]
#
# Options:
#   --skip-crds         Skip Gateway API CRDs installation
#   --skip-cert-manager Skip cert-manager installation
#   --dry-run           Show what would be deployed without applying
#   --help              Show this help message
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ai-data-capture"
DOMAIN="apidatacapture.store"
CERT_MANAGER_VERSION="v1.13.0"
GATEWAY_API_VERSION="v1.0.0"
MANIFESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../manifests" && pwd)"

# Parse command line arguments
SKIP_CRDS=false
SKIP_CERT_MANAGER=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-crds)
      SKIP_CRDS=true
      shift
      ;;
    --skip-cert-manager)
      SKIP_CERT_MANAGER=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help)
      grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

#############################################################################
# Helper Functions
#############################################################################

log_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
  echo -e "${RED}❌ $1${NC}"
}

log_step() {
  echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}$1${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    log_error "$1 is not installed. Please install it first."
    exit 1
  fi
}

wait_for_pods() {
  local namespace=$1
  local label=$2
  local timeout=${3:-300}
  
  log_info "Waiting for pods in namespace $namespace with label $label to be ready..."
  if kubectl -n "$namespace" wait --for=condition=ready pod -l "$label" --timeout="${timeout}s" 2>/dev/null; then
    log_success "Pods are ready"
    return 0
  else
    log_warning "Pods did not become ready within ${timeout}s"
    return 1
  fi
}

#############################################################################
# Pre-flight Checks
#############################################################################

log_step "Step 0: Pre-flight Checks"

# Check required commands
log_info "Checking required tools..."
check_command kubectl
check_command helm
check_command curl
log_success "All required tools are installed"

# Check cluster connectivity
log_info "Checking Kubernetes cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
  log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
  exit 1
fi
log_success "Connected to Kubernetes cluster"

# Get cluster info
CLUSTER_VERSION=$(kubectl version --short 2>/dev/null | grep "Server Version" | awk '{print $3}')
log_info "Cluster version: $CLUSTER_VERSION"

#############################################################################
# Step 1: Install Gateway API CRDs
#############################################################################

if [ "$SKIP_CRDS" = false ]; then
  log_step "Step 1: Installing Gateway API CRDs"
  
  # Check if CRDs already exist
  if kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null; then
    log_warning "Gateway API CRDs already installed"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      log_info "Skipping Gateway API CRDs installation"
    else
      log_info "Installing Gateway API CRDs version $GATEWAY_API_VERSION..."
      kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml"
      log_success "Gateway API CRDs installed"
    fi
  else
    log_info "Installing Gateway API CRDs version $GATEWAY_API_VERSION..."
    kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml"
    log_success "Gateway API CRDs installed"
  fi
  
  # Verify CRDs
  log_info "Verifying Gateway API CRDs..."
  EXPECTED_CRDS=("gatewayclasses.gateway.networking.k8s.io" "gateways.gateway.networking.k8s.io" "httproutes.gateway.networking.k8s.io" "referencegrants.gateway.networking.k8s.io")
  for crd in "${EXPECTED_CRDS[@]}"; do
    if kubectl get crd "$crd" &> /dev/null; then
      log_success "CRD $crd found"
    else
      log_error "CRD $crd not found"
      exit 1
    fi
  done
else
  log_step "Step 1: Skipping Gateway API CRDs installation"
fi

#############################################################################
# Step 2: Configure Cilium for Gateway API
#############################################################################

log_step "Step 2: Configuring Cilium for Gateway API"

# Check if Cilium is installed
if ! kubectl -n kube-system get deployment cilium-operator &> /dev/null; then
  log_error "Cilium is not installed. Please install Cilium first."
  exit 1
fi

# Check if Gateway API is enabled in Cilium
log_info "Checking Cilium Gateway API configuration..."
GATEWAY_ENABLED=$(kubectl -n kube-system get cm cilium-config -o jsonpath='{.data.enable-gateway-api}' 2>/dev/null || echo "false")

if [ "$GATEWAY_ENABLED" != "true" ]; then
  log_warning "Gateway API is not enabled in Cilium"
  log_info "Enabling Gateway API in Cilium..."
  
  kubectl -n kube-system patch configmap cilium-config --type merge -p '{"data":{"enable-gateway-api":"true"}}'
  
  log_info "Restarting Cilium components..."
  kubectl -n kube-system rollout restart deployment/cilium-operator
  kubectl -n kube-system rollout restart daemonset/cilium
  
  log_info "Waiting for Cilium to be ready..."
  sleep 10
  wait_for_pods "kube-system" "k8s-app=cilium" 180
  
  log_success "Cilium configured for Gateway API"
else
  log_success "Gateway API already enabled in Cilium"
fi

#############################################################################
# Step 3: Install cert-manager
#############################################################################

if [ "$SKIP_CERT_MANAGER" = false ]; then
  log_step "Step 3: Installing cert-manager"
  
  # Check if cert-manager is already installed
  if kubectl get namespace cert-manager &> /dev/null; then
    log_warning "cert-manager namespace already exists"
    read -p "Do you want to reinstall cert-manager? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      log_info "Skipping cert-manager installation"
    else
      log_info "Uninstalling existing cert-manager..."
      helm uninstall cert-manager -n cert-manager || true
      kubectl delete namespace cert-manager || true
      sleep 5
      
      log_info "Installing cert-manager..."
      helm repo add jetstack https://charts.jetstack.io
      helm repo update
      kubectl create namespace cert-manager
      helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version "$CERT_MANAGER_VERSION" \
        --set installCRDs=true
      
      wait_for_pods "cert-manager" "app.kubernetes.io/instance=cert-manager" 300
      log_success "cert-manager installed"
    fi
  else
    log_info "Installing cert-manager version $CERT_MANAGER_VERSION..."
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    kubectl create namespace cert-manager
    helm install cert-manager jetstack/cert-manager \
      --namespace cert-manager \
      --version "$CERT_MANAGER_VERSION" \
      --set installCRDs=true
    
    wait_for_pods "cert-manager" "app.kubernetes.io/instance=cert-manager" 300
    log_success "cert-manager installed"
  fi
  
  # Verify cert-manager
  log_info "Verifying cert-manager installation..."
  if kubectl -n cert-manager get pods -l app.kubernetes.io/instance=cert-manager | grep -q "Running"; then
    log_success "cert-manager is running"
  else
    log_error "cert-manager pods are not running"
    kubectl -n cert-manager get pods
    exit 1
  fi
else
  log_step "Step 3: Skipping cert-manager installation"
fi

#############################################################################
# Step 4: Check DNS Configuration
#############################################################################

log_step "Step 4: Checking DNS Configuration"

# Get node external IP
log_info "Getting cluster external IP..."
EXTERNAL_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")

if [ -z "$EXTERNAL_IP" ]; then
  log_warning "Could not determine external IP from nodes"
  log_info "Trying to get public IP from node..."
  NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
  EXTERNAL_IP=$(kubectl get node "$NODE_NAME" -o jsonpath='{.status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")
fi

if [ -n "$EXTERNAL_IP" ]; then
  log_success "Cluster external IP: $EXTERNAL_IP"
else
  log_warning "Could not determine cluster external IP automatically"
  echo -e "${YELLOW}Please manually check your node's public IP:${NC}"
  echo "  kubectl get nodes -o wide"
fi

# Check DNS resolution
log_info "Checking DNS resolution for $DOMAIN..."
RESOLVED_IP=$(dig +short "$DOMAIN" @8.8.8.8 | tail -n1)

if [ -n "$RESOLVED_IP" ]; then
  log_success "Domain $DOMAIN resolves to: $RESOLVED_IP"
  
  if [ -n "$EXTERNAL_IP" ] && [ "$RESOLVED_IP" != "$EXTERNAL_IP" ]; then
    log_warning "DNS IP ($RESOLVED_IP) does not match cluster IP ($EXTERNAL_IP)"
    log_warning "Please update your DNS records to point to $EXTERNAL_IP"
  fi
else
  log_warning "Domain $DOMAIN does not resolve yet"
  log_warning "Please configure DNS A record: $DOMAIN -> $EXTERNAL_IP"
  log_warning "Certificate issuance will fail until DNS is properly configured"
fi

#############################################################################
# Step 5: Deploy Application
#############################################################################

log_step "Step 5: Deploying Application with Gateway API"

# Validate manifests
log_info "Validating manifests..."
if [ ! -d "$MANIFESTS_DIR" ]; then
  log_error "Manifests directory not found: $MANIFESTS_DIR"
  exit 1
fi

if [ ! -f "$MANIFESTS_DIR/kustomization.yaml" ]; then
  log_error "kustomization.yaml not found in $MANIFESTS_DIR"
  exit 1
fi

# Preview deployment
log_info "Previewing deployment..."
kubectl kustomize "$MANIFESTS_DIR" > /tmp/ai-data-capture-preview.yaml
log_success "Generated manifest preview at /tmp/ai-data-capture-preview.yaml"

if [ "$DRY_RUN" = true ]; then
  log_warning "DRY RUN MODE - Not applying changes"
  log_info "Preview of resources to be deployed:"
  kubectl kustomize "$MANIFESTS_DIR" | grep -E "^kind:|^  name:"
  exit 0
fi

# Apply manifests
log_info "Applying manifests..."
kubectl apply -k "$MANIFESTS_DIR"
log_success "Manifests applied"

# Wait for deployment
log_info "Waiting for deployment to be ready..."
sleep 5
kubectl -n "$NAMESPACE" rollout status deployment/ai-data-capture-api --timeout=300s

# Wait for pods
wait_for_pods "$NAMESPACE" "app=ai-data-capture-api" 300

#############################################################################
# Step 6: Verify Gateway and Certificate
#############################################################################

log_step "Step 6: Verifying Gateway and Certificate"

# Check Gateway
log_info "Checking Gateway status..."
if kubectl -n "$NAMESPACE" get gateway ai-data-capture-gateway &> /dev/null; then
  GATEWAY_STATUS=$(kubectl -n "$NAMESPACE" get gateway ai-data-capture-gateway -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}' 2>/dev/null || echo "Unknown")
  if [ "$GATEWAY_STATUS" = "True" ]; then
    log_success "Gateway is ready"
  else
    log_warning "Gateway status: $GATEWAY_STATUS"
    kubectl -n "$NAMESPACE" describe gateway ai-data-capture-gateway
  fi
else
  log_error "Gateway not found"
  exit 1
fi

# Check HTTPRoute
log_info "Checking HTTPRoute status..."
if kubectl -n "$NAMESPACE" get httproute ai-data-capture-api-route &> /dev/null; then
  log_success "HTTPRoute created"
else
  log_error "HTTPRoute not found"
  exit 1
fi

# Check Certificate
log_info "Checking Certificate status..."
if kubectl -n "$NAMESPACE" get certificate apidatacapture-store-tls &> /dev/null; then
  log_success "Certificate resource created"
  
  log_info "Waiting for certificate to be issued (this may take a few minutes)..."
  for i in {1..30}; do
    CERT_READY=$(kubectl -n "$NAMESPACE" get certificate apidatacapture-store-tls -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    if [ "$CERT_READY" = "True" ]; then
      log_success "Certificate issued successfully!"
      break
    else
      echo -n "."
      sleep 10
    fi
  done
  echo ""
  
  if [ "$CERT_READY" != "True" ]; then
    log_warning "Certificate not ready yet. Check status with:"
    echo "  kubectl -n $NAMESPACE describe certificate apidatacapture-store-tls"
    echo "  kubectl -n $NAMESPACE get certificaterequest"
    echo "  kubectl -n cert-manager logs -l app=cert-manager"
  fi
else
  log_error "Certificate not found"
  exit 1
fi

# Check TLS Secret
log_info "Checking TLS secret..."
if kubectl -n "$NAMESPACE" get secret apidatacapture-store-tls-secret &> /dev/null; then
  log_success "TLS secret created"
else
  log_warning "TLS secret not found yet (certificate may still be issuing)"
fi

#############################################################################
# Step 7: Display Access Information
#############################################################################

log_step "Step 7: Deployment Summary"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Information:${NC}"
echo -e "  Namespace:     ${GREEN}$NAMESPACE${NC}"
echo -e "  Domain:        ${GREEN}https://$DOMAIN${NC}"
echo -e "  API Docs:      ${GREEN}https://$DOMAIN/docs${NC}"
echo -e "  Health Check:  ${GREEN}https://$DOMAIN/health${NC}"
echo ""

# Get service info
echo -e "${BLUE}🔌 Service Information:${NC}"
kubectl -n "$NAMESPACE" get svc

echo ""
echo -e "${BLUE}📦 Pod Status:${NC}"
kubectl -n "$NAMESPACE" get pods

echo ""
echo -e "${BLUE}🌐 Gateway Status:${NC}"
kubectl -n "$NAMESPACE" get gateway

echo ""
echo -e "${BLUE}🔒 Certificate Status:${NC}"
kubectl -n "$NAMESPACE" get certificate

echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo -e "  1. Verify DNS is pointing to your cluster IP"
echo -e "  2. Wait for TLS certificate to be issued (if not ready)"
echo -e "  3. Test HTTP redirect: ${GREEN}curl -I http://$DOMAIN${NC}"
echo -e "  4. Test HTTPS access: ${GREEN}curl -I https://$DOMAIN${NC}"
echo -e "  5. Access API docs: ${GREEN}https://$DOMAIN/docs${NC}"
echo ""

echo -e "${BLUE}🔍 Useful Commands:${NC}"
echo -e "  Check certificate: ${GREEN}kubectl -n $NAMESPACE describe certificate apidatacapture-store-tls${NC}"
echo -e "  Check logs:        ${GREEN}kubectl -n $NAMESPACE logs -l app=ai-data-capture-api -f${NC}"
echo -e "  Check gateway:     ${GREEN}kubectl -n $NAMESPACE describe gateway ai-data-capture-gateway${NC}"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

log_success "Deployment script completed successfully!"
