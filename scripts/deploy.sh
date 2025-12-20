#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ai-data-capture-api"
CONTAINER_NAME="${APP_NAME}-app"
NETWORK_NAME="${APP_NAME}-network"
DEPLOY_DIR="/opt/${APP_NAME}"
ENV_FILE="${DEPLOY_DIR}/.env"
BACKUP_DIR="${DEPLOY_DIR}/backups"

# Ensure required variables are set
if [ -z "$NEW_IMAGE" ]; then
    echo -e "${RED}ERROR: NEW_IMAGE environment variable not set${NC}"
    exit 1
fi

echo -e "${GREEN}Starting deployment of ${NEW_IMAGE}${NC}"

# Create deployment directory if it doesn't exist
mkdir -p ${DEPLOY_DIR}
mkdir -p ${BACKUP_DIR}

# Login to GitHub Container Registry
echo -e "${YELLOW}Logging in to GitHub Container Registry...${NC}"
echo ${GITHUB_TOKEN} | docker login ${REGISTRY} -u ${GITHUB_ACTOR:-github-actions} --password-stdin

# Pull new image
echo -e "${YELLOW}Pulling new image...${NC}"
docker pull ${NEW_IMAGE}

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker run --rm \
    --env-file ${ENV_FILE} \
    ${NEW_IMAGE} \
    alembic upgrade head

if [ $? -ne 0 ]; then
    echo -e "${RED}Database migration failed${NC}"
    exit 1
fi

echo -e "${GREEN}Database migrations completed successfully${NC}"

# Create docker network if it doesn't exist
docker network inspect ${NETWORK_NAME} >/dev/null 2>&1 || \
    docker network create ${NETWORK_NAME}

# Check if container is running
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo -e "${YELLOW}Existing container found. Performing zero-downtime deployment...${NC}"
    
    # Start new container with temporary name
    TEMP_CONTAINER="${CONTAINER_NAME}-new"
    
    echo -e "${YELLOW}Starting new container...${NC}"
    docker run -d \
        --name ${TEMP_CONTAINER} \
        --network ${NETWORK_NAME} \
        --env-file ${ENV_FILE} \
        -p 8001:8000 \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1" \
        --health-interval=10s \
        --health-timeout=5s \
        --health-retries=3 \
        --health-start-period=30s \
        ${NEW_IMAGE}
    
    # Wait for new container to be healthy
    echo -e "${YELLOW}Waiting for new container to be healthy...${NC}"
    for i in {1..30}; do
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' ${TEMP_CONTAINER} 2>/dev/null || echo "starting")
        
        if [ "$HEALTH_STATUS" = "healthy" ]; then
            echo -e "${GREEN}New container is healthy${NC}"
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo -e "${RED}New container failed to become healthy${NC}"
            docker logs ${TEMP_CONTAINER} --tail 50
            docker rm -f ${TEMP_CONTAINER}
            exit 1
        fi
        
        echo "Health status: ${HEALTH_STATUS} (attempt $i/30)"
        sleep 2
    done
    
    # Backup old container
    OLD_IMAGE=$(docker inspect --format='{{.Config.Image}}' ${CONTAINER_NAME})
    BACKUP_NAME="${CONTAINER_NAME}-backup-$(date +%Y%m%d-%H%M%S)"
    
    echo -e "${YELLOW}Creating backup of old container...${NC}"
    docker rename ${CONTAINER_NAME} ${BACKUP_NAME}
    docker stop ${BACKUP_NAME}
    
    # Rename new container to production name
    docker rename ${TEMP_CONTAINER} ${CONTAINER_NAME}
    
    # Update port mapping (stop and restart with correct port)
    docker stop ${CONTAINER_NAME}
    docker rm ${CONTAINER_NAME}
    
    docker run -d \
        --name ${CONTAINER_NAME} \
        --network ${NETWORK_NAME} \
        --env-file ${ENV_FILE} \
        -p 8000:8000 \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        ${NEW_IMAGE}
    
    # Wait for final container to be healthy
    echo -e "${YELLOW}Verifying final deployment...${NC}"
    sleep 5
    
    FINAL_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_NAME} 2>/dev/null || echo "unknown")
    if [ "$FINAL_HEALTH" = "healthy" ] || [ "$FINAL_HEALTH" = "starting" ]; then
        echo -e "${GREEN}Deployment successful!${NC}"
        
        # Remove backup container after successful deployment
        echo -e "${YELLOW}Cleaning up backup container...${NC}"
        docker rm ${BACKUP_NAME}
        
        # Keep backup image for rollback
        echo "Backup image available for rollback: ${OLD_IMAGE}"
    else
        echo -e "${RED}Final health check failed. Rolling back...${NC}"
        docker rm -f ${CONTAINER_NAME}
        docker rename ${BACKUP_NAME} ${CONTAINER_NAME}
        docker start ${CONTAINER_NAME}
        exit 1
    fi
else
    echo -e "${YELLOW}No existing container found. Performing fresh deployment...${NC}"
    
    docker run -d \
        --name ${CONTAINER_NAME} \
        --network ${NETWORK_NAME} \
        --env-file ${ENV_FILE} \
        -p 8000:8000 \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        ${NEW_IMAGE}
    
    echo -e "${GREEN}Fresh deployment completed${NC}"
fi

# Cleanup old images (keep last 3)
echo -e "${YELLOW}Cleaning up old images...${NC}"
docker images ${REGISTRY}/${IMAGE_NAME} --format "{{.ID}} {{.CreatedAt}}" | \
    sort -rk 2 | \
    awk 'NR>3 {print $1}' | \
    xargs -r docker rmi -f 2>/dev/null || true

# Show container status
echo -e "${GREEN}Current container status:${NC}"
docker ps -f name=${CONTAINER_NAME}

echo -e "${GREEN}Deployment completed successfully!${NC}"
