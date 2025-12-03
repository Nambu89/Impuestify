#!/bin/bash
# TaxIA Deployment Scripts

set -e  # Exit on error

echo "🚀 TaxIA Deployment Script"
echo "=========================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your configuration before continuing"
            exit 1
        else
            print_error ".env.example not found. Please create .env manually"
            exit 1
        fi
    fi
    print_success ".env file found"
}

# Validate required environment variables
validate_env_vars() {
    print_status "Validating environment variables..."
    
    required_vars=("OPENAI_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=.*your.*key.*here" .env; then
            print_error "Required environment variable ${var} is not set or contains placeholder value"
            print_warning "Please edit your .env file and set proper values"
            exit 1
        fi
    done
    
    print_success "Environment variables validated"
}

# Setup directories
setup_directories() {
    print_status "Setting up directories..."
    
    mkdir -p data
    mkdir -p cache
    mkdir -p logs
    
    print_success "Directories created"
}

# Install dependencies (local development)
install_deps() {
    print_status "Installing dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Railway deployment
deploy_railway() {
    print_status "Deploying to Railway..."
    
    # Check if railway CLI is installed
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI not found. Install it first:"
        echo "npm install -g @railway/cli"
        exit 1
    fi
    
    # Login to Railway (if not already logged in)
    railway login
    
    # Initialize project if not exists
    if [ ! -f ".railway.toml" ]; then
        railway init
    fi
    
    # Deploy
    railway up
    
    print_success "Deployed to Railway!"
}

# Render deployment
deploy_render() {
    print_status "Setting up Render deployment..."
    
    cat > render.yaml << EOF
services:
  - type: web
    name: taxia-api
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port \$PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: OPENAI_API_KEY
        sync: false
EOF
    
    print_success "render.yaml created"
    print_warning "Remember to:"
    echo "1. Create new Web Service on Render"
    echo "2. Connect your GitHub repository"
    echo "3. Set environment variables in Render dashboard"
}

# Fly.io deployment
deploy_fly() {
    print_status "Setting up Fly.io deployment..."
    
    # Check if flyctl is installed
    if ! command -v flyctl &> /dev/null; then
        print_error "Fly CLI not found. Install it first:"
        echo "https://fly.io/docs/getting-started/installing-flyctl/"
        exit 1
    fi
    
    # Initialize Fly app
    flyctl launch --no-deploy
    
    # Set secrets
    print_status "Setting secrets..."
    flyctl secrets set OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d'=' -f2)"
    
    # Deploy
    flyctl deploy
    
    print_success "Deployed to Fly.io!"
}

# Local development setup
setup_local() {
    print_status "Setting up local development environment..."
    
    check_env_file
    validate_env_vars
    setup_directories
    install_deps
    
    print_success "Local setup complete!"
    print_status "To start the server, run:"
    echo "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
}

# Docker setup
setup_docker() {
    print_status "Setting up Docker environment..."
    
    # Build Docker image
    docker build -t taxia-api .
    
    # Create docker-compose.yml
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  taxia-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF
    
    print_success "Docker setup complete!"
    print_status "To start with Docker Compose:"
    echo "docker-compose up -d"
}

# Test deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Wait for service to be ready
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        return 1
    fi
    
    # Test basic functionality
    response=$(curl -s -X POST "http://localhost:8000/ask" \
        -H "Content-Type: application/json" \
        -d '{"question": "¿Qué es el IRPF?"}')
    
    if echo "$response" | grep -q "answer"; then
        print_success "Basic functionality test passed"
    else
        print_error "Basic functionality test failed"
        return 1
    fi
    
    print_success "All tests passed!"
}

# Main script logic
case "$1" in
    "local")
        setup_local
        ;;
    "docker")
        check_env_file
        validate_env_vars
        setup_docker
        ;;
    "railway")
        check_env_file
        validate_env_vars
        deploy_railway
        ;;
    "render")
        deploy_render
        ;;
    "fly")
        check_env_file
        validate_env_vars
        deploy_fly
        ;;
    "test")
        test_deployment
        ;;
    *)
        echo "TaxIA Deployment Script"
        echo ""
        echo "Usage: $0 {local|docker|railway|render|fly|test}"
        echo ""
        echo "Commands:"
        echo "  local   - Setup local development environment"
        echo "  docker  - Setup Docker environment"
        echo "  railway - Deploy to Railway"
        echo "  render  - Setup Render deployment files"
        echo "  fly     - Deploy to Fly.io"
        echo "  test    - Test current deployment"
        echo ""
        echo "Examples:"
        echo "  $0 local     # Setup for local development"
        echo "  $0 railway   # Deploy to Railway"
        echo "  $0 test      # Test the deployment"
        exit 1
        ;;
esac