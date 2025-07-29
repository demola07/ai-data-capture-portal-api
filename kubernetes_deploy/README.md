# AI Data Capture Portal - Kubernetes Deployment

Complete production-ready Kubernetes deployment with AWS Application Load Balancer and automatic TLS certificates.

## 🎯 Architecture Overview

- **Application**: FastAPI on Docker (`demola07/ai-data-capture:v1`)
- **Load Balancer**: AWS Application Load Balancer (ALB)
- **TLS Certificates**: Automatic via cert-manager + Let's Encrypt
- **Gateway**: Kubernetes Gateway API with Cilium
- **Domain**: `apidatacapture.store`
- **Secrets**: File-mounted for enhanced security

## 📁 Project Structure

```
kubernetes_deploy/
├── manifests/           # Kubernetes YAML files
│   ├── namespace.yaml          # Namespace isolation
│   ├── secret.yaml             # Application secrets
│   ├── rbac.yaml               # Service account & permissions
│   ├── deployment.yaml         # Application deployment
│   ├── service.yaml            # Kubernetes service
│   ├── gateway.yaml            # Gateway API (AWS ALB)
│   ├── httproute.yaml          # HTTP routing rules
│   ├── referencegrant.yaml     # Cross-namespace access
│   ├── cert-manager-issuer.yaml # Let's Encrypt issuers
│   ├── certificate.yaml       # TLS certificate
│   ├── cilium-l7policy.yaml    # Network policies
│   ├── backendtlspolicy.yaml   # Backend TLS config
│   ├── hpa.yaml                # Auto-scaling
│   ├── pdb.yaml                # Pod disruption budget
│   ├── networkpolicy.yaml      # Network security
│   └── kustomization.yaml      # Kustomize config
├── scripts/             # Deployment scripts
│   ├── setup-aws-lb.sh         # AWS ALB controller setup
│   ├── deploy-with-tls.sh      # Complete deployment
│   ├── encode-secrets.sh       # Secret encoding helper
│   └── config-example.py       # App config example
└── docs/                # Documentation
    ├── aws-alb-setup-guide.md  # AWS ALB setup guide
    ├── cert-manager-setup.md   # Certificate management
    ├── deployment-flow.md      # Deployment process
    ├── dns-setup.md            # DNS configuration
    ├── docker-hub-setup.md     # Private registry
    ├── gateway-setup.md        # Gateway API details
    └── secrets-comparison.md   # Security best practices
```

## 🚀 Quick Start

**📖 For complete documentation, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

### Interactive Deployment (Recommended)
```bash
# Run the interactive deployment selector
./scripts/deploy.sh

# Choose your preferred deployment method:
# 1) Helm-based (recommended for production)
# 2) kubectl-based (simple)
```

### Direct Deployment

**Helm-based (Production):**
```bash
cd scripts/helm/
./deploy-with-helm.sh
```

**kubectl-based (Simple):**
```bash
cd scripts/kubectl/
./deploy-with-tls.sh
```

### 1. Setup AWS Application Load Balancer
```bash
cd kubernetes_deploy/scripts
./setup-aws-lb.sh
```

### 2. Configure Your Secrets
```bash
# Edit the email in cert-manager-issuer.yaml
vim manifests/cert-manager-issuer.yaml

# Encode your secrets
./encode-secrets.sh
```

### 3. Deploy Everything
```bash
# Run the interactive deployment selector
./scripts/deploy.sh

# Choose your preferred deployment method:
# 1) Helm-based (recommended for production)
# 2) kubectl-based (simple)
```

### 4. Configure DNS
Point your domain to the ALB DNS name provided by the deployment script.

## 📋 Prerequisites

- **AWS CLI** configured with appropriate permissions
- **Helm** installed for AWS Load Balancer Controller
- **kubectl** access to your Kubernetes cluster
- **Domain ownership** of `apidatacapture.store`
- **VPC with proper subnet tagging** (script will guide you)

## 🔧 Key Features

### Production Ready
- ✅ **Auto-scaling** (3-10 replicas based on CPU/memory)
- ✅ **High availability** with pod disruption budgets
- ✅ **Health checks** and rolling updates
- ✅ **Resource limits** and security contexts

### Security
- ✅ **File-mounted secrets** (not environment variables)
- ✅ **Network policies** with Cilium L7 rules
- ✅ **RBAC** with minimal permissions
- ✅ **Non-root containers** with security contexts
- ✅ **TLS termination** at load balancer

### AWS Integration
- ✅ **Native AWS ALB** with health checks
- ✅ **Automatic target registration** 
- ✅ **Security group management**
- ✅ **CloudWatch integration**

### Certificate Management
- ✅ **Automatic TLS certificates** via Let's Encrypt
- ✅ **Auto-renewal** (90-day certificates, renewed at 75 days)
- ✅ **HTTP-01 challenge** via Gateway API
- ✅ **Multiple domain support**

## 🌐 Network Flow

```
Internet → AWS ALB → Gateway API → Service → Pods
    ↓
  Route53/DNS → apidatacapture.store
    ↓
  TLS Cert (Let's Encrypt) → HTTPS
```

## 📊 Monitoring

### AWS CloudWatch
- ALB metrics (requests, latency, errors)
- Target health monitoring
- Auto-scaling metrics

### Kubernetes
```bash
# Check application status
kubectl get all -n ai-data-capture

# Check certificate status
kubectl get certificate -n ai-data-capture

# Check gateway status
kubectl get gateway -n ai-data-capture
```

## 🔍 Troubleshooting

### Common Commands
```bash
# Check AWS Load Balancer Controller
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Check cert-manager
kubectl logs -n cert-manager deployment/cert-manager

# Check application logs
kubectl logs -n ai-data-capture deployment/ai-data-capture-api
```

### Common Issues
- **ALB not created**: Check subnet tags and IAM permissions
- **Certificate not issued**: Verify DNS propagation
- **Pods not starting**: Check secrets and image pull secrets

## 📚 Documentation

- **[AWS ALB Setup Guide](docs/aws-alb-setup-guide.md)** - Complete ALB setup
- **[Certificate Management](docs/cert-manager-setup.md)** - TLS certificate setup
- **[Deployment Flow](docs/deployment-flow.md)** - Step-by-step process
- **[DNS Configuration](docs/dns-setup.md)** - Domain setup
- **[Security Best Practices](docs/secrets-comparison.md)** - Secret management

## 🎯 Production Checklist

Before going live:
- [ ] AWS ALB Controller installed and configured
- [ ] VPC subnets properly tagged
- [ ] Secrets configured (not committed to Git)
- [ ] DNS pointing to ALB
- [ ] TLS certificates issued
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup strategy in place

## 🚨 Security Notes

- **Never commit secrets** to version control
- **Use file-mounted secrets** instead of environment variables
- **Regularly rotate secrets** and certificates
- **Monitor access logs** and unusual activity
- **Keep dependencies updated**

## 📞 Support

For issues:
1. Check the troubleshooting section in relevant docs
2. Review AWS Load Balancer Controller logs
3. Verify all prerequisites are met
4. Check AWS Console for ALB and target group status

---

**Ready to deploy?** Start with `./setup-aws-lb.sh` and follow the guides! 🚀
