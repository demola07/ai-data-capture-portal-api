#!/bin/bash

# Complete deployment using Helm for infrastructure components
# This is the recommended production approach

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
NAMESPACE="ai-data-capture"

echo "🚀 Complete Deployment with Helm"
echo "================================="

# Check prerequisites
print_info "Checking prerequisites..."

# Check helm
if ! command -v helm &> /dev/null; then
    print_error "Helm is not installed"
    print_info "Install Helm: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
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

# Step 1: Install infrastructure with Helm
echo
echo "🏗️  Step 1: Installing infrastructure components..."

print_info "Running Helm-based infrastructure installation..."
./install-with-helm.sh

print_status "Infrastructure components installed"

# Step 2: Create application namespace
echo
echo "📦 Step 2: Creating application namespace..."

if kubectl get namespace $NAMESPACE &> /dev/null; then
    print_warning "Namespace $NAMESPACE already exists"
else
    kubectl create namespace $NAMESPACE
    print_status "Namespace $NAMESPACE created"
fi

# Step 3: Configure cert-manager ClusterIssuer
echo
echo "🔧 Step 3: Configuring cert-manager ClusterIssuer..."

print_info "Using existing ClusterIssuer manifest with email: $EMAIL"
print_info "Applying cert-manager ClusterIssuer from manifests..."

# Apply the existing ClusterIssuer manifest
kubectl apply -f ../../manifests/cert-manager-issuer.yaml

print_status "ClusterIssuer configured successfully"

# Step 4: Deploy application manifests
echo
echo "🚀 Step 4: Deploying application manifests..."

print_info "Applying Kubernetes manifests..."
kubectl apply -k ../../manifests/

print_info "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ai-data-capture-api -n $NAMESPACE

print_status "Application deployed successfully"

# Step 5: Get Gateway IP and configure DNS
echo
echo "🌐 Step 5: Getting Gateway IP for DNS configuration..."

print_info "Waiting for Gateway to get an IP address..."

# Wait for Gateway to be ready
kubectl wait --for=condition=Programmed --timeout=300s gateway/ai-data-capture-gateway -n $NAMESPACE

# For direct EC2 public IP setup, we need to get the node's public IP
print_info "Detecting EC2 public IP for direct NodePort access..."

# Method 1: Try to get from Kubernetes node (if configured)
if GATEWAY_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null) && [ -n "$GATEWAY_IP" ]; then
    print_info "Retrieved public IP from Kubernetes node: $GATEWAY_IP"
else
    GATEWAY_IP=""
    print_info "Node ExternalIP not found in Kubernetes, trying EC2 metadata..."
    
    # Method 2: Get from EC2 metadata service (only works on EC2 instances)
    if command -v curl &> /dev/null; then
        if GATEWAY_IP=$(curl -s --connect-timeout 5 --max-time 10 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null) && [ -n "$GATEWAY_IP" ]; then
            print_info "Retrieved public IP from EC2 metadata: $GATEWAY_IP"
        else
            GATEWAY_IP=""
        fi
    else
        print_warning "curl not available, cannot query EC2 metadata"
    fi
fi

# Method 3: Manual input if automatic detection fails
if [ -z "$GATEWAY_IP" ]; then
    print_warning "Could not automatically detect public IP"
    print_info "Please find your EC2 instance's public IP from AWS Console"
    echo
    read -p "Enter your EC2 public IP address: " GATEWAY_IP
    
    if [ -z "$GATEWAY_IP" ]; then
        print_error "No IP address provided"
        exit 1
    fi
fi

if [ -n "$GATEWAY_IP" ] && [ "$GATEWAY_IP" != "null" ]; then
    print_status "Gateway IP detected: $GATEWAY_IP"
    
    echo
    echo "📋 DNS Configuration Required:"
    echo "=============================="
    echo "Please configure the following DNS A records:"
    echo
    echo "Domain: $DOMAIN"
    echo "IP Address: $GATEWAY_IP"
    echo
    echo "DNS Records to create:"
    echo "A    $DOMAIN           $GATEWAY_IP"
    echo "A    www.$DOMAIN       $GATEWAY_IP"
    echo
    
    read -p "Press Enter after configuring DNS records to continue..."
else
    print_error "Could not determine Gateway IP address"
    print_info "Please check Gateway status manually:"
    print_info "kubectl get gateway ai-data-capture-gateway -n $NAMESPACE -o wide"
    exit 1
fi

# Step 6: Wait for certificate issuance
echo
echo "🔐 Step 6: Waiting for TLS certificate issuance..."

print_info "Monitoring certificate status..."
print_info "This may take a few minutes for DNS propagation and Let's Encrypt validation..."

# Wait for certificate to be ready
for i in {1..20}; do
    CERT_STATUS=$(kubectl get certificate $DOMAIN-tls -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    
    if [ "$CERT_STATUS" = "True" ]; then
        print_status "TLS certificate issued successfully!"
        break
    fi
    
    print_info "Waiting for certificate... (attempt $i/20)"
    
    # Show certificate status for debugging
    kubectl describe certificate $DOMAIN-tls -n $NAMESPACE | grep -A 5 "Status:" || true
    
    sleep 30
done

if [ "$CERT_STATUS" != "True" ]; then
    print_warning "Certificate issuance is taking longer than expected"
    print_info "Check certificate status: kubectl describe certificate $DOMAIN-tls -n $NAMESPACE"
    print_info "Check cert-manager logs: kubectl logs -n cert-manager -l app=cert-manager"
fi

# Step 7: Verify deployment
echo
echo "🔍 Step 7: Verifying deployment..."

print_info "Checking application health..."
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get gateway -n $NAMESPACE
kubectl get httproute -n $NAMESPACE

echo
echo "🎉 Deployment Complete!"
echo "======================="
echo
echo "✅ Infrastructure installed with Helm:"
echo "   - Gateway API CRDs"
echo "   - cert-manager"
echo
echo "✅ Application deployed:"
echo "   - Namespace: $NAMESPACE"
echo "   - Gateway IP: $GATEWAY_IP"
echo "   - Domain: $DOMAIN"
echo
echo "🔗 Access your application:"
echo "   https://$DOMAIN"
echo "   https://$DOMAIN/health"
echo "   https://$DOMAIN/docs"
echo
echo "🔧 Helm management commands:"
echo "   helm list --all-namespaces"
echo "   helm upgrade cert-manager jetstack/cert-manager -n cert-manager"
echo "   helm rollback cert-manager 1 -n cert-manager"
echo
echo "📊 Monitoring commands:"
echo "   kubectl get pods -n $NAMESPACE -w"
echo "   kubectl logs -f deployment/ai-data-capture-api -n $NAMESPACE"
echo "   kubectl describe certificate $DOMAIN-tls -n $NAMESPACE"
echo
print_status "Deployment completed successfully!"
