#!/bin/bash

# YouTube KOL Search System - One-Click Deployment Script
# For Synology NAS and other Docker-compatible systems

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/volume2/web/youtube-kol-search"
DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Functions
print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_header "Checking Requirements"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    print_info "✓ Docker is installed"
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    print_info "✓ Docker Compose is installed"
    
    # Check if running as root (needed for Synology)
    if [[ $EUID -ne 0 ]]; then
        print_warning "Not running as root. Some operations may require sudo."
    fi
}

create_directories() {
    print_header "Creating Project Directories"
    
    mkdir -p "$PROJECT_DIR"
    mkdir -p "$PROJECT_DIR/data/mysql"
    mkdir -p "$PROJECT_DIR/data/redis"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/backups"
    mkdir -p "$PROJECT_DIR/backend"
    mkdir -p "$PROJECT_DIR/frontend"
    
    print_info "✓ Directories created"
}

copy_config_files() {
    print_header "Copying Configuration Files"
    
    # Copy docker-compose.yml
    if [ -f "./assets/docker-compose.yml" ]; then
        cp ./assets/docker-compose.yml "$PROJECT_DIR/"
        print_info "✓ docker-compose.yml copied"
    else
        print_error "docker-compose.yml not found in ./assets/"
        exit 1
    fi
    
    # Copy .env.example to .env if .env doesn't exist
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "./assets/.env.example" ]; then
            cp ./assets/.env.example "$PROJECT_DIR/.env"
            print_info "✓ .env created from template"
            print_warning "Please edit $PROJECT_DIR/.env with your configuration!"
        else
            print_error ".env.example not found in ./assets/"
            exit 1
        fi
    else
        print_info "✓ .env already exists (not overwritten)"
    fi
}

setup_database() {
    print_header "Setting Up Database"
    
    # Check if init_database.py exists
    if [ ! -f "./scripts/init_database.py" ]; then
        print_error "init_database.py not found in ./scripts/"
        exit 1
    fi
    
    print_info "Database will be initialized on first Docker start"
    print_info "Or run manually: python3 scripts/init_database.py --password YOUR_PASSWORD"
}

start_services() {
    print_header "Starting Docker Services"
    
    cd "$PROJECT_DIR"
    
    # Pull images
    print_info "Pulling Docker images..."
    docker-compose pull
    
    # Build custom images
    print_info "Building application images..."
    docker-compose build
    
    # Start services
    print_info "Starting containers..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service status
    docker-compose ps
}

test_deployment() {
    print_header "Testing Deployment"
    
    # Test frontend
    if curl -f http://localhost:7853 &> /dev/null; then
        print_info "✓ Frontend is accessible at http://localhost:7853"
    else
        print_warning "⚠ Frontend may not be ready yet. Wait a minute and try http://localhost:7853"
    fi
    
    # Test API
    if curl -f http://localhost:7854/health &> /dev/null; then
        print_info "✓ API is accessible at http://localhost:7854"
    else
        print_warning "⚠ API may not be ready yet. Wait a minute and try http://localhost:7854/docs"
    fi
    
    # Test MySQL
    if docker exec youtube-kol-db mysqladmin ping -h localhost -uroot -p${MYSQL_ROOT_PASSWORD} &> /dev/null; then
        print_info "✓ MySQL is running"
    else
        print_warning "⚠ MySQL may not be ready yet"
    fi
    
    # Test Redis
    if docker exec youtube-kol-redis redis-cli ping | grep -q PONG; then
        print_info "✓ Redis is running"
    else
        print_warning "⚠ Redis may not be ready yet"
    fi
}

show_next_steps() {
    print_header "Deployment Complete!"
    
    echo ""
    echo -e "${GREEN}Access the system:${NC}"
    echo "  • Frontend:  http://localhost:7853"
    echo "  • API Docs:  http://localhost:7854/docs"
    echo "  • MySQL:     localhost:7855"
    echo "  • Redis:     localhost:7856"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Edit configuration: nano $PROJECT_DIR/.env"
    echo "  2. Add YouTube API keys via web interface (Settings → API Management)"
    echo "  3. Add AI API key (Deepseek or Zhipu)"
    echo "  4. Configure product information"
    echo "  5. Start your first search!"
    echo ""
    echo -e "${GREEN}Useful Commands:${NC}"
    echo "  • View logs:     docker-compose logs -f"
    echo "  • Stop services: docker-compose stop"
    echo "  • Start services: docker-compose start"
    echo "  • Restart:       docker-compose restart"
    echo "  • Remove all:    docker-compose down -v"
    echo ""
    echo -e "${GREEN}Testing APIs:${NC}"
    echo "  python3 scripts/test_apis.py --youtube-key YOUR_KEY --ai-provider deepseek --ai-key YOUR_AI_KEY"
    echo ""
}

main() {
    print_header "YouTube KOL Search System Deployment"
    
    check_requirements
    create_directories
    copy_config_files
    setup_database
    start_services
    test_deployment
    show_next_steps
    
    print_info "✅ Deployment completed successfully!"
}

# Run main function
main
