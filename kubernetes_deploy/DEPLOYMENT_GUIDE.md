# AI Data Capture Portal - Complete Deployment Guide

This is the comprehensive guide for deploying the AI Data Capture Portal on a self-managed Kubernetes cluster with Gateway API and cert-manager.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Deployment Methods](#deployment-methods)
5. [Quick Start](#quick-start)
6. [Detailed Setup](#detailed-setup)
7. [Manifests Reference](#manifests-reference)
8. [Scripts Reference](#scripts-reference)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)
11. [Production Checklist](#production-checklist)

## 🎯 Overview

### Architecture
```
Internet → EC2 Public IP → Gateway API (Cilium) → FastAPI Application
                        ↓
                   cert-manager → Let's Encrypt TLS
```

### Key Features
- **Self-managed Kubernetes** on AWS EC2
- **Gateway API** with Cilium CNI (next-gen ingress)
- **Automatic TLS** certificates via cert-manager + Let's Encrypt
- **Direct EC2 public IP** (no external load balancer)
- **Production-ready** health checks and monitoring
- **Secure secrets** management

### Application Details
- **FastAPI** application with comprehensive health endpoints
- **Docker image**: `demola07/ai-data-capture:v1`
- **Domain**: `apidatacapture.store`
- **Ports**: 8000 (internal), 80/443 (external)

## 🔧 Prerequisites

### Required Tools
- **kubectl** - Kubernetes CLI
- **Helm** (for Helm deployment method)
- **Docker** (for building images)
- **curl** (for IP detection)

### Infrastructure Requirements
- **Self-managed Kubernetes cluster** on AWS EC2
- **Cilium CNI** with Gateway API support
- **Public VPC** with Internet Gateway
- **Domain name** registered and accessible
- **Docker Hub account** (for private images)

### Cluster Setup
```bash
# Verify cluster connection
kubectl cluster-info

# Check Cilium is running
kubectl get pods -n kube-system | grep cilium

# Verify Gateway API support
kubectl get gatewayclass cilium
```

## 📁 Project Structure

```
kubernetes_deploy/
├── DEPLOYMENT_GUIDE.md         # This comprehensive guide
├── README.md                   # Quick overview
├── manifests/                  # Kubernetes manifests
│   ├── namespace.yaml             # Application namespace
│   ├── secret.yaml                # Sensitive configuration
│   ├── configmap.yaml             # Non-sensitive configuration
│   ├── rbac.yaml                  # Service account and permissions
│   ├── deployment.yaml            # Application deployment
│   ├── service.yaml               # ClusterIP and NodePort services
│   ├── gateway.yaml               # Gateway API configuration
│   ├── httproute.yaml             # HTTP routing rules
│   ├── referencegrant.yaml        # Cross-namespace permissions
│   ├── cert-manager-issuer.yaml   # Let's Encrypt ClusterIssuer
│   ├── certificate.yaml          # TLS certificate request
│   ├── hpa.yaml                   # Horizontal Pod Autoscaler
│   ├── pdb.yaml                   # Pod Disruption Budget
│   ├── networkpolicy.yaml         # Network security policies
│   └── kustomization.yaml         # Kustomize configuration
├── scripts/                    # Deployment scripts
│   ├── deploy.sh                  # Interactive deployment selector
│   ├── README.md                  # Scripts documentation
│   ├── helm/                      # Helm-based deployment
│   │   ├── deploy-with-helm.sh       # Complete Helm deployment
│   │   └── install-with-helm.sh      # Infrastructure only
│   ├── kubectl/                   # kubectl-based deployment
│   │   ├── deploy-with-tls.sh        # Complete kubectl deployment
│   │   └── install-gateway-api.sh    # Gateway API CRDs only
│   └── utilities/                 # Helper scripts
│       ├── encode-secrets.sh         # Secret encoding utility
│       └── config-example.py         # Configuration examples
├── helm/                       # Helm values and charts
│   └── cert-manager-values.yaml      # Production cert-manager config
└── docs/                       # Legacy documentation (archived)
```

## 🚀 Deployment Methods

### Method 1: Helm-based (RECOMMENDED for Production)

**Advantages:**
- ✅ **Package management** - Easy upgrades and rollbacks
- ✅ **Configuration management** - Values files for different environments
- ✅ **Production-ready** - Industry standard approach
- ✅ **CI/CD friendly** - Better for automation

**Use when:**
- Production deployment
- Multiple environments (staging, production)
- Team collaboration
- Long-term maintenance

### Method 2: kubectl-based (Simple)

**Advantages:**
- ✅ **Simple** - Direct kubectl commands
- ✅ **Fast** - No additional tooling required
- ✅ **Educational** - Easy to understand what's happening
- ✅ **Minimal dependencies** - Only requires kubectl

**Use when:**
- Quick testing
- Learning Kubernetes
- Simple one-off deployments
- Minimal tooling requirements

## ⚡ Quick Start

### Option 1: Interactive Deployment (Recommended)
```bash
cd kubernetes_deploy/scripts/
./deploy.sh
```
*Follow the interactive prompts to choose your deployment method*

### Option 2: Direct Helm Deployment
```bash
cd kubernetes_deploy/scripts/helm/
./deploy-with-helm.sh
```

### Option 3: Direct kubectl Deployment
```bash
cd kubernetes_deploy/scripts/kubectl/
./deploy-with-tls.sh
```

## 📖 Detailed Setup

### Step 1: Prepare Secrets

Create your secrets before deployment:

```bash
cd kubernetes_deploy/scripts/utilities/
./encode-secrets.sh
```

**Required secrets:**
- Database connection details
- JWT secret key
- AWS credentials (if using AWS services)
- OpenAI API key
- Docker Hub credentials (for private images)

### Step 2: Configure Domain

Ensure your domain is ready:
- **Domain registered**: `apidatacapture.store`
- **DNS provider access** for creating A records
- **Domain verification** (if required by registrar)

### Step 3: Choose Deployment Method

#### Helm Deployment (Production)

```bash
# Install Helm if not already installed
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Navigate to helm scripts
cd kubernetes_deploy/scripts/helm/

# Run complete deployment
./deploy-with-helm.sh
```

**What it does:**
1. Installs Gateway API CRDs with Helm
2. Installs cert-manager with Helm
3. Creates application namespace
4. Applies ClusterIssuer configuration
5. Deploys application manifests
6. Detects EC2 public IP
7. Provides DNS configuration instructions
8. Waits for TLS certificate issuance

#### kubectl Deployment (Simple)

```bash
# Navigate to kubectl scripts
cd kubernetes_deploy/scripts/kubectl/

# Run complete deployment
./deploy-with-tls.sh
```

**What it does:**
1. Installs Gateway API CRDs directly
2. Installs cert-manager directly
3. Updates ClusterIssuer with email
4. Deploys application manifests
5. Detects EC2 public IP
6. Provides DNS configuration instructions
7. Waits for TLS certificate issuance

### Step 4: Configure DNS

After deployment, you'll get instructions like:
```
📋 DNS Configuration Required:
==============================
Please configure the following DNS A records:

Domain: apidatacapture.store
IP Address: 1.2.3.4

DNS Records to create:
A    apidatacapture.store           1.2.3.4
A    www.apidatacapture.store       1.2.3.4
```

**Create these A records in your DNS provider:**
- **Type**: A
- **Name**: `@` (root domain)
- **Value**: Your EC2 public IP
- **TTL**: 300 (5 minutes)

**Also create:**
- **Type**: A
- **Name**: `www`
- **Value**: Your EC2 public IP
- **TTL**: 300 (5 minutes)

### Step 5: Verify Deployment

```bash
# Check application pods
kubectl get pods -n ai-data-capture

# Check services
kubectl get services -n ai-data-capture

# Check Gateway status
kubectl get gateway -n ai-data-capture

# Check certificate status
kubectl get certificate -n ai-data-capture

# Test health endpoints
curl https://apidatacapture.store/health
curl https://apidatacapture.store/health/ready
```

## 📋 Manifests Reference

### Core Application Manifests

#### `namespace.yaml`
Creates isolated namespace for the application:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-data-capture
  labels:
    app: ai-data-capture-api
```

#### `deployment.yaml`
**Key features:**
- **3 replicas** for high availability
- **Health checks** (startup, liveness, readiness)
- **Security contexts** (non-root user)
- **Resource limits** (CPU: 500m, Memory: 512Mi)
- **Anti-affinity rules** for pod distribution

#### `service.yaml`
**Two services:**
- **ClusterIP**: Internal cluster communication
- **NodePort**: External access via node ports

#### `gateway.yaml`
**Gateway API configuration:**
- **HTTP listener** on port 80 (redirects to HTTPS)
- **HTTPS listener** on port 443 with TLS
- **Cilium gateway class**
- **NodePort service type** for direct EC2 access

#### `httproute.yaml`
**HTTP routing rules:**
- **Root path** (`/`) routes to application
- **Health check paths** for monitoring
- **CORS headers** for web clients
- **Request/response header manipulation**

### Security Manifests

#### `secret.yaml`
**Sensitive configuration:**
- Database credentials
- JWT secrets
- API keys
- TLS certificates

#### `rbac.yaml`
**Minimal permissions:**
- Service account for application
- Role with specific permissions
- RoleBinding for security

#### `networkpolicy.yaml`
**Network security:**
- Ingress rules for allowed traffic
- Egress rules for external services
- Namespace isolation

### TLS/Certificate Manifests

#### `cert-manager-issuer.yaml`
**Let's Encrypt ClusterIssuer:**
- **Production server** for real certificates
- **HTTP01 challenge** via Gateway API
- **Email configuration** for notifications

#### `certificate.yaml`
**TLS certificate request:**
- **Domain**: `apidatacapture.store`
- **Issuer reference** to Let's Encrypt
- **Secret name** for storing certificate

### Scaling and Reliability

#### `hpa.yaml`
**Horizontal Pod Autoscaler:**
- **Min replicas**: 3
- **Max replicas**: 10
- **CPU target**: 70%
- **Memory target**: 80%

#### `pdb.yaml`
**Pod Disruption Budget:**
- **Min available**: 2 pods
- **Ensures availability** during updates

## 🔧 Scripts Reference

### Interactive Deployment

#### `deploy.sh`
**Main entry point** with interactive menu:
- Choose deployment method (Helm vs kubectl)
- Select complete vs infrastructure-only deployment
- Access utility scripts

### Helm Scripts

#### `helm/deploy-with-helm.sh`
**Complete Helm-based deployment:**
1. **Prerequisites check** (Helm, kubectl, cluster)
2. **Infrastructure installation** via `install-with-helm.sh`
3. **Namespace creation**
4. **ClusterIssuer configuration** (uses existing manifest)
5. **Application deployment**
6. **IP detection** (Kubernetes node → EC2 metadata → manual)
7. **DNS configuration instructions**
8. **Certificate monitoring**

#### `helm/install-with-helm.sh`
**Infrastructure components only:**
1. **Helm repository setup**
2. **Gateway API CRDs** installation with Helm
3. **cert-manager** installation with Helm
4. **Verification** of installations

### kubectl Scripts

#### `kubectl/deploy-with-tls.sh`
**Complete kubectl-based deployment:**
1. **Prerequisites check**
2. **Gateway API CRDs** installation
3. **cert-manager** installation
4. **ClusterIssuer** configuration
5. **Application deployment**
6. **IP detection** and DNS instructions
7. **Certificate monitoring**

#### `kubectl/install-gateway-api.sh`
**Gateway API CRDs only:**
- Standalone utility for installing Gateway API CRDs
- Can be used independently
- Includes verification steps

### Utility Scripts

#### `utilities/encode-secrets.sh`
**Interactive secret creation:**
- Prompts for sensitive values
- Base64 encoding
- Direct kubectl secret creation
- No files stored on disk

## ⚙️ Configuration

### Environment Variables

The application uses these configuration sources:

#### From ConfigMap (Non-sensitive):
```yaml
DATABASE_HOST: "your-db-host"
DATABASE_PORT: "5432"
DATABASE_NAME: "ai_data_capture"
CORS_ORIGINS: "https://apidatacapture.store,https://www.apidatacapture.store"
```

#### From Secrets (Sensitive):
```yaml
DATABASE_PASSWORD: <base64-encoded>
JWT_SECRET_KEY: <base64-encoded>
AWS_ACCESS_KEY_ID: <base64-encoded>
AWS_SECRET_ACCESS_KEY: <base64-encoded>
OPENAI_API_KEY: <base64-encoded>
```

### Health Check Endpoints

The application provides comprehensive health checks:

#### `/health` - Basic Health Check
```json
{
  "status": "healthy",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "service": "ai-data-capture-portal",
  "version": "1.0.0"
}
```

#### `/health/ready` - Readiness Probe
**Tests database connectivity:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "checks": {
    "application": "ok",
    "database": "ok",
    "dependencies": "ok"
  }
}
```

#### `/health/live` - Liveness Probe
```json
{
  "status": "alive",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "uptime_seconds": 3600.5
}
```

### IP Detection Logic

Scripts use multiple methods to detect your EC2 public IP:

#### Method 1: Kubernetes Node ExternalIP
```bash
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}'
```

#### Method 2: AWS EC2 Metadata Service
```bash
curl -s http://169.254.169.254/latest/meta-data/public-ipv4
```
*This is AWS's standard metadata service, safe and reliable*

#### Method 3: Manual Input
Prompts user to enter IP if automatic detection fails.

## 🚨 Troubleshooting

### Common Issues

#### 1. Gateway API CRDs Not Found
```bash
# Error: gateway CRDs not installed
kubectl get crd | grep gateway

# Solution: Install Gateway API CRDs
cd scripts/kubectl/
./install-gateway-api.sh
```

#### 2. cert-manager Not Working
```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Check certificate status
kubectl describe certificate apidatacapture.store-tls -n ai-data-capture

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

#### 3. DNS Not Resolving
```bash
# Test DNS resolution
nslookup apidatacapture.store

# Check if A record points to correct IP
dig apidatacapture.store A
```

#### 4. Application Not Starting
```bash
# Check pod status
kubectl get pods -n ai-data-capture

# Check pod logs
kubectl logs -f deployment/ai-data-capture-deployment -n ai-data-capture

# Check events
kubectl get events -n ai-data-capture --sort-by='.lastTimestamp'
```

#### 5. TLS Certificate Issues
```bash
# Check certificate status
kubectl get certificate -n ai-data-capture

# Check certificate details
kubectl describe certificate apidatacapture.store-tls -n ai-data-capture

# Check Let's Encrypt challenges
kubectl get challenges -n ai-data-capture
```

### Debugging Commands

```bash
# Cluster health
kubectl cluster-info
kubectl get nodes -o wide

# Application health
kubectl get all -n ai-data-capture
kubectl describe deployment ai-data-capture-deployment -n ai-data-capture

# Gateway API health
kubectl get gateway -n ai-data-capture -o wide
kubectl describe gateway ai-data-capture-gateway -n ai-data-capture

# Network connectivity
kubectl exec -it <pod-name> -n ai-data-capture -- curl localhost:8000/health

# Certificate debugging
kubectl get certificaterequests -n ai-data-capture
kubectl get orders -n ai-data-capture
```

### Log Analysis

```bash
# Application logs
kubectl logs -f deployment/ai-data-capture-deployment -n ai-data-capture

# cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Cilium logs (if needed)
kubectl logs -n kube-system -l k8s-app=cilium --tail=100

# Gateway controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=cilium-operator
```

## ✅ Production Checklist

### Before Deployment
- [ ] **Kubernetes cluster** is healthy and accessible
- [ ] **Cilium CNI** is installed and Gateway API is supported
- [ ] **Domain name** is registered and accessible
- [ ] **Docker image** is built and pushed to registry
- [ ] **Secrets** are prepared and encoded
- [ ] **DNS provider** access is available

### During Deployment
- [ ] **Deployment method** chosen (Helm recommended for production)
- [ ] **Prerequisites** check passed
- [ ] **Infrastructure components** installed successfully
- [ ] **Application manifests** deployed without errors
- [ ] **Public IP** detected correctly
- [ ] **DNS A records** created and propagating

### After Deployment
- [ ] **Application pods** are running and ready
- [ ] **Health endpoints** are responding correctly
- [ ] **TLS certificate** is issued and valid
- [ ] **Domain** resolves to correct IP
- [ ] **HTTPS access** works without certificate warnings
- [ ] **API endpoints** are accessible and functional

### Monitoring Setup
- [ ] **Health check monitoring** configured
- [ ] **Log aggregation** set up
- [ ] **Metrics collection** enabled
- [ ] **Alerting rules** configured
- [ ] **Backup procedures** documented

### Security Verification
- [ ] **Secrets** are not exposed in manifests or logs
- [ ] **RBAC** permissions are minimal and appropriate
- [ ] **Network policies** are enforcing expected restrictions
- [ ] **TLS certificates** are valid and auto-renewing
- [ ] **Container security** contexts are properly configured

## 🎯 Next Steps

After successful deployment:

1. **Set up monitoring** with Prometheus and Grafana
2. **Configure log aggregation** with ELK stack or similar
3. **Implement backup strategies** for data and configurations
4. **Set up CI/CD pipelines** for automated deployments
5. **Plan scaling strategies** based on usage patterns
6. **Document operational procedures** for your team

## 📞 Support

For issues or questions:
1. **Check this guide** for common solutions
2. **Review application logs** for specific error messages
3. **Verify cluster health** and resource availability
4. **Test individual components** to isolate issues
5. **Consult Kubernetes and cert-manager documentation** for advanced troubleshooting

---

**🚀 Your AI Data Capture Portal is now ready for production use!**

This comprehensive guide covers everything needed to deploy and maintain your application successfully. Keep this document updated as your deployment evolves.
