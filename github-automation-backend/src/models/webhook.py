from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class WebhookEvent(db.Model):
    __tablename__ = 'webhook_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # push, pull_request, etc.
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    github_delivery_id = db.Column(db.String(100), unique=True, nullable=False)
    payload = db.Column(db.Text, nullable=False)  # JSON string of the full payload
    processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationships
    repository = db.relationship('Repository', backref='webhook_events')
    commits = db.relationship('CommitAnalysis', backref='webhook_event', cascade='all, delete-orphan')
    
    def get_payload(self):
        """Parse and return the JSON payload"""
        try:
            return json.loads(self.payload)
        except json.JSONDecodeError:
            return {}
    
    def set_payload(self, payload_dict):
        """Set the payload from a dictionary"""
        self.payload = json.dumps(payload_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'repository_id': self.repository_id,
            'github_delivery_id': self.github_delivery_id,
            'processed': self.processed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'payload': self.get_payload()
        }

class CommitAnalysis(db.Model):
    __tablename__ = 'commit_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    webhook_event_id = db.Column(db.Integer, db.ForeignKey('webhook_events.id'), nullable=False)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    commit_sha = db.Column(db.String(40), nullable=False)
    commit_message = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(100), nullable=False)
    
    # AI Analysis Results
    ai_analysis = db.Column(db.Text)  # JSON string of AI analysis
    suggestions = db.Column(db.Text)  # JSON string of improvement suggestions
    risk_score = db.Column(db.Integer)  # 0-100 risk assessment
    quality_score = db.Column(db.Integer)  # 0-100 code quality score
    
    # PR Generation
    pr_generated = db.Column(db.Boolean, default=False)
    pr_url = db.Column(db.String(255))
    pr_title = db.Column(db.String(255))
    pr_description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyzed_at = db.Column(db.DateTime)
    
    # Relationships
    repository = db.relationship('Repository', backref='commit_analyses')
    
    def get_ai_analysis(self):
        """Parse and return the AI analysis JSON"""
        try:
            return json.loads(self.ai_analysis) if self.ai_analysis else {}
        except json.JSONDecodeError:
            return {}
    
    def set_ai_analysis(self, analysis_dict):
        """Set the AI analysis from a dictionary"""
        self.ai_analysis = json.dumps(analysis_dict)
    
    def get_suggestions(self):
        """Parse and return the suggestions JSON"""
        try:
            return json.loads(self.suggestions) if self.suggestions else []
        except json.JSONDecodeError:
            return []
    
    def set_suggestions(self, suggestions_list):
        """Set the suggestions from a list"""
        self.suggestions = json.dumps(suggestions_list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'webhook_event_id': self.webhook_event_id,
            'repository_id': self.repository_id,
            'commit_sha': self.commit_sha,
            'commit_message': self.commit_message,
            'author_name': self.author_name,
            'author_email': self.author_email,
            'ai_analysis': self.get_ai_analysis(),
            'suggestions': self.get_suggestions(),
            'risk_score': self.risk_score,
            'quality_score': self.quality_score,
            'pr_generated': self.pr_generated,
            'pr_url': self.pr_url,
            'pr_title': self.pr_title,
            'pr_description': self.pr_description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None
        }

class ActionLog(db.Model):
    __tablename__ = 'action_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # webhook_received, commit_analyzed, pr_generated, etc.
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'))
    commit_analysis_id = db.Column(db.Integer, db.ForeignKey('commit_analyses.id'))
    
    # Log details
    message = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(20), default='info')  # info, warning, error, success
    details = db.Column(db.Text)  # JSON string for additional details
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_ms = db.Column(db.Integer)  # Duration in milliseconds
    
    # Relationships
    repository = db.relationship('Repository', backref='action_logs')
    commit_analysis = db.relationship('CommitAnalysis', backref='action_logs')
    
    def get_details(self):
        """Parse and return the details JSON"""
        try:
            return json.loads(self.details) if self.details else {}
        except json.JSONDecodeError:
            return {}
    
    def set_details(self, details_dict):
        """Set the details from a dictionary"""
        self.details = json.dumps(details_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action_type': self.action_type,
            'repository_id': self.repository_id,
            'commit_analysis_id': self.commit_analysis_id,
            'message': self.message,
            'level': self.level,
            'details': self.get_details(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'duration_ms': self.duration_ms
        }

