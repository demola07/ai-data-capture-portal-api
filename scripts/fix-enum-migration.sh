#!/bin/bash
set -e

# Script to fix the role enum migration issue
# Run this on EC2 before deploying

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Fixing role enum migration issue...${NC}\n"

# Check if we have the .env file
if [ ! -f /opt/ai-data-capture-api/.env ]; then
    echo -e "${RED}Error: .env file not found at /opt/ai-data-capture-api/.env${NC}"
    exit 1
fi

# Pull latest image
echo -e "${YELLOW}1. Pulling latest image...${NC}"
docker pull ghcr.io/demola07/ai-data-capture-portal-api:latest

# Drop the existing role enum type
echo -e "${YELLOW}2. Dropping existing role enum type...${NC}"
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  python -c "
from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        # Drop the enum type (CASCADE removes it from any columns using it)
        conn.execute(text('DROP TYPE IF EXISTS role CASCADE'))
        conn.commit()
    print('✅ Dropped old role enum type')
except Exception as e:
    print(f'⚠️  Warning: {e}')
    print('Continuing anyway...')
"

# Run migrations
echo -e "${YELLOW}3. Running database migrations...${NC}"
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations completed successfully!${NC}\n"
else
    echo -e "${RED}❌ Migration failed${NC}"
    exit 1
fi

# Create network if it doesn't exist
echo -e "${YELLOW}4. Creating Docker network...${NC}"
docker network create ai-data-capture-api-network 2>/dev/null || echo "Network already exists"

# Stop and remove old container if exists
echo -e "${YELLOW}5. Removing old container...${NC}"
docker stop ai-data-capture-api-app 2>/dev/null || true
docker rm ai-data-capture-api-app 2>/dev/null || true

# Start new container
echo -e "${YELLOW}6. Starting container...${NC}"
docker run -d \
  --name ai-data-capture-api-app \
  --network ai-data-capture-api-network \
  --env-file /opt/ai-data-capture-api/.env \
  -p 8000:8000 \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=3 \
  --health-start-period=30s \
  ghcr.io/demola07/ai-data-capture-portal-api:latest

# Wait for container to be healthy
echo -e "${YELLOW}7. Waiting for container to be healthy...${NC}"
for i in {1..30}; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ai-data-capture-api-app 2>/dev/null || echo "starting")
    
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}✅ Container is healthy!${NC}\n"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Container failed to become healthy${NC}"
        echo "Logs:"
        docker logs ai-data-capture-api-app --tail 50
        exit 1
    fi
    
    echo "Health status: $HEALTH (attempt $i/30)"
    sleep 2
done

# Test the API
echo -e "${YELLOW}8. Testing API...${NC}"
sleep 2
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is responding!${NC}\n"
    curl http://localhost:8000/health | python3 -m json.tool
else
    echo -e "${RED}❌ API is not responding${NC}"
    docker logs ai-data-capture-api-app --tail 20
    exit 1
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "Container status:"
docker ps --filter name=ai-data-capture-api-app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\nAPI endpoints:"
echo "  - http://localhost:8000/health"
echo "  - http://api.ymrcounselling.com/health"
echo "  - https://api.ymrcounselling.com/docs"
