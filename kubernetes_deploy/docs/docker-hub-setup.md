# Docker Hub Private Repository Setup

This guide covers setting up authentication for pulling from your private Docker Hub repository `demola07/ai-data-capture:v1`.

## 🔑 **Step 1: Create Docker Hub Access Token**

### **Option A: Personal Access Token (Recommended)**

1. **Login to Docker Hub:**
   - Go to [https://hub.docker.com/](https://hub.docker.com/)
   - Sign in with your credentials

2. **Create Access Token:**
   - Click on your profile → **Account Settings**
   - Go to **Security** tab
   - Click **New Access Token**
   - **Name**: `kubernetes-pull-token`
   - **Permissions**: Select appropriate permissions:
     - `Public Repo Read` (if repo is public but you want authenticated pulls)
     - `Private Repo Read` (if repo is private)
   - Click **Generate**
   - **IMPORTANT**: Copy the token immediately (you won't see it again)

### **Option B: Use Docker Hub Password (Less Secure)**

You can use your Docker Hub password, but access tokens are more secure and recommended.

## 🔧 **Step 2: Create Kubernetes Secret**

### **Method 1: Using kubectl (Recommended)**

```bash
# Create the namespace first
kubectl create namespace ai-data-capture

# Create Docker registry secret using access token
kubectl create secret docker-registry ai-data-capture-registry-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=demola07 \
  --docker-password=<YOUR_ACCESS_TOKEN> \
  --docker-email=<YOUR_EMAIL_ADDRESS> \
  --namespace=ai-data-capture

# Verify the secret was created
kubectl get secret ai-data-capture-registry-secret -n ai-data-capture
```

### **Method 2: Using Docker Config (Alternative)**

If you have Docker installed and logged in:

```bash
# Login to Docker Hub
docker login

# Create secret from Docker config
kubectl create secret generic ai-data-capture-registry-secret \
  --from-file=.dockerconfigjson=$HOME/.docker/config.json \
  --type=kubernetes.io/dockerconfigjson \
  --namespace=ai-data-capture
```

### **Method 3: Manual YAML Creation**

If you prefer to create the secret manually:

```bash
# Create the Docker config JSON
cat <<EOF > docker-config.json
{
  "auths": {
    "https://index.docker.io/v1/": {
      "username": "demola07",
      "password": "<YOUR_ACCESS_TOKEN>",
      "email": "<YOUR_EMAIL>",
      "auth": "$(echo -n 'demola07:<YOUR_ACCESS_TOKEN>' | base64 -w 0)"
    }
  }
}
EOF

# Base64 encode the entire config
cat docker-config.json | base64 -w 0

# Create the secret YAML
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ai-data-capture-registry-secret
  namespace: ai-data-capture
  labels:
    app: ai-data-capture-api
    environment: production
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <BASE64_ENCODED_CONFIG_FROM_ABOVE>
EOF
```

## 🚀 **Step 3: Deploy Your Application**

Your deployment is already configured to use the `imagePullSecret`. Just deploy:

```bash
# Deploy all resources
kubectl apply -k kubernetes_deploy/

# Check if pods are pulling the image successfully
kubectl get pods -n ai-data-capture
kubectl describe pod <pod-name> -n ai-data-capture
```

## 🔍 **Step 4: Verify Setup**

### **Check Secret**
```bash
# Verify secret exists
kubectl get secret ai-data-capture-registry-secret -n ai-data-capture

# Check secret details
kubectl describe secret ai-data-capture-registry-secret -n ai-data-capture
```

### **Check Pod Status**
```bash
# Check if pods are running
kubectl get pods -n ai-data-capture

# If pods are in ImagePullBackOff, check events
kubectl describe pod <pod-name> -n ai-data-capture

# Check deployment events
kubectl describe deployment ai-data-capture-api -n ai-data-capture
```

### **Test Image Pull**
```bash
# Test if you can pull the image manually
docker pull demola07/ai-data-capture:v1
```

## 🚨 **Troubleshooting**

### **Issue 1: ImagePullBackOff**

```bash
# Check pod events
kubectl describe pod <pod-name> -n ai-data-capture

# Common causes:
# - Wrong credentials
# - Wrong Docker server URL
# - Secret not in the same namespace
# - imagePullSecret name mismatch
```

### **Issue 2: Authentication Failed**

```bash
# Verify credentials work manually
docker login
docker pull demola07/ai-data-capture:v1

# Check secret content
kubectl get secret ai-data-capture-registry-secret -n ai-data-capture -o yaml
```

### **Issue 3: Wrong Docker Server**

For Docker Hub, always use:
```
--docker-server=https://index.docker.io/v1/
```

Not:
- `docker.io`
- `registry-1.docker.io`
- `https://docker.io`

### **Issue 4: Namespace Issues**

```bash
# Ensure secret is in the same namespace as deployment
kubectl get secret ai-data-capture-registry-secret -n ai-data-capture

# If secret is in wrong namespace, delete and recreate
kubectl delete secret ai-data-capture-registry-secret -n wrong-namespace
kubectl create secret docker-registry ai-data-capture-registry-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=demola07 \
  --docker-password=<YOUR_ACCESS_TOKEN> \
  --docker-email=<YOUR_EMAIL> \
  --namespace=ai-data-capture
```

## 🔒 **Security Best Practices**

1. **Use Access Tokens**: Never use your main Docker Hub password
2. **Minimal Permissions**: Give tokens only the permissions they need
3. **Token Rotation**: Regularly rotate access tokens
4. **Secure Storage**: Never commit tokens to version control
5. **Environment Separation**: Use different tokens for different environments

## 📋 **Quick Setup Commands**

```bash
# 1. Create namespace
kubectl create namespace ai-data-capture

# 2. Create Docker registry secret (replace with your token and email)
kubectl create secret docker-registry ai-data-capture-registry-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=demola07 \
  --docker-password=<YOUR_ACCESS_TOKEN> \
  --docker-email=<YOUR_EMAIL> \
  --namespace=ai-data-capture

# 3. Deploy application
kubectl apply -k kubernetes_deploy/

# 4. Check deployment
kubectl get pods -n ai-data-capture
```

## ✅ **Success Indicators**

When everything is working correctly:

- ✅ Secret exists: `kubectl get secret ai-data-capture-registry-secret -n ai-data-capture`
- ✅ Pods are running: `kubectl get pods -n ai-data-capture`
- ✅ No ImagePullBackOff errors
- ✅ Deployment shows ready replicas: `kubectl get deployment -n ai-data-capture`

Your private Docker Hub image `demola07/ai-data-capture:v1` should now pull successfully! 🎉
