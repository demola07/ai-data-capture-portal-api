# AI Data Capture Portal API - Kubernetes Manifests

This directory contains production-ready Kubernetes manifests for deploying the AI Data Capture Portal API to your self-managed Kubernetes cluster.

## 📁 Manifest Files

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates the `ai-data-capture` namespace for resource isolation |
| `secret.yaml` | Contains all configuration as file-mounted secrets |
| `rbac.yaml` | Service account and RBAC permissions |
| `deployment.yaml` | Main application deployment with 3 replicas |
| `service.yaml` | ClusterIP and NodePort services |
| `gateway.yaml` | Gateway API configuration with HTTP/HTTPS listeners |
| `httproute.yaml` | HTTP routing rules and traffic management |
| `referencegrant.yaml` | Cross-namespace resource access permissions |
| `cilium-l7policy.yaml` | Cilium L7 network policies and rate limiting |
| `backendtlspolicy.yaml` | Backend TLS configuration (optional) |
| `hpa.yaml` | Horizontal Pod Autoscaler for auto-scaling |
| `pdb.yaml` | Pod Disruption Budget for high availability |
| `networkpolicy.yaml` | Network policies for security |
| `kustomization.yaml` | Kustomize configuration for easy management |

## 🚀 Deployment Instructions

### Prerequisites

1. **Kubernetes cluster** with at least 2 worker nodes
2. **kubectl** configured to access your cluster
3. **Gateway API CRDs** installed in the cluster
4. **Cilium** with Gateway API support enabled
5. **Metrics server** for HPA functionality
6. **cert-manager** for SSL certificates (optional)

### Step 1: Update Configuration

Before deploying, update the following values in the manifests:

#### In `secret.yaml`:
```bash
# Use the provided script to encode all your secrets
./kubernetes_deploy/encode-secrets.sh

# Or encode manually:
echo -n "your-database-hostname" | base64
echo -n "your-database-password" | base64
echo -n "your-jwt-secret-key" | base64
# ... etc for all secrets

# Update the secret.yaml file with the encoded values
```

#### In `gateway.yaml` and `httproute.yaml`:
- Domain configured as `apidatacapture.store` in HTTPRoute
- Update TLS certificate in Gateway configuration for `apidatacapture.store`
- Configure Cilium Gateway Class if needed

### Step 2: Deploy to Kubernetes

#### Option 1: Using kubectl
```bash
# Apply all kubernetes_deploy
kubectl apply -f kubernetes_deploy/

# Or apply in specific order
kubectl apply -f kubernetes_deploy/namespace.yaml
kubectl apply -f kubernetes_deploy/secret.yaml
kubectl apply -f kubernetes_deploy/rbac.yaml
kubectl apply -f kubernetes_deploy/deployment.yaml
kubectl apply -f kubernetes_deploy/service.yaml
kubectl apply -f kubernetes_deploy/gateway.yaml
kubectl apply -f kubernetes_deploy/httproute.yaml
kubectl apply -f kubernetes_deploy/referencegrant.yaml
kubectl apply -f kubernetes_deploy/cilium-l7policy.yaml
kubectl apply -f kubernetes_deploy/hpa.yaml
kubectl apply -f kubernetes_deploy/pdb.yaml
kubectl apply -f kubernetes_deploy/networkpolicy.yaml
```

#### Option 2: Using Kustomize
```bash
# Apply using kustomize
kubectl apply -k kubernetes_deploy/
```

### Step 3: Verify Deployment

```bash
# Check namespace
kubectl get ns ai-data-capture

# Check all resources in the namespace
kubectl get all -n ai-data-capture

# Check pod status
kubectl get pods -n ai-data-capture

# Check service endpoints
kubectl get svc -n ai-data-capture

# Check Gateway and HTTPRoute
kubectl get gateway -n ai-data-capture
kubectl get httproute -n ai-data-capture

# Check HPA status
kubectl get hpa -n ai-data-capture
```

### Step 4: Access the Application

#### Via NodePort (for testing):
```bash
# Get node IP
kubectl get nodes -o wide

# Access via NodePort
curl http://<NODE_IP>:30080/health
```

#### Via Gateway API (production):
```bash
# Get Gateway external IP
kubectl get gateway ai-data-capture-gateway -n ai-data-capture -o jsonpath='{.status.addresses[0].value}'

# Access via domain
curl https://apidatacapture.store/health
```

## 🔧 Configuration Details

### Resource Allocation
- **CPU Request**: 250m per pod
- **CPU Limit**: 500m per pod
- **Memory Request**: 256Mi per pod
- **Memory Limit**: 512Mi per pod

### Scaling Configuration
- **Min Replicas**: 3
- **Max Replicas**: 10
- **CPU Threshold**: 70%
- **Memory Threshold**: 80%

### Health Checks
- **Liveness Probe**: `/health` endpoint
- **Readiness Probe**: `/health` endpoint
- **Startup Probe**: `/health` endpoint with extended timeout

### Security Features
- Non-root user (UID 1001)
- Read-only root filesystem capability
- Security contexts applied
- Network policies for traffic control
- RBAC with minimal permissions

## 🛠 Customization

### Environment-Specific Changes

Create environment-specific patches:

```yaml
# kubernetes_deploy/patches/staging-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-data-capture-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        resources:
          requests:
            memory: "128Mi"
            cpu: "125m"
```

### Updating Image Version

```bash
# Update image tag in kustomization.yaml
# Or use kustomize edit
cd kubernetes_deploy/
kustomize edit set image demola07/ai-data-capture:v2
```

## 📊 Monitoring and Logging

### Prometheus Metrics
The deployment includes annotations for Prometheus scraping:
- Metrics endpoint: `/metrics`
- Port: `8000`

### Logging
Application logs are available via:
```bash
kubectl logs -n ai-data-capture -l app=ai-data-capture-api -f
```

## 🔒 Security Considerations

1. **Secrets Management**: Use external secret management tools like AWS Secrets Manager or HashiCorp Vault
2. **Image Security**: Scan container images for vulnerabilities
3. **Network Policies**: Restrict network traffic between pods
4. **RBAC**: Apply principle of least privilege
5. **Pod Security Standards**: Consider implementing Pod Security Standards

## 🚨 Troubleshooting

### Common Issues

#### Pods not starting:
```bash
kubectl describe pod -n ai-data-capture <pod-name>
kubectl logs -n ai-data-capture <pod-name>
```

#### Service not accessible:
```bash
kubectl get endpoints -n ai-data-capture
kubectl describe svc -n ai-data-capture ai-data-capture-api-service
```

#### Ingress not working:
```bash
kubectl describe ingress -n ai-data-capture ai-data-capture-api-ingress
kubectl get events -n ai-data-capture
```

#### HPA not scaling:
```bash
kubectl describe hpa -n ai-data-capture ai-data-capture-api-hpa
kubectl top pods -n ai-data-capture
```

## 📝 Maintenance

### Rolling Updates
```bash
# Update deployment image
kubectl set image deployment/ai-data-capture-api api=demola07/ai-data-capture:v2 -n ai-data-capture

# Check rollout status
kubectl rollout status deployment/ai-data-capture-api -n ai-data-capture

# Rollback if needed
kubectl rollout undo deployment/ai-data-capture-api -n ai-data-capture
```

### Scaling
```bash
# Manual scaling
kubectl scale deployment ai-data-capture-api --replicas=5 -n ai-data-capture

# Update HPA limits
kubectl patch hpa ai-data-capture-api-hpa -n ai-data-capture -p '{"spec":{"maxReplicas":15}}'
```

## 📞 Support

For issues or questions regarding the deployment:
1. Check the troubleshooting section above
2. Review Kubernetes events: `kubectl get events -n ai-data-capture`
3. Check application logs: `kubectl logs -n ai-data-capture -l app=ai-data-capture-api`
