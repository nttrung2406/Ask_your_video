#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "  Video Reasoning System"
echo "======================================"

# Parse arguments
ACTION="${1:-start}"

case $ACTION in
    start)
        echo "Starting all services..."
        
        # Create shared docker network if it doesn't exist
        echo "Setting up Docker network..."
        docker network create app_network 2>/dev/null || echo "Network app_network already exists"
        
        # Create shared volume for uploads if it doesn't exist
        echo "Setting up shared volumes..."
        docker volume create video_uploads 2>/dev/null || echo "Volume video_uploads already exists"
        
        # Run model setup (downloads resources and starts docker compose)
        echo ""
        echo "Setting up and starting Model service..."
        cd "$SCRIPT_DIR/model"
        chmod +x start.sh
        ./start.sh
        
        # Start backend
        echo ""
        echo "Starting Backend service..."
        cd "$SCRIPT_DIR/backend"
        docker compose up -d --build
        
        # Build frontend
        echo ""
        echo "Building Frontend..."
        cd "$SCRIPT_DIR/frontend"
        if [ -d "node_modules" ]; then
            echo "Node modules already installed, skipping npm install"
        else
            npm install
        fi
        npm run dev
        
        echo ""
        echo "======================================"
        echo "  All services started!"
        echo "======================================"
        echo ""
        echo "Services:"
        echo "  - Backend API:  http://localhost:8082"
        echo "  - Model API:    http://localhost:8081"
        echo "  - Redis:        localhost:8084"
        echo ""
        echo "To view logs:"
        echo "  $0 logs backend"
        echo "  $0 logs model"
        ;;
    
    stop)
        echo "Stopping all services..."
        
        cd "$SCRIPT_DIR/backend"
        docker compose down
        
        cd "$SCRIPT_DIR/model"
        docker compose down
        
        echo "All services stopped."
        ;;
    
    logs)
        SERVICE="${2:-all}"
        case $SERVICE in
            backend)
                cd "$SCRIPT_DIR/backend"
                docker compose logs -f
                ;;
            model)
                cd "$SCRIPT_DIR/model"
                docker compose logs -f
                ;;
            all)
                echo "Use '$0 logs backend' or '$0 logs model'"
                ;;
        esac
        ;;
    
    status)
        echo "Service Status:"
        echo ""
        echo "Backend:"
        cd "$SCRIPT_DIR/backend"
        docker compose ps
        echo ""
        echo "Model:"
        cd "$SCRIPT_DIR/model"
        docker compose ps
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    clean)
        echo "Cleaning up all services..."
        
        # Stop all services first
        $0 stop 2>/dev/null || true
        
        # Run cleanup script if exists
        if [ -f "$SCRIPT_DIR/cleanup.sh" ]; then
            chmod +x "$SCRIPT_DIR/cleanup.sh"
            "$SCRIPT_DIR/cleanup.sh"
        fi
        
        # Remove docker volumes
        echo "Removing Docker volumes..."
        docker volume rm video_uploads 2>/dev/null || true
        docker volume rm session-redis-data 2>/dev/null || true
        docker volume rm model_data 2>/dev/null || true
        
        # Remove docker network
        echo "Removing Docker network..."
        docker network rm app_network 2>/dev/null || true
        
        echo "Cleanup complete."
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|clean}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (model, backend, frontend)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - View logs (logs backend|model)"
        echo "  status  - Show service status"
        echo "  clean   - Stop services and remove volumes/network"
        exit 1
        ;;
esac
