import os
import sys
# DON'T CHANGE THIS: Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from models.repository import db, Repository, Analysis, AutomationEntry
from models.webhook import WebhookEvent, CommitAnalysis, ActionLog
from routes.repository import repository_bp
from routes.webhook import webhook_bp
from routes.admin import admin_bp
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app():
    app = Flask(__name__, static_folder='static')
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'postgresql://github_automation:automation_password@localhost/github_automation'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins="*")  # Allow all origins for development
    
    # Register blueprints
    app.register_blueprint(repository_bp, url_prefix='/api')
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    # Serve React app
    @app.route('/')
    @app.route('/<path:path>')
    def serve_react_app(path=''):
        """Serve the React application"""
        # If it's an API route, let Flask handle it normally
        if path.startswith('api/') or path.startswith('webhook/') or path.startswith('admin/'):
            return app.send_static_file('index.html')
        
        # If the file exists in static folder, serve it
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            # Otherwise, serve the React app's index.html
            return send_from_directory(app.static_folder, 'index.html')
    
    return app

app = create_app()

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5000,
        debug=True
    )

