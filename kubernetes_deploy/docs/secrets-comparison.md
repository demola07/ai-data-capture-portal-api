# Secrets Management: Environment Variables vs File Mounts

This guide compares different approaches to handling secrets in Kubernetes and provides recommendations.

## 🔒 **Comparison: Environment Variables vs File Mounts**

| Aspect | Environment Variables | File Mounts | Winner |
|--------|----------------------|-------------|---------|
| **Security** | Visible in `ps aux`, `/proc` | Hidden from process list | 🏆 **Files** |
| **Size Limits** | Limited (~1MB total) | No practical limits | 🏆 **Files** |
| **Atomic Updates** | May cause restart | Updated atomically | 🏆 **Files** |
| **Process Exposure** | Visible in process env | Not visible | 🏆 **Files** |
| **Simplicity** | Very simple to use | Requires file reading | 🏆 **Env Vars** |
| **Debugging** | Easy to check with `env` | Need to cat files | 🏆 **Env Vars** |
| **Legacy Support** | Universal support | App must support files | 🏆 **Env Vars** |
| **Certificate Storage** | Base64 encoded, messy | Natural file format | 🏆 **Files** |

## 📊 **When to Use Each Approach**

### **Use Environment Variables For:**
- ✅ Simple configuration values
- ✅ Feature flags (true/false)
- ✅ Non-sensitive settings
- ✅ Legacy applications that only support env vars
- ✅ Quick prototyping

### **Use File Mounts For:**
- ✅ Passwords and API keys
- ✅ Database connection strings
- ✅ TLS certificates and private keys
- ✅ Large configuration files
- ✅ Production environments
- ✅ Applications with high security requirements

## 🎯 **Recommended Hybrid Approach**

The best practice is to use **both approaches strategically**:

```yaml
# In deployment.yaml
env:
# Non-sensitive config from ConfigMap
- name: DATABASE_HOSTNAME
  valueFrom:
    configMapKeyRef:
      name: ai-data-capture-config
      key: database-hostname

# Point to secret files
- name: DATABASE_PASSWORD_FILE
  value: "/etc/secrets/database-password"

volumeMounts:
# Mount secrets as files
- name: secret-files
  mountPath: /etc/secrets
  readOnly: true

volumes:
- name: secret-files
  secret:
    secretName: ai-data-capture-secret
    defaultMode: 0400
```

## 🔧 **Implementation Examples**

### **1. Current Approach (Environment Variables)**

```yaml
# deployment.yaml
env:
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: ai-data-capture-secret
      key: database-password
```

```python
# In your app
import os
database_password = os.getenv("DATABASE_PASSWORD")
```

### **2. File Mount Approach (Recommended)**

```yaml
# deployment.yaml
env:
- name: DATABASE_PASSWORD_FILE
  value: "/etc/secrets/database-password"

volumeMounts:
- name: secret-files
  mountPath: /etc/secrets
  readOnly: true

volumes:
- name: secret-files
  secret:
    secretName: ai-data-capture-secret
    defaultMode: 0400
```

```python
# In your app
def read_secret_file(file_path: str) -> str:
    with open(file_path, 'r') as f:
        return f.read().strip()

database_password = read_secret_file("/etc/secrets/database-password")
```

### **3. Hybrid Approach (Best of Both)**

```python
def get_secret(env_var: str, file_path: str) -> str:
    """Try file first, fallback to environment variable."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    return os.getenv(env_var)

# Usage
database_password = get_secret("DATABASE_PASSWORD", "/etc/secrets/database-password")
```

## 🚀 **Migration Strategy**

### **Phase 1: Add File Support (Backward Compatible)**

1. **Update deployment** to mount secrets as files
2. **Update application** to support both env vars and files
3. **Test thoroughly** in development

### **Phase 2: Switch to Files (Production)**

1. **Deploy with file mounts** enabled
2. **Verify application** reads from files
3. **Remove environment variables** from deployment

### **Phase 3: Clean Up**

1. **Remove fallback** to environment variables
2. **Update documentation**
3. **Security audit**

## 🔒 **Security Best Practices**

### **File Permissions**
```yaml
volumes:
- name: secret-files
  secret:
    secretName: ai-data-capture-secret
    defaultMode: 0400  # Read-only for owner only
    items:
    - key: database-password
      path: database-password
      mode: 0400
```

### **File Locations**
- ✅ Use `/etc/secrets/` for secret files
- ✅ Use `/etc/config/` for config files
- ❌ Avoid `/tmp/` or world-writable directories

### **Application Security**
```python
import os
import stat

def read_secret_securely(file_path: str) -> str:
    """Read secret file with security checks."""
    # Check file permissions
    file_stat = os.stat(file_path)
    if file_stat.st_mode & stat.S_IROTH:
        raise ValueError(f"Secret file {file_path} is world-readable!")
    
    # Read file
    with open(file_path, 'r') as f:
        return f.read().strip()
```

## 📋 **Implementation Checklist**

### **For Your FastAPI Application:**

- [ ] **Update deployment.yaml** to mount secrets as files
- [ ] **Modify application code** to read from files
- [ ] **Add fallback logic** for backward compatibility
- [ ] **Test locally** with mounted files
- [ ] **Deploy to development** environment
- [ ] **Verify security** (file permissions, process visibility)
- [ ] **Deploy to production**
- [ ] **Remove environment variable fallbacks**

### **Files to Update:**

1. **`deployment.yaml`** - Add volume mounts
2. **`secret.yaml`** - Ensure secrets are properly structured
3. **Application config** - Add file reading logic
4. **Health checks** - Verify secrets are loaded
5. **Documentation** - Update deployment guides

## 🎯 **Recommendation for Your Project**

For your AI Data Capture Portal API, I recommend:

1. **Use the hybrid approach** (`deployment-with-file-secrets.yaml`)
2. **Mount sensitive secrets as files**:
   - Database password
   - JWT secret key
   - API keys
3. **Keep non-sensitive config as environment variables**:
   - Database hostname
   - Port numbers
   - Feature flags

This gives you the **security benefits of file mounts** while maintaining **simplicity for non-sensitive configuration**.

## 🔄 **Quick Migration**

To switch to file-based secrets:

```bash
# 1. Replace your current deployment
cp kubernetes_deploy/deployment-with-file-secrets.yaml kubernetes_deploy/deployment.yaml

# 2. Update your application code (see config-example.py)

# 3. Deploy
kubectl apply -k kubernetes_deploy/

# 4. Verify
kubectl exec -it <pod-name> -n ai-data-capture -- ls -la /etc/secrets/
```

Your secrets will be more secure and your application will be production-ready! 🚀
