# Cert-Manager and Let's Encrypt Setup Guide

This guide explains how to set up automatic TLS certificate management for your AI Data Capture Portal using cert-manager and Let's Encrypt.

## Overview

- **Domain**: `apidatacapture.store`
- **Certificate Authority**: Let's Encrypt
- **Challenge Type**: HTTP-01 via Gateway API
- **Certificate Manager**: cert-manager
- **Auto-renewal**: Enabled (certificates renewed 15 days before expiry)

## Prerequisites

1. **Kubernetes cluster** with Gateway API support (Cilium)
2. **Domain ownership** of `apidatacapture.store`
3. **DNS configuration** pointing to your Gateway's external IP
4. **Gateway API** resources deployed

## Step 1: Install cert-manager

### Option A: Using Helm (Recommended)

```bash
# Add the Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true \
  --set global.leaderElection.namespace=cert-manager
```

### Option B: Using kubectl

```bash
# Install cert-manager CRDs and resources
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### Verify Installation

```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Verify CRDs are installed
kubectl get crd | grep cert-manager

# Expected output should show:
# - cert-manager-webhook
# - cert-manager-controller  
# - cert-manager-cainjector
```

## Step 2: Configure DNS

Ensure your domain points to the Gateway's external IP:

```bash
# Get Gateway external IP
kubectl get gateway ai-data-capture-gateway -n ai-data-capture -o jsonpath='{.status.addresses[0].value}'

# Configure DNS A records:
# apidatacapture.store -> <GATEWAY_IP>
# www.apidatacapture.store -> <GATEWAY_IP>
```

## Step 3: Update Email in ClusterIssuer

Edit the ClusterIssuer manifest to use your email:

```bash
# Edit the cert-manager-issuer.yaml file
vim kubernetes_deploy/manifests/cert-manager-issuer.yaml

# Change this line in both issuers:
email: your-email@example.com  # Replace with your actual email
```

## Step 4: Deploy cert-manager Resources

```bash
# Apply ClusterIssuers (staging and production)
kubectl apply -f kubernetes_deploy/manifests/cert-manager-issuer.yaml

# Apply Certificate resource
kubectl apply -f kubernetes_deploy/manifests/certificate.yaml

# Verify ClusterIssuers
kubectl get clusterissuer
```

## Step 5: Deploy Application with TLS

```bash
# Deploy all manifests (Gateway will use the cert-manager certificate)
kubectl apply -k kubernetes_deploy/manifests/

# Check certificate status
kubectl get certificate -n ai-data-capture
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture
```

## Certificate Lifecycle

### Certificate Request Process

1. **Certificate resource** created → triggers cert-manager
2. **ACME challenge** initiated via HTTP-01 
3. **Let's Encrypt** validates domain ownership
4. **Certificate issued** and stored in Kubernetes secret
5. **Gateway** automatically uses the certificate for TLS termination

### Monitoring Certificates

```bash
# Check certificate status
kubectl get certificate -n ai-data-capture

# Detailed certificate information
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture

# Check certificate secret
kubectl get secret apidatacapture-store-tls-secret -n ai-data-capture

# View certificate details
kubectl get secret apidatacapture-store-tls-secret -n ai-data-capture -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

### Certificate Renewal

Certificates are automatically renewed by cert-manager:

- **Certificate duration**: 90 days (Let's Encrypt standard)
- **Renewal trigger**: 15 days before expiry
- **Renewal method**: Automatic via cert-manager controller

## Troubleshooting

### Certificate Not Issued

```bash
# Check certificate events
kubectl describe certificate apidatacapture-store-tls -n ai-data-capture

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager -f

# Check ACME challenge
kubectl get challenge -n ai-data-capture
kubectl describe challenge -n ai-data-capture
```

### Common Issues

1. **DNS not propagated**: Wait for DNS propagation (up to 48 hours)
2. **Gateway not accessible**: Ensure LoadBalancer service has external IP
3. **HTTP-01 challenge fails**: Check Gateway HTTP listener is working
4. **Rate limiting**: Use staging issuer for testing

### Testing with Staging

For testing, use the staging issuer to avoid rate limits:

```yaml
# In certificate.yaml, change:
issuerRef:
  name: letsencrypt-staging  # Use staging for testing
```

### Switching to Production

Once staging works, switch to production:

```yaml
# In certificate.yaml, change back to:
issuerRef:
  name: letsencrypt-prod  # Use production for real certificates
```

## Security Considerations

1. **Email privacy**: Use a dedicated email for Let's Encrypt notifications
2. **Certificate storage**: Secrets are stored encrypted in etcd
3. **Private key security**: RSA 2048-bit keys with PKCS1 encoding
4. **Access control**: Use RBAC to limit access to certificate secrets

## Integration with Gateway API

The certificate is automatically used by the Gateway:

```yaml
# In gateway.yaml
listeners:
- name: https
  port: 443
  protocol: HTTPS
  tls:
    mode: Terminate
    certificateRefs:
    - name: apidatacapture-store-tls-secret  # cert-manager secret
      kind: Secret
```

## Backup and Recovery

```bash
# Backup certificate secret
kubectl get secret apidatacapture-store-tls-secret -n ai-data-capture -o yaml > cert-backup.yaml

# Restore certificate secret (if needed)
kubectl apply -f cert-backup.yaml
```

This setup provides automatic, secure, and renewable TLS certificates for your AI Data Capture Portal with zero manual intervention required.
