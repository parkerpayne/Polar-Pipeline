#!/bin/bash

# Function to prune containers based on label
prune_containers() {
    LABEL="com.polar.pipeline.service"
    docker system prune --filter "label=$LABEL" --force
}

# Step 1: Stop and remove containers
echo "Stopping and removing containers..."
docker compose down

# Step 2: Prune containers based on label
echo "Pruning containers..."
prune_containers

# Step 3: Run docker-compose up
echo "Running docker-compose up..."
docker compose up -d