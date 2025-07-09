from flask import Blueprint, request, jsonify
import hashlib
import hmac
import json
from datetime import datetime
from ..models.webhook import WebhookEvent, CommitAnalysis, ActionLog, db
from ..models.repository import Repository
from ..services.github_service import GitHubService
from ..services.openai_service import OpenAIService
import logging

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

def verify_github_signature(payload_body, signature_header, secret):
    """Verify that the payload was sent from GitHub by validating SHA256 signature."""
    if not signature_header:
        return False
    
    hash_object = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

@webhook_bp.route('/webhook/github', methods=['POST'])
def handle_github_webhook():
    """Handle incoming GitHub webhook events"""
    start_time = datetime.utcnow()
    
    try:
        # Get headers
        event_type = request.headers.get('X-GitHub-Event')
        delivery_id = request.headers.get('X-GitHub-Delivery')
        signature = request.headers.get('X-Hub-Signature-256')
        
        if not event_type or not delivery_id:
            logger.warning("Missing required GitHub headers")
            return jsonify({'error': 'Missing required headers'}), 400
        
        # Get payload
        payload_body = request.get_data()
        
        # Verify signature (optional - uncomment if you set up webhook secret)
        # webhook_secret = os.environ.get('GITHUB_WEBHOOK_SECRET')
        # if webhook_secret and not verify_github_signature(payload_body, signature, webhook_secret):
        #     logger.warning(f"Invalid signature for delivery {delivery_id}")
        #     return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse JSON payload
        try:
            payload = json.loads(payload_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload for delivery {delivery_id}")
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        # Get or create repository
        repo_data = payload.get('repository', {})
        if not repo_data:
            logger.warning(f"No repository data in payload for delivery {delivery_id}")
            return jsonify({'error': 'No repository data'}), 400
        
        repository = Repository.query.filter_by(github_id=repo_data['id']).first()
        if not repository:
            # Create new repository record
            repository = Repository(
                name=repo_data['name'],
                full_name=repo_data['full_name'],
                github_id=repo_data['id'],
                url=repo_data['html_url'],
                clone_url=repo_data['clone_url'],
                description=repo_data.get('description', ''),
                language=repo_data.get('language', ''),
                stars=repo_data.get('stargazers_count', 0),
                forks=repo_data.get('forks_count', 0),
                open_issues=repo_data.get('open_issues_count', 0),
                private=repo_data.get('private', False)
            )
            db.session.add(repository)
            db.session.flush()  # Get the ID
        
        # Check if we've already processed this delivery
        existing_event = WebhookEvent.query.filter_by(github_delivery_id=delivery_id).first()
        if existing_event:
            logger.info(f"Webhook delivery {delivery_id} already processed")
            return jsonify({'message': 'Already processed', 'event_id': existing_event.id}), 200
        
        # Create webhook event record
        webhook_event = WebhookEvent(
            event_type=event_type,
            repository_id=repository.id,
            github_delivery_id=delivery_id
        )
        webhook_event.set_payload(payload)
        db.session.add(webhook_event)
        
        # Log the webhook receipt
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_entry = ActionLog(
            action_type='webhook_received',
            repository_id=repository.id,
            message=f"Received {event_type} webhook for {repository.full_name}",
            level='info',
            duration_ms=duration_ms
        )
        log_entry.set_details({
            'event_type': event_type,
            'delivery_id': delivery_id,
            'repository': repository.full_name,
            'payload_size': len(payload_body)
        })
        db.session.add(log_entry)
        
        db.session.commit()
        
        # Process the webhook asynchronously (in a real app, you'd use Celery or similar)
        # For now, we'll process it synchronously
        if event_type == 'push':
            process_push_event(webhook_event, payload)
        elif event_type == 'pull_request':
            process_pull_request_event(webhook_event, payload)
        
        logger.info(f"Successfully processed webhook {delivery_id} for {repository.full_name}")
        return jsonify({
            'message': 'Webhook processed successfully',
            'event_id': webhook_event.id,
            'event_type': event_type,
            'repository': repository.full_name
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook {delivery_id}: {str(e)}")
        db.session.rollback()
        
        # Log the error
        try:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            error_log = ActionLog(
                action_type='webhook_error',
                message=f"Failed to process webhook: {str(e)}",
                level='error',
                duration_ms=duration_ms
            )
            error_log.set_details({
                'error': str(e),
                'delivery_id': delivery_id,
                'event_type': event_type
            })
            db.session.add(error_log)
            db.session.commit()
        except:
            pass  # Don't fail if logging fails
        
        return jsonify({'error': 'Internal server error'}), 500

def process_push_event(webhook_event, payload):
    """Process a push event and analyze commits"""
    try:
        commits = payload.get('commits', [])
        repository = webhook_event.repository
        
        logger.info(f"Processing {len(commits)} commits for {repository.full_name}")
        
        for commit_data in commits:
            # Skip merge commits
            if len(commit_data.get('parents', [])) > 1:
                continue
            
            # Create commit analysis record
            commit_analysis = CommitAnalysis(
                webhook_event_id=webhook_event.id,
                repository_id=repository.id,
                commit_sha=commit_data['id'],
                commit_message=commit_data['message'],
                author_name=commit_data['author']['name'],
                author_email=commit_data['author']['email']
            )
            db.session.add(commit_analysis)
            db.session.flush()  # Get the ID
            
            # Analyze the commit with OpenAI
            try:
                openai_service = OpenAIService()
                analysis_result = openai_service.analyze_commit(commit_data, repository)
                
                commit_analysis.set_ai_analysis(analysis_result.get('analysis', {}))
                commit_analysis.set_suggestions(analysis_result.get('suggestions', []))
                commit_analysis.risk_score = analysis_result.get('risk_score', 0)
                commit_analysis.quality_score = analysis_result.get('quality_score', 0)
                commit_analysis.analyzed_at = datetime.utcnow()
                
                # Log successful analysis
                log_entry = ActionLog(
                    action_type='commit_analyzed',
                    repository_id=repository.id,
                    commit_analysis_id=commit_analysis.id,
                    message=f"Analyzed commit {commit_data['id'][:8]} by {commit_data['author']['name']}",
                    level='success'
                )
                log_entry.set_details({
                    'commit_sha': commit_data['id'],
                    'risk_score': commit_analysis.risk_score,
                    'quality_score': commit_analysis.quality_score,
                    'suggestions_count': len(analysis_result.get('suggestions', []))
                })
                db.session.add(log_entry)
                
                # Generate PR if needed
                if analysis_result.get('should_create_pr', False):
                    github_service = GitHubService()
                    pr_result = github_service.create_improvement_pr(
                        repository, 
                        commit_analysis, 
                        analysis_result
                    )
                    
                    if pr_result.get('success'):
                        commit_analysis.pr_generated = True
                        commit_analysis.pr_url = pr_result.get('pr_url')
                        commit_analysis.pr_title = pr_result.get('pr_title')
                        commit_analysis.pr_description = pr_result.get('pr_description')
                        
                        # Log PR generation
                        pr_log = ActionLog(
                            action_type='pr_generated',
                            repository_id=repository.id,
                            commit_analysis_id=commit_analysis.id,
                            message=f"Generated PR for commit {commit_data['id'][:8]}",
                            level='success'
                        )
                        pr_log.set_details({
                            'pr_url': pr_result.get('pr_url'),
                            'pr_title': pr_result.get('pr_title')
                        })
                        db.session.add(pr_log)
                
            except Exception as e:
                logger.error(f"Error analyzing commit {commit_data['id']}: {str(e)}")
                
                # Log analysis error
                error_log = ActionLog(
                    action_type='analysis_error',
                    repository_id=repository.id,
                    commit_analysis_id=commit_analysis.id,
                    message=f"Failed to analyze commit {commit_data['id'][:8]}: {str(e)}",
                    level='error'
                )
                error_log.set_details({
                    'commit_sha': commit_data['id'],
                    'error': str(e)
                })
                db.session.add(error_log)
        
        # Mark webhook as processed
        webhook_event.processed = True
        webhook_event.processed_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Successfully processed push event for {repository.full_name}")
        
    except Exception as e:
        logger.error(f"Error processing push event: {str(e)}")
        db.session.rollback()
        raise

def process_pull_request_event(webhook_event, payload):
    """Process a pull request event"""
    try:
        action = payload.get('action')
        pr_data = payload.get('pull_request', {})
        repository = webhook_event.repository
        
        logger.info(f"Processing PR {action} for {repository.full_name}")
        
        # Log PR event
        log_entry = ActionLog(
            action_type='pr_event',
            repository_id=repository.id,
            message=f"PR {action}: {pr_data.get('title', 'Unknown')}",
            level='info'
        )
        log_entry.set_details({
            'action': action,
            'pr_number': pr_data.get('number'),
            'pr_title': pr_data.get('title'),
            'pr_url': pr_data.get('html_url'),
            'author': pr_data.get('user', {}).get('login')
        })
        db.session.add(log_entry)
        
        # Mark webhook as processed
        webhook_event.processed = True
        webhook_event.processed_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Successfully processed PR event for {repository.full_name}")
        
    except Exception as e:
        logger.error(f"Error processing PR event: {str(e)}")
        db.session.rollback()
        raise

@webhook_bp.route('/webhook/events', methods=['GET'])
def get_webhook_events():
    """Get recent webhook events"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        events = WebhookEvent.query.order_by(WebhookEvent.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'events': [event.to_dict() for event in events.items],
            'total': events.total,
            'pages': events.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching webhook events: {str(e)}")
        return jsonify({'error': 'Failed to fetch events'}), 500

@webhook_bp.route('/webhook/commits', methods=['GET'])
def get_commit_analyses():
    """Get recent commit analyses"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        repository_id = request.args.get('repository_id', type=int)
        
        query = CommitAnalysis.query
        if repository_id:
            query = query.filter_by(repository_id=repository_id)
        
        analyses = query.order_by(CommitAnalysis.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'analyses': [analysis.to_dict() for analysis in analyses.items],
            'total': analyses.total,
            'pages': analyses.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching commit analyses: {str(e)}")
        return jsonify({'error': 'Failed to fetch analyses'}), 500

@webhook_bp.route('/webhook/logs', methods=['GET'])
def get_action_logs():
    """Get recent action logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        level = request.args.get('level')
        action_type = request.args.get('action_type')
        repository_id = request.args.get('repository_id', type=int)
        
        query = ActionLog.query
        if level:
            query = query.filter_by(level=level)
        if action_type:
            query = query.filter_by(action_type=action_type)
        if repository_id:
            query = query.filter_by(repository_id=repository_id)
        
        logs = query.order_by(ActionLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching action logs: {str(e)}")
        return jsonify({'error': 'Failed to fetch logs'}), 500

