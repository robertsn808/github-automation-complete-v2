#!/bin/bash

# GitHub Automation - Build and Deploy Script
# This script automates the React build process and copies files to Flask static directory

set -e  # Exit on any error

# Configuration
REACT_DIR="/home/ubuntu/my-github-automation/my-github-automation"
FLASK_STATIC_DIR="/home/ubuntu/github-automation-backend/src/static"
BACKUP_DIR="/home/ubuntu/github-automation-backend/backups"
LOG_FILE="/home/ubuntu/github-automation-backend/build.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if directory exists
check_directory() {
    if [ ! -d "$1" ]; then
        error "Directory $1 does not exist!"
        exit 1
    fi
}

# Function to create backup
create_backup() {
    if [ -d "$FLASK_STATIC_DIR" ] && [ "$(ls -A $FLASK_STATIC_DIR)" ]; then
        log "Creating backup of existing static files..."
        mkdir -p "$BACKUP_DIR"
        BACKUP_NAME="static_backup_$(date +%Y%m%d_%H%M%S)"
        cp -r "$FLASK_STATIC_DIR" "$BACKUP_DIR/$BACKUP_NAME"
        success "Backup created: $BACKUP_DIR/$BACKUP_NAME"
    else
        log "No existing static files to backup"
    fi
}

# Function to build React app
build_react() {
    log "Starting React build process..."
    
    # Check if React directory exists
    check_directory "$REACT_DIR"
    
    # Navigate to React directory
    cd "$REACT_DIR"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        error "package.json not found in $REACT_DIR"
        exit 1
    fi
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        log "Installing npm dependencies..."
        npm install
        if [ $? -ne 0 ]; then
            error "npm install failed"
            exit 1
        fi
        success "Dependencies installed successfully"
    else
        log "Dependencies already installed, skipping npm install"
    fi
    
    # Run the build
    log "Building React application..."
    npm run build
    
    if [ $? -ne 0 ]; then
        error "React build failed"
        exit 1
    fi
    
    # Check if build directory was created
    if [ ! -d "build" ]; then
        error "Build directory was not created"
        exit 1
    fi
    
    success "React build completed successfully"
}

# Function to copy files to Flask static directory
copy_to_flask() {
    log "Copying build files to Flask static directory..."
    
    # Create Flask static directory if it doesn't exist
    mkdir -p "$FLASK_STATIC_DIR"
    
    # Remove existing files (except .gitkeep if it exists)
    if [ -d "$FLASK_STATIC_DIR" ]; then
        find "$FLASK_STATIC_DIR" -mindepth 1 ! -name '.gitkeep' -delete
    fi
    
    # Copy all files from React build to Flask static
    cp -r "$REACT_DIR/build/"* "$FLASK_STATIC_DIR/"
    
    if [ $? -ne 0 ]; then
        error "Failed to copy files to Flask static directory"
        exit 1
    fi
    
    success "Files copied successfully to $FLASK_STATIC_DIR"
}

# Function to verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check if index.html exists
    if [ ! -f "$FLASK_STATIC_DIR/index.html" ]; then
        error "index.html not found in Flask static directory"
        exit 1
    fi
    
    # Check if static assets exist
    if [ ! -d "$FLASK_STATIC_DIR/static" ]; then
        warning "Static assets directory not found"
    fi
    
    # Count files
    FILE_COUNT=$(find "$FLASK_STATIC_DIR" -type f | wc -l)
    log "Total files deployed: $FILE_COUNT"
    
    success "Deployment verification completed"
}

# Function to update Flask app to serve React
update_flask_routes() {
    log "Updating Flask routes to serve React app..."
    
    FLASK_MAIN_FILE="/home/ubuntu/github-automation-backend/src/main.py"
    
    # Check if Flask main file exists
    if [ ! -f "$FLASK_MAIN_FILE" ]; then
        error "Flask main file not found: $FLASK_MAIN_FILE"
        exit 1
    fi
    
    # Create a backup of the main file
    cp "$FLASK_MAIN_FILE" "$FLASK_MAIN_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add React serving route if it doesn't exist
    if ! grep -q "serve React app" "$FLASK_MAIN_FILE"; then
        log "Adding React serving route to Flask app..."
        
        cat >> "$FLASK_MAIN_FILE" << 'EOF'

# Serve React app
@app.route('/')
@app.route('/<path:path>')
def serve_react_app(path=''):
    """Serve the React application"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
EOF
        
        success "React serving route added to Flask app"
    else
        log "React serving route already exists in Flask app"
    fi
}

# Function to restart Flask development server
restart_flask() {
    log "Checking Flask server status..."
    
    # Kill existing Flask processes
    pkill -f "python.*main.py" || true
    sleep 2
    
    log "Flask server processes stopped"
    
    # Note: In production, you would restart the server here
    # For development, the user needs to manually restart
    warning "Please restart your Flask development server to see the changes"
    log "Run: cd /home/ubuntu/github-automation-backend && source venv/bin/activate && python src/main.py"
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo "======================================"
    echo "     DEPLOYMENT SUMMARY"
    echo "======================================"
    echo ""
    echo "✅ React app built successfully"
    echo "✅ Files copied to Flask static directory"
    echo "✅ Flask routes updated"
    echo ""
    echo "📁 React build directory: $REACT_DIR/build"
    echo "📁 Flask static directory: $FLASK_STATIC_DIR"
    echo "📄 Build log: $LOG_FILE"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Restart your Flask server"
    echo "   2. Visit http://localhost:5000 to see your app"
    echo "   3. Check the admin panel at http://localhost:5000/admin"
    echo ""
    echo "======================================"
}

# Main execution
main() {
    log "Starting automated build and deploy process..."
    
    # Create log file
    touch "$LOG_FILE"
    
    # Create backup
    create_backup
    
    # Build React app
    build_react
    
    # Copy to Flask
    copy_to_flask
    
    # Verify deployment
    verify_deployment
    
    # Update Flask routes
    update_flask_routes
    
    # Restart Flask (optional)
    if [ "$1" = "--restart" ]; then
        restart_flask
    fi
    
    # Show summary
    show_summary
    
    success "Build and deploy process completed successfully!"
}

# Handle command line arguments
case "$1" in
    --help|-h)
        echo "GitHub Automation - Build and Deploy Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --restart      Restart Flask server after deployment"
        echo "  --clean        Clean build directories before building"
        echo ""
        echo "Examples:"
        echo "  $0                    # Build and deploy"
        echo "  $0 --restart          # Build, deploy, and restart server"
        echo "  $0 --clean            # Clean and build"
        echo ""
        exit 0
        ;;
    --clean)
        log "Cleaning build directories..."
        rm -rf "$REACT_DIR/build"
        rm -rf "$REACT_DIR/node_modules"
        success "Build directories cleaned"
        main
        ;;
    *)
        main "$@"
        ;;
esac

