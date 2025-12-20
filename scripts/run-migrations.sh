#!/bin/bash
set -e

# Manual database migration script
# Use this to run migrations manually on EC2

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_NAME="ai-data-capture-api"
DEPLOY_DIR="/opt/${APP_NAME}"
ENV_FILE="${DEPLOY_DIR}/.env"

echo -e "${GREEN}Running database migrations...${NC}"

# Get current running image
CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' ${APP_NAME}-app 2>/dev/null || echo "")

if [ -z "$CURRENT_IMAGE" ]; then
    echo -e "${RED}No running container found. Please specify image:${NC}"
    echo "Usage: $0 [image-name]"
    echo "Example: $0 ghcr.io/demola07/ai-data-capture-portal-api:latest"
    exit 1
fi

IMAGE="${1:-$CURRENT_IMAGE}"

echo -e "${YELLOW}Using image: ${IMAGE}${NC}"

# Run migrations
docker run --rm \
    --env-file ${ENV_FILE} \
    ${IMAGE} \
    alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations completed successfully${NC}"
else
    echo -e "${RED}❌ Migration failed${NC}"
    exit 1
fi

# Show current migration version
echo -e "${YELLOW}Current database version:${NC}"
docker run --rm \
    --env-file ${ENV_FILE} \
    ${IMAGE} \
    alembic current
