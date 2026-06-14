#!/bin/bash

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

MODEL_RESOURCE_DIR="${SCRIPT_DIR}/model/model_resource"
echo "======================================"
echo "  Video Reasoning Pipeline Cleanup"
cd "${MODEL_RESOURCE_DIR}"
echo "This will remove all downloaded models and built artifacts."
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup aborted."
    exit 0
fi
# Remove model_resource directory
if [ -d "${MODEL_RESOURCE_DIR}" ]; then
    echo "Removing model_resource directory..."
    echo "(May require sudo for Docker-created files)"
    sudo rm -rf "${MODEL_RESOURCE_DIR}"
    echo "model_resource: Removed"
else
    echo "model_resource: Not found, skipping"
fi
echo "======================================"
echo "  Frontend Cleanup"
# Remove node_modules and build artifacts from frontend
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
cd
cd "${FRONTEND_DIR}"
if [ -d "${FRONTEND_DIR}" ]; then
    echo "Cleaning frontend node_modules and build artifacts..."
    rm -rf "${FRONTEND_DIR}/node_modules" "${FRONTEND_DIR}/dist" "${FRONTEND_DIR}/package-lock.json"
    echo "Frontend: Cleaned"
else
    echo "Frontend: Not found, skipping"
fi
echo "======================================"
echo "  Backend Cleanup"
# Remove Docker containers and images for backend
BACKEND_DIR="${SCRIPT_DIR}/backend"
cd
cd "${BACKEND_DIR}"
if [ -d "${BACKEND_DIR}" ]; then
    echo "Removing caching resources for backend..."
    cd "${BACKEND_DIR}"
    rm -rf "${BACKEND_DIR}/uploads"
    echo "Cleaning backend Docker containers and images..."
    docker compose down --rmi all --volumes --remove-orphans
    echo "Backend: Cleaned"
else
    echo "Backend: Not found, skipping"
fi
echo "Cleanup complete!"
