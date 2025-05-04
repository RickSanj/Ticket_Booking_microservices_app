#!/bin/bash
    
echo "- Build images..."
docker build -t event-service -f Dockerfile . 
echo "+++ Image has been successfully build"

echo "+++ Stop and remove old services..."
docker stop event-service
docker rm event-service
echo "+++ successfully stoped and removed old services"

echo "+++ Starting event-service..."
docker run -d \
  --name event-service \
  --network project-network \
  -p 8082:8082 \
  event-service