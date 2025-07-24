#!/bin/bash

# Main deployment script - Choose your deployment method
# This script helps you select between Helm and kubectl deployment methods

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

clear
print_header "🚀 AI Data Capture Portal - Kubernetes Deployment"
print_header "=================================================="

echo
print_info "Choose your deployment method:"
echo
echo "1) 🎯 Helm-based Deployment (RECOMMENDED for Production)"
echo "   - Package management with easy upgrades/rollbacks"
echo "   - Configuration management with values files"
echo "   - Industry standard approach"
echo "   - Better for CI/CD and production environments"
echo
echo "2) ⚡ kubectl-based Deployment (Simple)"
echo "   - Direct kubectl commands"
echo "   - Faster for quick testing"
echo "   - Minimal tooling requirements"
echo "   - Good for learning and development"
echo
echo "3) 🔧 Infrastructure Only"
echo "   - Install only cert-manager and Gateway API"
echo "   - Deploy application manifests manually later"
echo
echo "4) 🛠️  Utilities"
echo "   - Secret encoding and configuration helpers"
echo
echo "0) ❌ Exit"
echo

read -p "Enter your choice (0-4): " choice

case $choice in
    1)
        print_header "\n🎯 Helm-based Deployment Selected"
        print_info "This will deploy using Helm for infrastructure components"
        
        # Check if Helm is installed
        if ! command -v helm &> /dev/null; then
            print_error "Helm is not installed"
            print_info "Install Helm: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
            exit 1
        fi
        
        echo
        print_info "Choose Helm deployment option:"
        echo "1) Complete deployment (infrastructure + application)"
        echo "2) Infrastructure only (cert-manager + Gateway API)"
        echo
        read -p "Enter choice (1-2): " helm_choice
        
        case $helm_choice in
            1)
                print_info "Running complete Helm deployment..."
                cd helm/
                ./deploy-with-helm.sh
                ;;
            2)
                print_info "Running Helm infrastructure installation..."
                cd helm/
                ./install-with-helm.sh
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
        ;;
        
    2)
        print_header "\n⚡ kubectl-based Deployment Selected"
        print_info "This will deploy using direct kubectl commands"
        
        echo
        print_info "Choose kubectl deployment option:"
        echo "1) Complete deployment (infrastructure + application)"
        echo "2) Gateway API CRDs only"
        echo
        read -p "Enter choice (1-2): " kubectl_choice
        
        case $kubectl_choice in
            1)
                print_info "Running complete kubectl deployment..."
                cd kubectl/
                ./deploy-with-tls.sh
                ;;
            2)
                print_info "Installing Gateway API CRDs only..."
                cd kubectl/
                ./install-gateway-api.sh
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
        ;;
        
    3)
        print_header "\n🔧 Infrastructure Only Selected"
        print_info "Choose infrastructure installation method:"
        echo "1) Helm-based (recommended)"
        echo "2) kubectl-based"
        echo
        read -p "Enter choice (1-2): " infra_choice
        
        case $infra_choice in
            1)
                if ! command -v helm &> /dev/null; then
                    print_error "Helm is not installed"
                    exit 1
                fi
                print_info "Installing infrastructure with Helm..."
                cd helm/
                ./install-with-helm.sh
                ;;
            2)
                print_info "Installing infrastructure with kubectl..."
                cd kubectl/
                ./install-gateway-api.sh
                print_info "Note: You'll need to install cert-manager separately"
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
        ;;
        
    4)
        print_header "\n🛠️  Utilities Selected"
        print_info "Available utilities:"
        echo "1) Encode secrets for Kubernetes"
        echo "2) View configuration examples"
        echo
        read -p "Enter choice (1-2): " util_choice
        
        case $util_choice in
            1)
                print_info "Running secret encoding utility..."
                cd utilities/
                ./encode-secrets.sh
                ;;
            2)
                print_info "Showing configuration examples..."
                cd utilities/
                cat config-example.py
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
        ;;
        
    0)
        print_info "Exiting..."
        exit 0
        ;;
        
    *)
        print_error "Invalid choice. Please enter 0-4."
        exit 1
        ;;
esac

echo
print_status "Operation completed!"
print_info "Check the output above for any additional steps required."
echo
print_info "📚 For more information, see:"
print_info "   - scripts/README.md"
print_info "   - kubernetes_deploy/docs/"
