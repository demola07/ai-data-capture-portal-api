# Gateway API Setup with Cilium

This guide covers the setup and configuration of Gateway API with Cilium for the AI Data Capture Portal API.

## 🚀 Prerequisites

### 1. Gateway API CRDs Installation

First, install the Gateway API CRDs in your cluster:

```bash
# Install Gateway API CRDs (v1.0.0 or later)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Verify installation
kubectl get crd | grep gateway
```

### 2. Cilium Gateway API Support

Ensure Cilium is configured with Gateway API support:

```bash
# Check if Cilium Gateway API is enabled
kubectl get pods -n cilium-system -l k8s-app=cilium-operator

# If not enabled, update Cilium configuration
helm upgrade cilium cilium/cilium \
  --namespace cilium-system \
  --set gatewayAPI.enabled=true \
  --set l7Proxy=true \
  --set envoy.enabled=true
```

### 3. Verify Cilium Gateway Class

Check if the Cilium Gateway Class exists:

```bash
kubectl get gatewayclass cilium
```

If it doesn't exist, it will be created by the `gateway.yaml` manifest.

## 📋 Gateway API Resources Overview

| Resource | Purpose |
|----------|---------|
| `gateway.yaml` | Main Gateway configuration with HTTP/HTTPS listeners |
| `httproute.yaml` | HTTP routing rules and traffic policies |
| `referencegrant.yaml` | Cross-namespace resource references |
| `cilium-l7policy.yaml` | Cilium-specific L7 network policies |
| `backendtlspolicy.yaml` | Backend TLS configuration (optional) |

## 🔧 Configuration Steps

### 1. Update TLS Certificates

In `gateway.yaml`, update the TLS certificate:

```bash
# Create TLS certificate (replace with your actual cert and key)
kubectl create secret tls ai-data-capture-tls-cert \
  --cert=path/to/your/certificate.crt \
  --key=path/to/your/private.key \
  -n ai-data-capture

# Or use cert-manager to automatically provision certificates
```

### 2. Update Domain Names

Update the following files with your actual domain:

- `httproute.yaml`: Domain configured as `apidatacapture.store`
- `gateway.yaml`: Update certificate references if needed

### 3. Configure Backend Services

Ensure your service configuration in `service.yaml` matches the backend references in `httproute.yaml`.

## 🚀 Deployment

Deploy all Gateway API resources:

```bash
# Apply all kubernetes_deploy
kubectl apply -k kubernetes_deploy/

# Or apply Gateway API resources specifically
kubectl apply -f kubernetes_deploy/gateway.yaml
kubectl apply -f kubernetes_deploy/httproute.yaml
kubectl apply -f kubernetes_deploy/referencegrant.yaml
kubectl apply -f kubernetes_deploy/cilium-l7policy.yaml
```

## 🔍 Verification

### 1. Check Gateway Status

```bash
# Check Gateway status
kubectl get gateway -n ai-data-capture
kubectl describe gateway ai-data-capture-gateway -n ai-data-capture

# Check Gateway Class
kubectl get gatewayclass cilium
```

### 2. Check HTTPRoute Status

```bash
# Check HTTPRoute status
kubectl get httproute -n ai-data-capture
kubectl describe httproute ai-data-capture-api-route -n ai-data-capture
```

### 3. Check Cilium Gateway Controller

```bash
# Check Cilium Gateway Controller logs
kubectl logs -n cilium-system -l k8s-app=cilium-operator | grep gateway

# Check Envoy proxy status
kubectl get pods -n cilium-system -l k8s-app=cilium
```

### 4. Test Connectivity

```bash
# Get Gateway external IP
kubectl get gateway ai-data-capture-gateway -n ai-data-capture -o jsonpath='{.status.addresses[0].value}'

# Test HTTP to HTTPS redirect
curl -v http://apidatacapture.store/health

# Test HTTPS endpoint
curl -v https://apidatacapture.store/health
```

## 🎯 Advanced Features

### 1. Traffic Splitting

Add traffic splitting to `httproute.yaml`:

```yaml
backendRefs:
- name: ai-data-capture-api-service-v1
  port: 80
  weight: 90
- name: ai-data-capture-api-service-v2
  port: 80
  weight: 10
```

### 2. Request/Response Transformation

The HTTPRoute includes examples of:
- Request header modification
- Response header modification
- Path rewriting
- Redirects

### 3. Rate Limiting with Cilium

The `cilium-l7policy.yaml` includes rate limiting examples. Adjust the limits based on your requirements.

### 4. mTLS to Backend

Uncomment and configure `backendtlspolicy.yaml` if your backend requires TLS.

## 🛠 Troubleshooting

### Gateway Not Ready

```bash
# Check Gateway events
kubectl describe gateway ai-data-capture-gateway -n ai-data-capture

# Check Cilium operator logs
kubectl logs -n cilium-system -l k8s-app=cilium-operator
```

### HTTPRoute Not Working

```bash
# Check HTTPRoute status
kubectl get httproute ai-data-capture-api-route -n ai-data-capture -o yaml

# Check backend service endpoints
kubectl get endpoints ai-data-capture-api-service -n ai-data-capture
```

### TLS Certificate Issues

```bash
# Check certificate secret
kubectl get secret ai-data-capture-tls-cert -n ai-data-capture

# Verify certificate content
kubectl get secret ai-data-capture-tls-cert -n ai-data-capture -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text
```

### Cilium L7 Policy Issues

```bash
# Check Cilium network policies
kubectl get cnp -n ai-data-capture

# Check Cilium endpoint status
kubectl exec -n cilium-system cilium-xxxxx -- cilium endpoint list
```

## 🔒 Security Considerations

1. **TLS Configuration**: Ensure strong TLS configuration with modern cipher suites
2. **Rate Limiting**: Configure appropriate rate limits in Cilium L7 policies
3. **Network Policies**: Use Cilium network policies for micro-segmentation
4. **Header Security**: Security headers are configured in HTTPRoute
5. **Certificate Management**: Use cert-manager for automated certificate lifecycle

## 📊 Monitoring

### Gateway API Metrics

Gateway API resources expose metrics that can be collected by Prometheus:

```bash
# Check if metrics are available
kubectl port-forward -n cilium-system svc/cilium-envoy 9090:9090
curl http://localhost:9090/stats
```

### Cilium Metrics

Cilium provides detailed L7 metrics:

```bash
# Enable Cilium metrics
helm upgrade cilium cilium/cilium \
  --set prometheus.enabled=true \
  --set operator.prometheus.enabled=true
```

## 🔄 Migration from Ingress

If migrating from traditional Ingress:

1. Keep both Ingress and Gateway API running initially
2. Test Gateway API thoroughly
3. Update DNS to point to Gateway IP
4. Remove Ingress resources after validation

## 📚 Additional Resources

- [Gateway API Documentation](https://gateway-api.sigs.k8s.io/)
- [Cilium Gateway API Guide](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/)
- [Gateway API Best Practices](https://gateway-api.sigs.k8s.io/guides/)
