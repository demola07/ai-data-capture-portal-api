#!/bin/bash
set -e

# Rollback script for AI Data Capture API
# Usage: ./rollback.sh [image-tag]

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONTAINER_NAME="ai-data-capture-api-app"
REGISTRY="ghcr.io"
IMAGE_NAME="demola07/ai-data-capture-portal-api"

# Check if image tag is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Available images:${NC}"
    docker images ${REGISTRY}/${IMAGE_NAME} --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
    echo ""
    echo -e "${YELLOW}Usage: $0 <image-tag>${NC}"
    echo "Example: $0 main-abc1234"
    exit 1
fi

ROLLBACK_IMAGE="${REGISTRY}/${IMAGE_NAME}:$1"

echo -e "${YELLOW}Rolling back to: ${ROLLBACK_IMAGE}${NC}"

# Check if image exists locally
if ! docker image inspect ${ROLLBACK_IMAGE} >/dev/null 2>&1; then
    echo -e "${YELLOW}Image not found locally. Pulling...${NC}"
    docker pull ${ROLLBACK_IMAGE}
fi

# Stop current container
echo -e "${YELLOW}Stopping current container...${NC}"
docker stop ${CONTAINER_NAME} || true

# Backup current container
BACKUP_NAME="${CONTAINER_NAME}-pre-rollback-$(date +%Y%m%d-%H%M%S)"
docker rename ${CONTAINER_NAME} ${BACKUP_NAME} 2>/dev/null || true

# Start container with rollback image
echo -e "${YELLOW}Starting container with rollback image...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    --network ai-data-capture-api-network \
    --env-file /opt/ai-data-capture-api/.env \
    -p 8000:8000 \
    --restart unless-stopped \
    --health-cmd="curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    --health-start-period=40s \
    ${ROLLBACK_IMAGE}

# Wait for health check
echo -e "${YELLOW}Waiting for service to be healthy...${NC}"
for i in {1..30}; do
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_NAME} 2>/dev/null || echo "starting")
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo -e "${GREEN}Rollback successful! Service is healthy${NC}"
        
        # Remove backup container
        docker rm ${BACKUP_NAME} 2>/dev/null || true
        
        # Show container status
        docker ps -f name=${CONTAINER_NAME}
        exit 0
    fi
    
    echo "Health status: ${HEALTH_STATUS} (attempt $i/30)"
    sleep 2
done

echo -e "${RED}Rollback failed - service did not become healthy${NC}"
docker logs ${CONTAINER_NAME} --tail 50
exit 1
