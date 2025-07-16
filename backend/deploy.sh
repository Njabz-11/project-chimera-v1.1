#!/bin/bash

# Project Chimera Enterprise Deployment Script
# This script handles deployment to different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
BUILD_TARGET="development"
COMPOSE_FILE="docker-compose.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Set environment (development|staging|production)"
    echo "  -t, --target TARGET      Set build target (development|production)"
    echo "  -f, --file FILE          Docker compose file to use"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e development        Deploy to development environment"
    echo "  $0 -e production -t production  Deploy to production"
    echo "  $0 --environment staging --file docker-compose.staging.yml"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--target)
            BUILD_TARGET="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    print_error "Must be one of: development, staging, production"
    exit 1
fi

# Set compose file based on environment if not specified
if [[ "$COMPOSE_FILE" == "docker-compose.yml" && "$ENVIRONMENT" == "production" ]]; then
    COMPOSE_FILE="docker-compose.yml -f docker-compose.prod.yml"
fi

print_status "Starting Project Chimera Enterprise deployment..."
print_status "Environment: $ENVIRONMENT"
print_status "Build Target: $BUILD_TARGET"
print_status "Compose File: $COMPOSE_FILE"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data logs static docker/nginx/ssl

# Check for environment file
if [[ ! -f .env ]]; then
    if [[ -f .env.template ]]; then
        print_warning ".env file not found. Copying from template..."
        cp .env.template .env
        print_warning "Please edit .env file with your configuration before continuing."
        read -p "Press Enter to continue after editing .env file..."
    else
        print_error ".env file not found and no template available."
        exit 1
    fi
fi

# Production-specific checks
if [[ "$ENVIRONMENT" == "production" ]]; then
    print_status "Performing production deployment checks..."
    
    # Check for required environment variables
    if ! grep -q "SECRET_KEY=" .env || grep -q "your-secret-key-change-in-production" .env; then
        print_error "Production deployment requires a secure SECRET_KEY in .env file"
        print_error "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        exit 1
    fi
    
    # Check for SSL certificates
    if [[ ! -f docker/nginx/ssl/cert.pem || ! -f docker/nginx/ssl/key.pem ]]; then
        print_warning "SSL certificates not found in docker/nginx/ssl/"
        print_warning "HTTPS will not be available. Consider adding SSL certificates for production."
    fi
    
    # Check for production database configuration
    if grep -q "sqlite" .env; then
        print_warning "SQLite database detected. Consider using PostgreSQL for production."
    fi
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down --remove-orphans || true

# Build images
print_status "Building Docker images..."
docker-compose -f $COMPOSE_FILE build --build-arg BUILD_TARGET=$BUILD_TARGET

# Start services
print_status "Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Health check
print_status "Performing health check..."
max_attempts=30
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed!"
        break
    else
        print_status "Health check attempt $attempt/$max_attempts failed, retrying in 5 seconds..."
        sleep 5
        ((attempt++))
    fi
done

if [[ $attempt -gt $max_attempts ]]; then
    print_error "Health check failed after $max_attempts attempts"
    print_error "Check logs with: docker-compose -f $COMPOSE_FILE logs"
    exit 1
fi

# Show running services
print_status "Deployment completed successfully!"
print_status "Running services:"
docker-compose -f $COMPOSE_FILE ps

# Show access URLs
print_success "Project Chimera Enterprise is now running!"
echo ""
echo "Access URLs:"
echo "  • Main Application: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Dashboard: http://localhost:8501"
echo "  • Monitoring (Grafana): http://localhost:3000 (admin/admin)"
echo "  • Metrics (Prometheus): http://localhost:9090"
echo ""

if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "Production Notes:"
    echo "  • Configure your domain DNS to point to this server"
    echo "  • Set up SSL certificates in docker/nginx/ssl/"
    echo "  • Configure firewall rules appropriately"
    echo "  • Set up regular backups"
    echo "  • Monitor logs and metrics regularly"
    echo ""
fi

print_status "To view logs: docker-compose -f $COMPOSE_FILE logs -f"
print_status "To stop: docker-compose -f $COMPOSE_FILE down"
