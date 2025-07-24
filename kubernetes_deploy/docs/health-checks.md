# Health Check Endpoints

Your FastAPI application now includes comprehensive health check endpoints that integrate perfectly with Kubernetes probes.

## 🏥 Available Health Endpoints

### 1. `/health` - Basic Health Check
**Used by**: Kubernetes liveness and readiness probes
**Purpose**: Simple health status check
```json
{
  "status": "healthy",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "service": "ai-data-capture-portal",
  "version": "1.0.0"
}
```

### 2. `/health/live` - Liveness Probe
**Used by**: Kubernetes liveness probe
**Purpose**: Check if application process is alive
```json
{
  "status": "alive",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "uptime_seconds": 3600.5
}
```

### 3. `/health/ready` - Readiness Probe
**Used by**: Kubernetes readiness probe
**Purpose**: Check if application is ready to serve traffic
**Features**: Tests database connectivity
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

**If not ready (503 status):**
```json
{
  "status": "not_ready",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "checks": {
    "application": "ok",
    "database": "failed: connection timeout",
    "dependencies": "ok"
  },
  "error": "connection timeout"
}
```

### 4. `/health/startup` - Startup Probe
**Used by**: Kubernetes startup probe
**Purpose**: Check if application has completed startup
```json
{
  "status": "started",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "startup_time": "2024-01-24T00:00:00.000Z"
}
```

### 5. `/health/status` - Detailed Health Status
**Used by**: Monitoring and debugging
**Purpose**: Comprehensive system information
```json
{
  "service": "ai-data-capture-portal",
  "version": "1.0.0",
  "status": "healthy",
  "timestamp": "2024-01-24T00:30:00.000Z",
  "uptime": {
    "seconds": 3600.5,
    "human_readable": "1h 0m 0s"
  },
  "startup_time": "2024-01-24T00:00:00.000Z",
  "environment": {
    "python_version": "3.11.0",
    "environment": "production"
  },
  "dependencies": {
    "database": {
      "status": "connected",
      "version": "PostgreSQL 15.0",
      "error": null
    }
  },
  "endpoints": {
    "health": "/health",
    "liveness": "/health/live",
    "readiness": "/health/ready",
    "startup": "/health/startup",
    "detailed": "/health/status"
  }
}
```

## 🔧 Kubernetes Integration

Your deployment manifests are already configured to use these endpoints:

### Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Startup Probe
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30
```

## 🧪 Testing Health Endpoints

### Local Testing
```bash
# Basic health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Detailed status
curl http://localhost:8000/health/status
```

### Production Testing
```bash
# After deployment
curl https://apidatacapture.store/health
curl https://apidatacapture.store/health/ready
curl https://apidatacapture.store/health/status
```

### Kubernetes Testing
```bash
# Check if probes are working
kubectl describe pod <pod-name> -n ai-data-capture

# Test from inside cluster
kubectl exec -it <pod-name> -n ai-data-capture -- curl localhost:8000/health
```

## 📊 Database Health Checks

The readiness probe includes actual database connectivity testing:

### What it checks:
- ✅ **Database connection** - Can connect to PostgreSQL
- ✅ **Query execution** - Can execute simple SELECT query
- ✅ **Response time** - Connection responds within timeout

### Failure scenarios:
- ❌ Database server down
- ❌ Network connectivity issues
- ❌ Authentication failures
- ❌ Database overloaded

## 🚨 Troubleshooting

### Pod Not Starting
```bash
# Check startup probe
kubectl describe pod <pod-name> -n ai-data-capture
kubectl logs <pod-name> -n ai-data-capture
```

### Pod Not Ready
```bash
# Check readiness probe
curl http://<pod-ip>:8000/health/ready

# Check database connectivity
kubectl logs <pod-name> -n ai-data-capture
```

### Frequent Restarts
```bash
# Check liveness probe
kubectl get events -n ai-data-capture
kubectl describe pod <pod-name> -n ai-data-capture
```

## 🔍 Monitoring Integration

### Prometheus Metrics
The health endpoints can be scraped by Prometheus:
```yaml
# Add to your monitoring config
- job_name: 'ai-data-capture-health'
  static_configs:
  - targets: ['apidatacapture.store']
  metrics_path: '/health/status'
```

### Alerting Rules
```yaml
# Example alert for unhealthy application
- alert: ApplicationUnhealthy
  expr: up{job="ai-data-capture-health"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "AI Data Capture Portal is unhealthy"
```

## 🎯 Best Practices

### Probe Configuration
- **Startup probe**: Generous timeout for slow startup
- **Liveness probe**: Conservative settings to avoid false positives
- **Readiness probe**: Strict settings for traffic management

### Database Health
- **Connection pooling**: Reuse connections for efficiency
- **Timeout handling**: Fail fast on database issues
- **Graceful degradation**: Continue serving cached data if possible

### Monitoring
- **Log health check failures** for debugging
- **Track response times** for performance monitoring
- **Set up alerts** for critical health failures

Your application now has production-ready health checks that integrate seamlessly with Kubernetes! 🏥✅
