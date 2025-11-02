#!/bin/bash

#############################################################################
# AI Data Capture Portal - LoadBalancer Deployment Script
#############################################################################
# This script deploys the application with AWS LoadBalancer for production
# high availability and security.
#
# Usage: ./deploy-with-loadbalancer.sh [OPTIONS]
#
# Options:
#   --skip-crds         Skip Gateway API CRDs installation
#   --skip-cert-manager Skip cert-manager installation
#   --lb-type TYPE      LoadBalancer type: nlb (default) or clb
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
LB_TYPE="nlb"

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
    --lb-type)
      LB_TYPE="$2"
      shift 2
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
check_command aws
log_success "All required tools are installed"

# Check cluster connectivity
log_info "Checking Kubernetes cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
  log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
  exit 1
fi
log_success "Connected to Kubernetes cluster"

# Check AWS cloud provider
log_info "Checking AWS cloud provider configuration..."
PROVIDER_ID=$(kubectl get nodes -o jsonpath='{.items[0].spec.providerID}' 2>/dev/null || echo "")

if [[ $PROVIDER_ID == aws://* ]]; then
  log_success "AWS cloud provider is configured"
  AWS_REGION=$(echo "$PROVIDER_ID" | cut -d'/' -f4)
  log_info "AWS Region: $AWS_REGION"
else
  log_error "AWS cloud provider is not configured!"
  log_error "LoadBalancer service requires AWS cloud provider."
  log_error "Please configure your cluster with --cloud-provider=aws"
  exit 1
fi

# Check AWS credentials
log_info "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
  log_success "AWS credentials are configured"
  AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
  log_info "AWS Account: $AWS_ACCOUNT"
else
  log_warning "AWS CLI credentials not configured (may not be required if using IAM roles)"
fi

#############################################################################
# Step 1: Install Gateway API CRDs
#############################################################################

if [ "$SKIP_CRDS" = false ]; then
  log_step "Step 1: Installing Gateway API CRDs"
  
  if kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null; then
    log_warning "Gateway API CRDs already installed"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      log_info "Installing Gateway API CRDs version $GATEWAY_API_VERSION..."
      kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml"
      log_success "Gateway API CRDs installed"
    else
      log_info "Skipping Gateway API CRDs installation"
    fi
  else
    log_info "Installing Gateway API CRDs version $GATEWAY_API_VERSION..."
    kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml"
    log_success "Gateway API CRDs installed"
  fi
else
  log_step "Step 1: Skipping Gateway API CRDs installation"
fi

#############################################################################
# Step 2: Configure Cilium for Gateway API
#############################################################################

log_step "Step 2: Configuring Cilium for Gateway API"

if ! kubectl -n kube-system get deployment cilium-operator &> /dev/null; then
  log_error "Cilium is not installed. Please install Cilium first."
  exit 1
fi

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
  
  if kubectl get namespace cert-manager &> /dev/null; then
    log_warning "cert-manager namespace already exists"
    read -p "Do you want to reinstall cert-manager? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
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
    else
      log_info "Skipping cert-manager installation"
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
else
  log_step "Step 3: Skipping cert-manager installation"
fi

#############################################################################
# Step 4: Verify VPC and Subnet Configuration
#############################################################################

log_step "Step 4: Verifying VPC and Subnet Configuration"

log_info "Checking VPC configuration..."

# Get VPC ID from nodes
NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
INSTANCE_ID=$(kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}' | cut -d'/' -f5)

if [ -n "$INSTANCE_ID" ]; then
  VPC_ID=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].VpcId' --output text 2>/dev/null || echo "")
  
  if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
    log_success "VPC ID: $VPC_ID"
    
    # Check for public subnets
    log_info "Checking for public subnets with LoadBalancer tags..."
    PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
      --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:kubernetes.io/role/elb,Values=1" \
      --query 'Subnets[*].SubnetId' --output text 2>/dev/null || echo "")
    
    if [ -n "$PUBLIC_SUBNETS" ]; then
      log_success "Found public subnets: $PUBLIC_SUBNETS"
    else
      log_warning "No subnets found with tag 'kubernetes.io/role/elb=1'"
      log_warning "LoadBalancer will use auto-discovery, but tagging is recommended"
      log_info "To tag subnets manually:"
      echo "  aws ec2 create-tags --resources <subnet-id> --tags Key=kubernetes.io/role/elb,Value=1"
    fi
    
    # Check for Internet Gateway
    IGW=$(aws ec2 describe-internet-gateways \
      --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
      --query 'InternetGateways[0].InternetGatewayId' --output text 2>/dev/null || echo "")
    
    if [ -n "$IGW" ] && [ "$IGW" != "None" ]; then
      log_success "Internet Gateway attached: $IGW"
    else
      log_error "No Internet Gateway found for VPC $VPC_ID"
      log_error "LoadBalancer requires an Internet Gateway for internet-facing access"
      exit 1
    fi
  else
    log_warning "Could not determine VPC ID"
  fi
else
  log_warning "Could not determine instance ID from node"
fi

#############################################################################
# Step 5: Deploy Application with LoadBalancer
#############################################################################

log_step "Step 5: Deploying Application with LoadBalancer"

# Validate manifests
log_info "Validating manifests..."
if [ ! -d "$MANIFESTS_DIR" ]; then
  log_error "Manifests directory not found: $MANIFESTS_DIR"
  exit 1
fi

# Verify Gateway has LoadBalancer annotation
log_info "Verifying Gateway LoadBalancer configuration..."
if grep -q 'io.cilium/service-type: "LoadBalancer"' "$MANIFESTS_DIR/gateway.yaml"; then
  log_success "Gateway configured for LoadBalancer"
else
  log_error "Gateway not configured for LoadBalancer!"
  log_error "Please ensure gateway.yaml has: io.cilium/service-type: \"LoadBalancer\""
  exit 1
fi

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
# Step 6: Wait for LoadBalancer Provisioning
#############################################################################

log_step "Step 6: Waiting for LoadBalancer Provisioning"

log_info "AWS is creating the LoadBalancer (this may take 2-5 minutes)..."

# Wait for LoadBalancer to get external IP/hostname
for i in {1..60}; do
  LB_HOSTNAME=$(kubectl -n "$NAMESPACE" get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
  
  if [ -n "$LB_HOSTNAME" ]; then
    log_success "LoadBalancer provisioned!"
    break
  else
    echo -n "."
    sleep 5
  fi
done
echo ""

if [ -z "$LB_HOSTNAME" ]; then
  log_error "LoadBalancer not provisioned after 5 minutes"
  log_error "Check events: kubectl -n $NAMESPACE describe svc"
  exit 1
fi

log_success "LoadBalancer Hostname: $LB_HOSTNAME"

# Resolve LoadBalancer IPs
log_info "Resolving LoadBalancer IP addresses..."
LB_IPS=$(dig +short "$LB_HOSTNAME" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || echo "")

if [ -n "$LB_IPS" ]; then
  log_success "LoadBalancer IPs:"
  echo "$LB_IPS" | while read -r ip; do
    echo "  - $ip"
  done
else
  log_warning "Could not resolve LoadBalancer IPs yet (DNS may not be propagated)"
fi

#############################################################################
# Step 7: Verify Gateway and Certificate
#############################################################################

log_step "Step 7: Verifying Gateway and Certificate"

# Check Gateway
log_info "Checking Gateway status..."
sleep 10
GATEWAY_STATUS=$(kubectl -n "$NAMESPACE" get gateway ai-data-capture-gateway -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}' 2>/dev/null || echo "Unknown")

if [ "$GATEWAY_STATUS" = "True" ]; then
  log_success "Gateway is ready"
else
  log_warning "Gateway status: $GATEWAY_STATUS"
  log_info "Gateway may still be initializing..."
fi

# Check Certificate
log_info "Checking Certificate status..."
if kubectl -n "$NAMESPACE" get certificate apidatacapture-store-tls &> /dev/null; then
  log_success "Certificate resource created"
  
  log_info "Certificate will be issued once DNS points to LoadBalancer"
  log_warning "You must configure DNS before certificate can be issued!"
else
  log_error "Certificate not found"
fi

#############################################################################
# Step 8: DNS Configuration Instructions
#############################################################################

log_step "Step 8: DNS Configuration Required"

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  ACTION REQUIRED: Configure DNS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}LoadBalancer Hostname:${NC} ${GREEN}$LB_HOSTNAME${NC}"
echo ""
echo -e "${BLUE}Configure DNS at your provider:${NC}"
echo ""

# Check if using Route53
if aws route53 list-hosted-zones --query "HostedZones[?Name=='$DOMAIN.'].Id" --output text 2>/dev/null | grep -q "/hostedzone/"; then
  HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='$DOMAIN.'].Id" --output text | cut -d'/' -f3)
  log_success "Found Route53 Hosted Zone: $HOSTED_ZONE_ID"
  echo ""
  echo -e "${GREEN}Option 1: Use AWS Route53 (Recommended)${NC}"
  echo ""
  echo "Create ALIAS record:"
  echo "  Type: A (Alias)"
  echo "  Name: $DOMAIN"
  echo "  Value: $LB_HOSTNAME"
  echo "  Alias: Yes"
  echo ""
  echo "Or run this command:"
  echo ""
  cat << EOF
aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "$DOMAIN",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "$(aws elbv2 describe-load-balancers --query "LoadBalancers[?DNSName=='$LB_HOSTNAME'].CanonicalHostedZoneId" --output text 2>/dev/null || echo 'Z215JYRZR1TBD5')",
        "DNSName": "$LB_HOSTNAME",
        "EvaluateTargetHealth": false
      }
    }
  }]
}'
EOF
  echo ""
else
  echo -e "${GREEN}Option 1: CNAME Record (Most DNS Providers)${NC}"
  echo "  Type: CNAME"
  echo "  Name: $DOMAIN"
  echo "  Value: $LB_HOSTNAME"
  echo "  TTL: 300"
  echo ""
  echo -e "${YELLOW}Note: Some providers don't support CNAME for root domain${NC}"
  echo ""
fi

echo -e "${GREEN}Option 2: A Record (If CNAME not supported)${NC}"
if [ -n "$LB_IPS" ]; then
  echo "$LB_IPS" | while read -r ip; do
    echo "  Type: A"
    echo "  Name: $DOMAIN"
    echo "  Value: $ip"
    echo "  TTL: 300"
    echo ""
  done
else
  echo "  First resolve: dig +short $LB_HOSTNAME"
  echo "  Then create A record with resolved IP"
  echo ""
fi

echo -e "${BLUE}Also configure www subdomain:${NC}"
echo "  Type: CNAME"
echo "  Name: www"
echo "  Value: $DOMAIN"
echo "  TTL: 300"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

#############################################################################
# Step 9: Display Summary
#############################################################################

log_step "Step 9: Deployment Summary"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 LoadBalancer Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Information:${NC}"
echo -e "  Namespace:         ${GREEN}$NAMESPACE${NC}"
echo -e "  LoadBalancer Type: ${GREEN}$LB_TYPE${NC}"
echo -e "  LoadBalancer DNS:  ${GREEN}$LB_HOSTNAME${NC}"
echo -e "  Domain:            ${GREEN}https://$DOMAIN${NC}"
echo ""

echo -e "${BLUE}🔌 LoadBalancer Service:${NC}"
kubectl -n "$NAMESPACE" get svc -l gateway.networking.k8s.io/gateway-name=ai-data-capture-gateway

echo ""
echo -e "${BLUE}📦 Pod Status:${NC}"
kubectl -n "$NAMESPACE" get pods

echo ""
echo -e "${BLUE}🌐 Gateway Status:${NC}"
kubectl -n "$NAMESPACE" get gateway

echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo -e "  1. ${YELLOW}Configure DNS to point to LoadBalancer (see above)${NC}"
echo -e "  2. Wait for DNS propagation (5-60 minutes)"
echo -e "  3. Verify DNS: ${GREEN}dig $DOMAIN +short${NC}"
echo -e "  4. Wait for certificate issuance (2-5 minutes after DNS)"
echo -e "  5. Test HTTPS: ${GREEN}curl -I https://$DOMAIN${NC}"
echo ""

echo -e "${BLUE}🔍 Useful Commands:${NC}"
echo -e "  Check LoadBalancer: ${GREEN}kubectl -n $NAMESPACE get svc${NC}"
echo -e "  Check certificate:  ${GREEN}kubectl -n $NAMESPACE get certificate${NC}"
echo -e "  Check logs:         ${GREEN}kubectl -n $NAMESPACE logs -l app=ai-data-capture-api -f${NC}"
echo -e "  Test LoadBalancer:  ${GREEN}curl -I http://$LB_HOSTNAME${NC}"
echo ""

echo -e "${BLUE}🔒 Security Notes:${NC}"
echo -e "  ✅ LoadBalancer provides single entry point"
echo -e "  ✅ No NodePort exposure to internet"
echo -e "  ✅ AWS manages LoadBalancer security group"
echo -e "  ✅ TLS termination at Gateway level"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

log_success "Deployment script completed successfully!"
log_warning "Remember to configure DNS before certificate can be issued!"
