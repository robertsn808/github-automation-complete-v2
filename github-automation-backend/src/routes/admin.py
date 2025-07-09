from flask import Blueprint, request, jsonify, render_template_string
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from ..models.repository import Repository, Analysis, AutomationEntry
from ..models.webhook import WebhookEvent, CommitAnalysis, ActionLog, db
import json

admin_bp = Blueprint('admin', __name__)

# Admin Dashboard HTML Template
ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Automation - Admin Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .stat-card { transition: transform 0.2s; }
        .stat-card:hover { transform: translateY(-2px); }
        .log-level-info { @apply bg-blue-100 text-blue-800; }
        .log-level-success { @apply bg-green-100 text-green-800; }
        .log-level-warning { @apply bg-yellow-100 text-yellow-800; }
        .log-level-error { @apply bg-red-100 text-red-800; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-gray-800 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-xl font-bold">
                <i class="fas fa-robot mr-2"></i>
                GitHub Automation Admin
            </h1>
            <div class="flex space-x-4">
                <button onclick="refreshDashboard()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
                    <i class="fas fa-sync-alt mr-1"></i> Refresh
                </button>
                <button onclick="exportLogs()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded">
                    <i class="fas fa-download mr-1"></i> Export
                </button>
            </div>
        </div>
    </nav>

    <div class="container mx-auto p-6">
        <!-- Statistics Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="stat-card bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-600 text-sm">Total Repositories</p>
                        <p class="text-3xl font-bold text-blue-600" id="total-repos">-</p>
                    </div>
                    <i class="fas fa-code-branch text-blue-500 text-2xl"></i>
                </div>
            </div>
            
            <div class="stat-card bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-600 text-sm">Webhook Events</p>
                        <p class="text-3xl font-bold text-green-600" id="total-webhooks">-</p>
                    </div>
                    <i class="fas fa-webhook text-green-500 text-2xl"></i>
                </div>
            </div>
            
            <div class="stat-card bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-600 text-sm">Commit Analyses</p>
                        <p class="text-3xl font-bold text-purple-600" id="total-analyses">-</p>
                    </div>
                    <i class="fas fa-search text-purple-500 text-2xl"></i>
                </div>
            </div>
            
            <div class="stat-card bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-600 text-sm">PRs Generated</p>
                        <p class="text-3xl font-bold text-orange-600" id="total-prs">-</p>
                    </div>
                    <i class="fas fa-code-pull-request text-orange-500 text-2xl"></i>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">Activity Over Time</h3>
                <canvas id="activityChart" width="400" height="200"></canvas>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">Log Levels Distribution</h3>
                <canvas id="logLevelsChart" width="400" height="200"></canvas>
            </div>
        </div>

        <!-- Recent Activity and Logs -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Recent Webhook Events -->
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">
                    <i class="fas fa-clock mr-2"></i>Recent Webhook Events
                </h3>
                <div id="recent-webhooks" class="space-y-3">
                    <!-- Webhook events will be loaded here -->
                </div>
            </div>

            <!-- Recent Logs -->
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold mb-4">
                    <i class="fas fa-list mr-2"></i>Recent Logs
                </h3>
                <div class="mb-4">
                    <select id="log-level-filter" class="border rounded px-3 py-1" onchange="filterLogs()">
                        <option value="">All Levels</option>
                        <option value="info">Info</option>
                        <option value="success">Success</option>
                        <option value="warning">Warning</option>
                        <option value="error">Error</option>
                    </select>
                </div>
                <div id="recent-logs" class="space-y-2 max-h-96 overflow-y-auto">
                    <!-- Logs will be loaded here -->
                </div>
            </div>
        </div>

        <!-- Repository Management -->
        <div class="mt-8 bg-white p-6 rounded-lg shadow-md">
            <h3 class="text-lg font-semibold mb-4">
                <i class="fas fa-cogs mr-2"></i>Repository Management
            </h3>
            <div id="repository-list" class="overflow-x-auto">
                <!-- Repository table will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        let activityChart, logLevelsChart;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            loadDashboardData();
            
            // Auto-refresh every 30 seconds
            setInterval(loadDashboardData, 30000);
        });

        function initializeCharts() {
            // Activity Chart
            const activityCtx = document.getElementById('activityChart').getContext('2d');
            activityChart = new Chart(activityCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Webhook Events',
                        data: [],
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'Commit Analyses',
                        data: [],
                        borderColor: 'rgb(147, 51, 234)',
                        backgroundColor: 'rgba(147, 51, 234, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });

            // Log Levels Chart
            const logLevelsCtx = document.getElementById('logLevelsChart').getContext('2d');
            logLevelsChart = new Chart(logLevelsCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Info', 'Success', 'Warning', 'Error'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: [
                            'rgb(59, 130, 246)',
                            'rgb(34, 197, 94)',
                            'rgb(251, 191, 36)',
                            'rgb(239, 68, 68)'
                        ]
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }

        async function loadDashboardData() {
            try {
                // Load statistics
                const statsResponse = await fetch('/admin/api/statistics');
                const stats = await statsResponse.json();
                
                document.getElementById('total-repos').textContent = stats.total_repositories;
                document.getElementById('total-webhooks').textContent = stats.total_webhooks;
                document.getElementById('total-analyses').textContent = stats.total_analyses;
                document.getElementById('total-prs').textContent = stats.total_prs;

                // Load activity data
                const activityResponse = await fetch('/admin/api/activity');
                const activity = await activityResponse.json();
                
                activityChart.data.labels = activity.labels;
                activityChart.data.datasets[0].data = activity.webhooks;
                activityChart.data.datasets[1].data = activity.analyses;
                activityChart.update();

                // Load log levels data
                const logLevelsResponse = await fetch('/admin/api/log-levels');
                const logLevels = await logLevelsResponse.json();
                
                logLevelsChart.data.datasets[0].data = [
                    logLevels.info,
                    logLevels.success,
                    logLevels.warning,
                    logLevels.error
                ];
                logLevelsChart.update();

                // Load recent webhooks
                loadRecentWebhooks();
                
                // Load recent logs
                loadRecentLogs();
                
                // Load repositories
                loadRepositories();

            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }

        async function loadRecentWebhooks() {
            try {
                const response = await fetch('/webhook/events?per_page=5');
                const data = await response.json();
                
                const container = document.getElementById('recent-webhooks');
                container.innerHTML = '';
                
                data.events.forEach(event => {
                    const eventDiv = document.createElement('div');
                    eventDiv.className = 'border-l-4 border-blue-500 pl-4 py-2';
                    eventDiv.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div>
                                <p class="font-medium">${event.event_type}</p>
                                <p class="text-sm text-gray-600">Repository ID: ${event.repository_id}</p>
                            </div>
                            <span class="text-xs text-gray-500">${formatDate(event.created_at)}</span>
                        </div>
                    `;
                    container.appendChild(eventDiv);
                });
            } catch (error) {
                console.error('Error loading recent webhooks:', error);
            }
        }

        async function loadRecentLogs() {
            try {
                const level = document.getElementById('log-level-filter').value;
                const url = level ? `/webhook/logs?per_page=10&level=${level}` : '/webhook/logs?per_page=10';
                
                const response = await fetch(url);
                const data = await response.json();
                
                const container = document.getElementById('recent-logs');
                container.innerHTML = '';
                
                data.logs.forEach(log => {
                    const logDiv = document.createElement('div');
                    logDiv.className = `p-3 rounded border-l-4 log-level-${log.level}`;
                    logDiv.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div>
                                <p class="font-medium">${log.message}</p>
                                <p class="text-sm opacity-75">${log.action_type}</p>
                            </div>
                            <span class="text-xs opacity-75">${formatDate(log.created_at)}</span>
                        </div>
                    `;
                    container.appendChild(logDiv);
                });
            } catch (error) {
                console.error('Error loading recent logs:', error);
            }
        }

        async function loadRepositories() {
            try {
                const response = await fetch('/api/repositories');
                const data = await response.json();
                
                const container = document.getElementById('repository-list');
                
                let tableHTML = `
                    <table class="min-w-full table-auto">
                        <thead>
                            <tr class="bg-gray-50">
                                <th class="px-4 py-2 text-left">Repository</th>
                                <th class="px-4 py-2 text-left">Language</th>
                                <th class="px-4 py-2 text-left">Stars</th>
                                <th class="px-4 py-2 text-left">Last Analysis</th>
                                <th class="px-4 py-2 text-left">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.repositories.forEach(repo => {
                    tableHTML += `
                        <tr class="border-t">
                            <td class="px-4 py-2">
                                <div>
                                    <p class="font-medium">${repo.name}</p>
                                    <p class="text-sm text-gray-600">${repo.full_name}</p>
                                </div>
                            </td>
                            <td class="px-4 py-2">${repo.language || 'N/A'}</td>
                            <td class="px-4 py-2">${repo.stars}</td>
                            <td class="px-4 py-2">${repo.last_analysis ? formatDate(repo.last_analysis) : 'Never'}</td>
                            <td class="px-4 py-2">
                                <button onclick="viewRepository(${repo.id})" class="text-blue-600 hover:text-blue-800">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                tableHTML += '</tbody></table>';
                container.innerHTML = tableHTML;
                
            } catch (error) {
                console.error('Error loading repositories:', error);
            }
        }

        function filterLogs() {
            loadRecentLogs();
        }

        function refreshDashboard() {
            loadDashboardData();
        }

        function exportLogs() {
            window.open('/admin/api/export-logs', '_blank');
        }

        function viewRepository(id) {
            // Implement repository detail view
            alert(`View repository details for ID: ${id}`);
        }

        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString();
        }
    </script>
</body>
</html>
"""

@admin_bp.route('/admin')
def admin_dashboard():
    """Serve the admin dashboard"""
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE)

@admin_bp.route('/admin/api/statistics')
def get_statistics():
    """Get dashboard statistics"""
    try:
        # Get basic counts
        total_repositories = Repository.query.count()
        total_webhooks = WebhookEvent.query.count()
        total_analyses = CommitAnalysis.query.count()
        total_prs = CommitAnalysis.query.filter_by(pr_generated=True).count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_webhooks = WebhookEvent.query.filter(WebhookEvent.created_at >= yesterday).count()
        recent_analyses = CommitAnalysis.query.filter(CommitAnalysis.created_at >= yesterday).count()
        
        # Get processing statistics
        processed_webhooks = WebhookEvent.query.filter_by(processed=True).count()
        processing_rate = (processed_webhooks / total_webhooks * 100) if total_webhooks > 0 else 0
        
        return jsonify({
            'total_repositories': total_repositories,
            'total_webhooks': total_webhooks,
            'total_analyses': total_analyses,
            'total_prs': total_prs,
            'recent_webhooks': recent_webhooks,
            'recent_analyses': recent_analyses,
            'processing_rate': round(processing_rate, 1)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/activity')
def get_activity_data():
    """Get activity data for charts"""
    try:
        # Get data for the last 7 days
        days = []
        webhook_counts = []
        analysis_counts = []
        
        for i in range(6, -1, -1):
            date = datetime.utcnow() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            webhook_count = WebhookEvent.query.filter(
                WebhookEvent.created_at >= start_of_day,
                WebhookEvent.created_at < end_of_day
            ).count()
            
            analysis_count = CommitAnalysis.query.filter(
                CommitAnalysis.created_at >= start_of_day,
                CommitAnalysis.created_at < end_of_day
            ).count()
            
            days.append(date.strftime('%m/%d'))
            webhook_counts.append(webhook_count)
            analysis_counts.append(analysis_count)
        
        return jsonify({
            'labels': days,
            'webhooks': webhook_counts,
            'analyses': analysis_counts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/log-levels')
def get_log_levels():
    """Get log level distribution"""
    try:
        # Get counts for each log level
        info_count = ActionLog.query.filter_by(level='info').count()
        success_count = ActionLog.query.filter_by(level='success').count()
        warning_count = ActionLog.query.filter_by(level='warning').count()
        error_count = ActionLog.query.filter_by(level='error').count()
        
        return jsonify({
            'info': info_count,
            'success': success_count,
            'warning': warning_count,
            'error': error_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/repositories')
def get_repositories_admin():
    """Get repositories with admin details"""
    try:
        repositories = db.session.query(
            Repository,
            func.max(Analysis.created_at).label('last_analysis')
        ).outerjoin(Analysis).group_by(Repository.id).all()
        
        result = []
        for repo, last_analysis in repositories:
            repo_dict = repo.to_dict()
            repo_dict['last_analysis'] = last_analysis.isoformat() if last_analysis else None
            
            # Add webhook and analysis counts
            repo_dict['webhook_count'] = WebhookEvent.query.filter_by(repository_id=repo.id).count()
            repo_dict['analysis_count'] = Analysis.query.filter_by(repository_id=repo.id).count()
            repo_dict['commit_analysis_count'] = CommitAnalysis.query.filter_by(repository_id=repo.id).count()
            
            result.append(repo_dict)
        
        return jsonify({'repositories': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/repository/<int:repo_id>')
def get_repository_details(repo_id):
    """Get detailed information about a specific repository"""
    try:
        repository = Repository.query.get_or_404(repo_id)
        
        # Get recent webhook events
        recent_webhooks = WebhookEvent.query.filter_by(repository_id=repo_id)\
            .order_by(desc(WebhookEvent.created_at)).limit(10).all()
        
        # Get recent commit analyses
        recent_analyses = CommitAnalysis.query.filter_by(repository_id=repo_id)\
            .order_by(desc(CommitAnalysis.created_at)).limit(10).all()
        
        # Get recent logs
        recent_logs = ActionLog.query.filter_by(repository_id=repo_id)\
            .order_by(desc(ActionLog.created_at)).limit(20).all()
        
        # Calculate statistics
        total_commits_analyzed = CommitAnalysis.query.filter_by(repository_id=repo_id).count()
        prs_generated = CommitAnalysis.query.filter_by(repository_id=repo_id, pr_generated=True).count()
        avg_risk_score = db.session.query(func.avg(CommitAnalysis.risk_score))\
            .filter_by(repository_id=repo_id).scalar() or 0
        avg_quality_score = db.session.query(func.avg(CommitAnalysis.quality_score))\
            .filter_by(repository_id=repo_id).scalar() or 0
        
        return jsonify({
            'repository': repository.to_dict(),
            'statistics': {
                'total_commits_analyzed': total_commits_analyzed,
                'prs_generated': prs_generated,
                'avg_risk_score': round(avg_risk_score, 1),
                'avg_quality_score': round(avg_quality_score, 1)
            },
            'recent_webhooks': [webhook.to_dict() for webhook in recent_webhooks],
            'recent_analyses': [analysis.to_dict() for analysis in recent_analyses],
            'recent_logs': [log.to_dict() for log in recent_logs]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/export-logs')
def export_logs():
    """Export logs as CSV"""
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        # Get logs from the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        logs = ActionLog.query.filter(ActionLog.created_at >= thirty_days_ago)\
            .order_by(desc(ActionLog.created_at)).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Timestamp', 'Action Type', 'Level', 'Message', 
            'Repository ID', 'Commit Analysis ID', 'Duration (ms)', 'Details'
        ])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.isoformat(),
                log.action_type,
                log.level,
                log.message,
                log.repository_id,
                log.commit_analysis_id,
                log.duration_ms,
                json.dumps(log.get_details()) if log.details else ''
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=github_automation_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/system-health')
def get_system_health():
    """Get system health information"""
    try:
        # Database connection test
        db_healthy = True
        try:
            db.session.execute('SELECT 1')
        except:
            db_healthy = False
        
        # Get recent error rate
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        total_logs = ActionLog.query.filter(ActionLog.created_at >= one_hour_ago).count()
        error_logs = ActionLog.query.filter(
            ActionLog.created_at >= one_hour_ago,
            ActionLog.level == 'error'
        ).count()
        
        error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
        
        # Get processing queue status
        unprocessed_webhooks = WebhookEvent.query.filter_by(processed=False).count()
        
        # Get average processing time
        avg_processing_time = db.session.query(func.avg(ActionLog.duration_ms))\
            .filter(ActionLog.duration_ms.isnot(None)).scalar() or 0
        
        return jsonify({
            'database_healthy': db_healthy,
            'error_rate_1h': round(error_rate, 2),
            'unprocessed_webhooks': unprocessed_webhooks,
            'avg_processing_time_ms': round(avg_processing_time, 2),
            'system_status': 'healthy' if db_healthy and error_rate < 10 else 'warning'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

