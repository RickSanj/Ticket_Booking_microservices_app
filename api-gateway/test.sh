#!/bin/bash
    
echo "- Build images..."
docker build -t api-gateway -f Dockerfile . 
echo "+++ Image has been successfully build"

echo "+++ Stop and remove old services..."
docker stop api-gateway
docker rm api-gateway
echo "+++ successfully stoped and removed old services"

echo "+++ Starting api-gateway..."
docker run -d \
  --name api-gateway \
  --network project-network \
  -p 8080:8080 \
  api-gateway