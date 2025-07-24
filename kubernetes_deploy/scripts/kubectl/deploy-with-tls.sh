#!/bin/bash

# AI Data Capture Portal - Complete Deployment with TLS
# This script deploys the application with automatic TLS certificate management

set -e  # Exit on any error

echo "🚀 AI Data Capture Portal - Deployment with TLS"
echo "=================================================="
echo

# Configuration
NAMESPACE="ai-data-capture"
DOMAIN="apidatacapture.store"
EMAIL="demolasobaki@gmail.com"  # CHANGE THIS TO YOUR EMAIL

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

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

# Check and install Gateway API CRDs if needed
print_info "Checking Gateway API CRDs..."
if ! kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null; then
    print_warning "Gateway API CRDs not found, installing..."
    print_info "Installing Gateway API CRDs (standard channel)..."
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml
    
    print_info "Waiting for Gateway API CRDs to be ready..."
    kubectl wait --for condition=established --timeout=60s crd/gateways.gateway.networking.k8s.io
    kubectl wait --for condition=established --timeout=60s crd/httproutes.gateway.networking.k8s.io
    kubectl wait --for condition=established --timeout=60s crd/referencegrants.gateway.networking.k8s.io
    
    print_status "Gateway API CRDs installed successfully"
else
    print_status "Gateway API CRDs already installed"
fi

# Check if we're using simple EC2 public IP approach
print_info "Using direct EC2 public IP approach (no load balancer needed)"
print_status "Simple setup for public VPC with Internet Gateway"

print_status "Prerequisites check passed"

# Step 1: Install cert-manager
echo
echo "📦 Step 1: Installing cert-manager..."

if kubectl get namespace cert-manager &> /dev/null; then
    print_warning "cert-manager namespace already exists, skipping installation"
else
    print_info "Installing cert-manager using kubectl..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    print_info "Waiting for cert-manager to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-cainjector -n cert-manager
    
    print_status "cert-manager installed successfully"
fi

# Step 2: Verify email configuration
echo
echo "📧 Step 2: Verifying email configuration..."

if [ "$EMAIL" = "your-email@example.com" ]; then
    print_error "Please update the EMAIL variable in this script with your actual email address"
    print_info "Edit the script and change: EMAIL=\"your-email@example.com\""
    exit 1
fi

print_status "Email configuration verified: $EMAIL"

# Step 3: Update ClusterIssuer with email
echo
echo "🔧 Step 3: Updating ClusterIssuer configuration..."

# Create temporary file with updated email
TEMP_ISSUER=$(mktemp)
sed "s/your-email@example.com/$EMAIL/g" ../manifests/cert-manager-issuer.yaml > "$TEMP_ISSUER"

kubectl apply -f "$TEMP_ISSUER"
rm "$TEMP_ISSUER"

print_status "ClusterIssuer configured with email: $EMAIL"

# Step 4: Check DNS configuration
echo
echo "🌐 Step 4: Checking DNS configuration..."

print_info "Checking if $DOMAIN resolves..."
if nslookup "$DOMAIN" &> /dev/null; then
    RESOLVED_IP=$(nslookup "$DOMAIN" | grep -A1 "Name:" | tail -1 | awk '{print $2}')
    print_status "Domain $DOMAIN resolves to: $RESOLVED_IP"
else
    print_warning "Domain $DOMAIN does not resolve yet"
    print_info "Make sure to configure DNS A record pointing to your Gateway's external IP"
fi

# Step 5: Deploy application manifests
echo
echo "🚢 Step 5: Deploying application manifests..."

print_info "Applying all manifests using kustomize..."
kubectl apply -k ../manifests/

print_status "Application manifests deployed"

# Step 6: Get EC2 Public IP for DNS configuration
echo
echo "🌐 Step 6: Getting EC2 Public IP..."

print_info "Detecting your EC2 public IP address..."
if command -v curl &> /dev/null; then
    if GATEWAY_IP=$(curl -s --connect-timeout 5 --max-time 10 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null) && [ -n "$GATEWAY_IP" ]; then
        print_status "EC2 public IP detected: $GATEWAY_IP"
    else
        print_warning "Could not detect EC2 public IP automatically"
        read -p "Enter your EC2 public IP address: " GATEWAY_IP
    fi
else
    print_warning "curl not available, cannot query EC2 metadata"
    read -p "Enter your EC2 public IP address: " GATEWAY_IP
fi

if [ ! -z "$GATEWAY_IP" ]; then
    echo
    print_info "Configure your DNS with these records:"
    echo "  Type: A"
    echo "  Name: $DOMAIN"
    echo "  Value: $GATEWAY_IP"
    echo "  TTL: 300"
    echo
    echo "  Type: A"
    echo "  Name: www.$DOMAIN"
    echo "  Value: $GATEWAY_IP"
    echo "  TTL: 300"
fi

# Step 7: DNS Configuration Instructions
echo
echo "🌐 Step 7: DNS Configuration Required"
echo "===================================="

if [ ! -z "$GATEWAY_IP" ]; then
    print_warning "IMPORTANT: Configure your DNS before certificate issuance!"
    echo
    print_info "Add these DNS records in your domain manager:"
    echo "  Type: A"
    echo "  Name: apidatacapture.store"
    echo "  Value: $GATEWAY_IP"
    echo "  TTL: 300 (or lowest available)"
    echo
    echo "  Type: A"
    echo "  Name: www.apidatacapture.store"
    echo "  Value: $GATEWAY_IP"
    echo "  TTL: 300 (or lowest available)"
    echo
    
    read -p "Press ENTER after you've configured DNS records..."
    
    print_info "Testing DNS resolution..."
    for i in {1..10}; do
        if nslookup "$DOMAIN" | grep -q "$GATEWAY_IP"; then
            print_status "DNS resolution successful!"
            DNS_READY=true
            break
        fi
        echo -n "."
        sleep 10
    done
    
    if [ "$DNS_READY" != "true" ]; then
        print_warning "DNS not resolving yet. This is normal and may take time."
        print_info "Certificate will be issued automatically once DNS propagates."
    fi
fi

# Step 8: Monitor certificate issuance
echo
echo "🔐 Step 8: Certificate Status"
echo "============================="

print_info "Checking certificate status (will retry automatically)..."
CERT_STATUS=$(kubectl get certificate apidatacapture-store-tls -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")

if [ "$CERT_STATUS" = "True" ]; then
    print_status "Certificate already issued successfully!"
elif [ "$CERT_STATUS" = "False" ]; then
    CERT_MESSAGE=$(kubectl get certificate apidatacapture-store-tls -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].message}' 2>/dev/null || echo "")
    print_warning "Certificate not ready yet: $CERT_MESSAGE"
    print_info "This is normal if DNS hasn't propagated yet."
else
    print_info "Certificate status: $CERT_STATUS"
    print_info "cert-manager will automatically issue the certificate once DNS resolves."
fi

# Step 9: Verify deployment
echo
echo "🔍 Step 9: Verifying deployment..."

print_info "Checking pod status..."
kubectl get pods -n $NAMESPACE

print_info "Checking service status..."
kubectl get svc -n $NAMESPACE

print_info "Checking gateway status..."
kubectl get gateway -n $NAMESPACE

print_info "Checking certificate status..."
kubectl get certificate -n $NAMESPACE

# Final status
echo
echo "🎉 Deployment Summary"
echo "===================="
print_status "Application deployed to namespace: $NAMESPACE"
print_status "Domain: https://$DOMAIN"
print_status "TLS certificate management: Automatic via cert-manager"

if [ ! -z "$GATEWAY_IP" ]; then
    print_status "Gateway IP: $GATEWAY_IP"
    echo
    print_info "Next steps:"
    echo "1. Ensure DNS records point to $GATEWAY_IP"
    echo "2. Wait for DNS propagation (up to 48 hours)"
    echo "3. Test your application at https://$DOMAIN"
else
    print_warning "Gateway IP not available yet"
    echo
    print_info "Next steps:"
    echo "1. Wait for Gateway to get external IP: kubectl get gateway -n $NAMESPACE -w"
    echo "2. Configure DNS records with the Gateway IP"
    echo "3. Test your application at https://$DOMAIN"
fi

echo
print_info "Monitor certificate status with:"
echo "kubectl describe certificate apidatacapture-store-tls -n $NAMESPACE"

echo
print_status "Deployment completed! 🚀"
