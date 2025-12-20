#!/bin/bash

# Quick deployment health check script
# Run this on EC2 to verify deployment status

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== AI Data Capture API - Deployment Status ===${NC}\n"

# 1. Check if container is running
echo -e "${YELLOW}1. Container Status:${NC}"
if docker ps | grep -q "ai-data-capture-api-app"; then
    echo -e "${GREEN}✅ Container is running${NC}"
    docker ps --filter name=ai-data-capture-api-app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo -e "${RED}❌ Container is not running${NC}"
    echo "Recent containers:"
    docker ps -a --filter name=ai-data-capture-api --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
fi

echo ""

# 2. Check container health
echo -e "${YELLOW}2. Health Status:${NC}"
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ai-data-capture-api-app 2>/dev/null || echo "unknown")
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✅ Container is healthy${NC}"
elif [ "$HEALTH" = "starting" ]; then
    echo -e "${YELLOW}⏳ Container is starting...${NC}"
else
    echo -e "${RED}❌ Container health: $HEALTH${NC}"
fi

echo ""

# 3. Check current image
echo -e "${YELLOW}3. Current Image:${NC}"
docker inspect --format='{{.Config.Image}}' ai-data-capture-api-app 2>/dev/null || echo "N/A"

echo ""

# 4. Test API endpoints
echo -e "${YELLOW}4. API Endpoint Tests:${NC}"

# Test root endpoint
if curl -s http://localhost:8000/ | grep -q "YMR"; then
    echo -e "${GREEN}✅ Root endpoint (/) responding${NC}"
else
    echo -e "${RED}❌ Root endpoint (/) not responding${NC}"
fi

# Test health endpoint
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health endpoint (/health) responding${NC}"
else
    echo -e "${RED}❌ Health endpoint (/health) not responding${NC}"
fi

# Test via domain (if Nginx is setup)
if command -v nginx &> /dev/null; then
    echo ""
    echo -e "${YELLOW}5. Nginx Status:${NC}"
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx is running${NC}"
        
        # Test via domain
        if curl -s http://api.ymrcounselling.com/health 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}✅ Domain (api.ymrcounselling.com) responding${NC}"
        else
            echo -e "${YELLOW}⚠️  Domain not responding (DNS may not be propagated yet)${NC}"
        fi
    else
        echo -e "${RED}❌ Nginx is not running${NC}"
    fi
fi

echo ""

# 6. Recent logs
echo -e "${YELLOW}6. Recent Logs (last 10 lines):${NC}"
docker logs ai-data-capture-api-app --tail 10 2>/dev/null || echo "No logs available"

echo ""

# 7. Resource usage
echo -e "${YELLOW}7. Resource Usage:${NC}"
docker stats ai-data-capture-api-app --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || echo "N/A"

echo ""
echo -e "${GREEN}=== Check Complete ===${NC}"
