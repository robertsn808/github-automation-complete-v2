import requests
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self, token=None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}' if self.token else '',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Automation-Bot/1.0'
        }
    
    def get_commit_details(self, repo_full_name, commit_sha):
        """Get detailed information about a specific commit"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/commits/{commit_sha}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching commit details for {commit_sha}: {str(e)}")
            return None
    
    def get_commit_diff(self, repo_full_name, commit_sha):
        """Get the diff for a specific commit"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/commits/{commit_sha}"
            headers = {**self.headers, 'Accept': 'application/vnd.github.v3.diff'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching commit diff for {commit_sha}: {str(e)}")
            return None
    
    def create_branch(self, repo_full_name, branch_name, base_sha):
        """Create a new branch from a base commit"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/git/refs"
            data = {
                'ref': f'refs/heads/{branch_name}',
                'sha': base_sha
            }
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {str(e)}")
            return None
    
    def create_file(self, repo_full_name, file_path, content, message, branch):
        """Create or update a file in the repository"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/contents/{file_path}"
            
            # Check if file exists
            try:
                existing_response = requests.get(url, headers=self.headers, params={'ref': branch})
                existing_file = existing_response.json() if existing_response.status_code == 200 else None
            except:
                existing_file = None
            
            data = {
                'message': message,
                'content': content,  # Should be base64 encoded
                'branch': branch
            }
            
            if existing_file and 'sha' in existing_file:
                data['sha'] = existing_file['sha']
            
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating/updating file {file_path}: {str(e)}")
            return None
    
    def create_pull_request(self, repo_full_name, title, body, head_branch, base_branch='main'):
        """Create a pull request"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/pulls"
            data = {
                'title': title,
                'body': body,
                'head': head_branch,
                'base': base_branch
            }
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}")
            return None
    
    def create_improvement_pr(self, repository, commit_analysis, analysis_result):
        """Create a PR with improvements based on commit analysis"""
        try:
            suggestions = analysis_result.get('suggestions', [])
            if not suggestions:
                return {'success': False, 'error': 'No suggestions to implement'}
            
            # Generate branch name
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            branch_name = f"auto-improvement-{commit_analysis.commit_sha[:8]}-{timestamp}"
            
            # Get the latest commit SHA for the default branch
            default_branch = 'main'  # You might want to get this from repository data
            latest_commit = self.get_latest_commit(repository.full_name, default_branch)
            if not latest_commit:
                return {'success': False, 'error': 'Could not get latest commit'}
            
            # Create new branch
            branch_result = self.create_branch(repository.full_name, branch_name, latest_commit['sha'])
            if not branch_result:
                return {'success': False, 'error': 'Could not create branch'}
            
            # Generate improvement files
            improvements_implemented = []
            for i, suggestion in enumerate(suggestions[:3]):  # Limit to 3 suggestions
                if suggestion.get('type') == 'code_improvement':
                    file_path = f"improvements/suggestion_{i+1}_{timestamp}.md"
                    content = self.generate_improvement_content(suggestion, commit_analysis)
                    
                    # Create the improvement file
                    file_result = self.create_file(
                        repository.full_name,
                        file_path,
                        content,
                        f"Add improvement suggestion: {suggestion.get('title', 'Code improvement')}",
                        branch_name
                    )
                    
                    if file_result:
                        improvements_implemented.append({
                            'file': file_path,
                            'title': suggestion.get('title', 'Code improvement'),
                            'description': suggestion.get('description', '')
                        })
            
            if not improvements_implemented:
                return {'success': False, 'error': 'No improvements could be implemented'}
            
            # Create PR
            pr_title = f"🤖 Auto-generated improvements for commit {commit_analysis.commit_sha[:8]}"
            pr_body = self.generate_pr_description(commit_analysis, improvements_implemented, analysis_result)
            
            pr_result = self.create_pull_request(
                repository.full_name,
                pr_title,
                pr_body,
                branch_name,
                default_branch
            )
            
            if pr_result:
                return {
                    'success': True,
                    'pr_url': pr_result['html_url'],
                    'pr_title': pr_title,
                    'pr_description': pr_body,
                    'branch_name': branch_name,
                    'improvements_count': len(improvements_implemented)
                }
            else:
                return {'success': False, 'error': 'Could not create pull request'}
                
        except Exception as e:
            logger.error(f"Error creating improvement PR: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_latest_commit(self, repo_full_name, branch):
        """Get the latest commit SHA for a branch"""
        try:
            url = f"{self.base_url}/repos/{repo_full_name}/branches/{branch}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()['commit']
        except Exception as e:
            logger.error(f"Error getting latest commit for {branch}: {str(e)}")
            return None
    
    def generate_improvement_content(self, suggestion, commit_analysis):
        """Generate content for an improvement file"""
        import base64
        
        content = f"""# Code Improvement Suggestion

## Original Commit
- **SHA**: {commit_analysis.commit_sha}
- **Message**: {commit_analysis.commit_message}
- **Author**: {commit_analysis.author_name} <{commit_analysis.author_email}>

## Suggestion Details
- **Type**: {suggestion.get('type', 'Unknown')}
- **Title**: {suggestion.get('title', 'Code Improvement')}
- **Priority**: {suggestion.get('priority', 'Medium')}

## Description
{suggestion.get('description', 'No description provided')}

## Implementation
{suggestion.get('implementation', 'Implementation details not provided')}

## Benefits
{suggestion.get('benefits', 'Benefits not specified')}

## Risk Assessment
- **Risk Level**: {suggestion.get('risk_level', 'Low')}
- **Impact**: {suggestion.get('impact', 'Minimal')}

---
*This improvement was automatically generated by the GitHub Automation Bot based on AI analysis.*
"""
        
        return base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    def generate_pr_description(self, commit_analysis, improvements, analysis_result):
        """Generate a comprehensive PR description"""
        description = f"""# 🤖 Automated Code Improvements

This PR contains automatically generated improvements based on AI analysis of commit `{commit_analysis.commit_sha[:8]}`.

## 📊 Analysis Summary
- **Risk Score**: {commit_analysis.risk_score}/100
- **Quality Score**: {commit_analysis.quality_score}/100
- **Commit Message**: {commit_analysis.commit_message}
- **Author**: {commit_analysis.author_name}

## 🔧 Improvements Implemented

"""
        
        for i, improvement in enumerate(improvements, 1):
            description += f"""### {i}. {improvement['title']}
- **File**: `{improvement['file']}`
- **Description**: {improvement['description']}

"""
        
        description += f"""## 🧠 AI Analysis Details

The AI analysis identified {len(analysis_result.get('suggestions', []))} potential improvements. This PR implements the top {len(improvements)} suggestions.

### Key Findings:
"""
        
        analysis = analysis_result.get('analysis', {})
        if analysis.get('code_quality'):
            description += f"- **Code Quality**: {analysis['code_quality']}\n"
        if analysis.get('security_concerns'):
            description += f"- **Security Concerns**: {analysis['security_concerns']}\n"
        if analysis.get('performance_notes'):
            description += f"- **Performance Notes**: {analysis['performance_notes']}\n"
        
        description += """
## ✅ Review Checklist
- [ ] Review the suggested improvements
- [ ] Test the changes in a development environment
- [ ] Verify that the improvements align with project standards
- [ ] Merge if the improvements add value

---
*This PR was automatically created by the GitHub Automation Bot. Please review carefully before merging.*
"""
        
        return description

