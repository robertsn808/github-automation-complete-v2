import openai
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Use the latest model
    
    def analyze_commit(self, commit_data, repository):
        """Analyze a commit and provide suggestions for improvements"""
        try:
            # Prepare commit information
            commit_info = {
                'sha': commit_data['id'],
                'message': commit_data['message'],
                'author': commit_data['author']['name'],
                'timestamp': commit_data['timestamp'],
                'added_files': commit_data.get('added', []),
                'modified_files': commit_data.get('modified', []),
                'removed_files': commit_data.get('removed', []),
                'url': commit_data.get('url', '')
            }
            
            # Create analysis prompt
            prompt = self.create_commit_analysis_prompt(commit_info, repository)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software engineer and code reviewer. Analyze commits and provide actionable improvement suggestions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content
            analysis_result = json.loads(analysis_text)
            
            # Validate and enhance the result
            return self.process_analysis_result(analysis_result, commit_info)
            
        except Exception as e:
            logger.error(f"Error analyzing commit {commit_data['id']}: {str(e)}")
            return self.create_fallback_analysis(commit_data)
    
    def create_commit_analysis_prompt(self, commit_info, repository):
        """Create a detailed prompt for commit analysis"""
        prompt = f"""Analyze this Git commit and provide detailed feedback and improvement suggestions.

## Repository Context
- **Name**: {repository.full_name}
- **Language**: {repository.language or 'Unknown'}
- **Description**: {repository.description or 'No description'}
- **Stars**: {repository.stars}
- **Private**: {repository.private}

## Commit Details
- **SHA**: {commit_info['sha']}
- **Message**: {commit_info['message']}
- **Author**: {commit_info['author']}
- **Timestamp**: {commit_info['timestamp']}

## File Changes
- **Added Files**: {len(commit_info['added_files'])} files
- **Modified Files**: {len(commit_info['modified_files'])} files  
- **Removed Files**: {len(commit_info['removed_files'])} files

### Files Added:
{chr(10).join(f"- {file}" for file in commit_info['added_files'][:10])}

### Files Modified:
{chr(10).join(f"- {file}" for file in commit_info['modified_files'][:10])}

### Files Removed:
{chr(10).join(f"- {file}" for file in commit_info['removed_files'][:10])}

## Analysis Requirements

Please provide a comprehensive analysis in JSON format with the following structure:

```json
{{
  "analysis": {{
    "commit_type": "feature|bugfix|refactor|docs|test|chore|hotfix",
    "complexity": "low|medium|high",
    "code_quality": "assessment of code quality based on commit message and files",
    "security_concerns": "any potential security issues identified",
    "performance_notes": "performance implications of the changes",
    "best_practices": "adherence to coding best practices",
    "testing_coverage": "assessment of testing implications"
  }},
  "risk_score": 25,
  "quality_score": 85,
  "suggestions": [
    {{
      "id": "suggestion_1",
      "type": "code_improvement|security|performance|testing|documentation",
      "title": "Brief title of the suggestion",
      "description": "Detailed description of the improvement",
      "priority": "low|medium|high|critical",
      "implementation": "Specific steps to implement this improvement",
      "benefits": "Expected benefits of implementing this suggestion",
      "risk_level": "low|medium|high",
      "impact": "Expected impact on the codebase",
      "files_affected": ["list", "of", "files"],
      "estimated_effort": "time estimate for implementation"
    }}
  ],
  "should_create_pr": false,
  "pr_suggestions": {{
    "title": "Suggested PR title if should_create_pr is true",
    "description": "Suggested PR description",
    "labels": ["suggested", "labels"]
  }},
  "follow_up_actions": [
    "List of recommended follow-up actions"
  ]
}}
```

## Analysis Guidelines

1. **Risk Score (0-100)**: Higher scores indicate more risky changes
   - 0-25: Low risk (documentation, minor fixes)
   - 26-50: Medium risk (feature additions, refactoring)
   - 51-75: High risk (major changes, architecture modifications)
   - 76-100: Critical risk (security changes, breaking changes)

2. **Quality Score (0-100)**: Higher scores indicate better quality
   - Consider commit message quality, file organization, naming conventions
   - Based on visible patterns in file names and commit message

3. **Suggestions**: Provide 1-5 actionable suggestions
   - Focus on improvements that can be implemented
   - Consider security, performance, maintainability, and testing
   - Be specific and actionable

4. **PR Creation**: Set should_create_pr to true only if:
   - There are high-value, low-risk improvements to implement
   - The suggestions would significantly benefit the codebase
   - The changes are non-breaking and safe to automate

Analyze this commit thoroughly and provide valuable insights and suggestions.
"""
        return prompt
    
    def process_analysis_result(self, analysis_result, commit_info):
        """Process and validate the analysis result"""
        try:
            # Ensure required fields exist
            if 'analysis' not in analysis_result:
                analysis_result['analysis'] = {}
            
            if 'suggestions' not in analysis_result:
                analysis_result['suggestions'] = []
            
            # Validate risk and quality scores
            analysis_result['risk_score'] = max(0, min(100, analysis_result.get('risk_score', 50)))
            analysis_result['quality_score'] = max(0, min(100, analysis_result.get('quality_score', 70)))
            
            # Add metadata
            analysis_result['metadata'] = {
                'analyzed_at': datetime.utcnow().isoformat(),
                'commit_sha': commit_info['sha'],
                'model_used': self.model,
                'suggestions_count': len(analysis_result['suggestions'])
            }
            
            # Enhance suggestions with IDs if missing
            for i, suggestion in enumerate(analysis_result['suggestions']):
                if 'id' not in suggestion:
                    suggestion['id'] = f"suggestion_{i+1}_{commit_info['sha'][:8]}"
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing analysis result: {str(e)}")
            return self.create_fallback_analysis(commit_info)
    
    def create_fallback_analysis(self, commit_data):
        """Create a basic fallback analysis if OpenAI fails"""
        return {
            'analysis': {
                'commit_type': 'unknown',
                'complexity': 'medium',
                'code_quality': 'Unable to analyze - API error',
                'security_concerns': 'Manual review recommended',
                'performance_notes': 'No analysis available',
                'best_practices': 'Manual review recommended',
                'testing_coverage': 'Unknown'
            },
            'risk_score': 50,
            'quality_score': 50,
            'suggestions': [
                {
                    'id': f"fallback_{commit_data['id'][:8]}",
                    'type': 'code_improvement',
                    'title': 'Manual Code Review Recommended',
                    'description': 'Automated analysis failed. Please conduct manual code review.',
                    'priority': 'medium',
                    'implementation': 'Perform manual code review of the changes',
                    'benefits': 'Ensures code quality and identifies potential issues',
                    'risk_level': 'low',
                    'impact': 'Maintains code quality standards',
                    'files_affected': commit_data.get('modified', []),
                    'estimated_effort': '30 minutes'
                }
            ],
            'should_create_pr': False,
            'pr_suggestions': {
                'title': 'Manual Review Required',
                'description': 'Automated analysis was not available for this commit.',
                'labels': ['manual-review']
            },
            'follow_up_actions': [
                'Conduct manual code review',
                'Check for security vulnerabilities',
                'Verify test coverage'
            ],
            'metadata': {
                'analyzed_at': datetime.utcnow().isoformat(),
                'commit_sha': commit_data['id'],
                'model_used': 'fallback',
                'error': 'OpenAI API unavailable'
            }
        }
    
    def generate_pr_improvements(self, repository, commit_analysis, suggestions):
        """Generate specific code improvements for a PR"""
        try:
            # Filter suggestions that are suitable for PR generation
            implementable_suggestions = [
                s for s in suggestions 
                if s.get('type') in ['code_improvement', 'documentation', 'testing'] 
                and s.get('risk_level') in ['low', 'medium']
                and s.get('priority') in ['medium', 'high']
            ]
            
            if not implementable_suggestions:
                return None
            
            # Create prompt for generating specific improvements
            prompt = f"""Generate specific code improvements for a GitHub repository based on commit analysis.

## Repository: {repository.full_name}
- **Language**: {repository.language}
- **Description**: {repository.description}

## Commit Analysis
- **SHA**: {commit_analysis.commit_sha}
- **Message**: {commit_analysis.commit_message}
- **Author**: {commit_analysis.author_name}
- **Risk Score**: {commit_analysis.risk_score}/100
- **Quality Score**: {commit_analysis.quality_score}/100

## Suggestions to Implement
{json.dumps(implementable_suggestions, indent=2)}

Generate specific, implementable improvements in JSON format:

```json
{{
  "improvements": [
    {{
      "suggestion_id": "reference to original suggestion",
      "file_path": "path/to/file/to/create/or/modify",
      "file_type": "markdown|code|config|documentation",
      "action": "create|modify|delete",
      "content": "complete file content or modification instructions",
      "commit_message": "descriptive commit message for this change",
      "justification": "why this improvement is valuable"
    }}
  ],
  "pr_metadata": {{
    "title": "Comprehensive PR title",
    "description": "Detailed PR description with context and benefits",
    "labels": ["improvement", "automated"],
    "estimated_impact": "description of expected positive impact"
  }}
}}
```

Focus on creating practical, valuable improvements that:
1. Are safe to implement automatically
2. Follow the repository's existing patterns and conventions
3. Provide clear value to the codebase
4. Include proper documentation and explanations

Generate improvements now:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert software engineer creating automated code improvements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            improvements = json.loads(response.choices[0].message.content)
            return improvements
            
        except Exception as e:
            logger.error(f"Error generating PR improvements: {str(e)}")
            return None
    
    def analyze_repository_health(self, repository_data, recent_commits):
        """Analyze overall repository health and provide recommendations"""
        try:
            prompt = f"""Analyze the overall health of this GitHub repository and provide strategic recommendations.

## Repository Overview
- **Name**: {repository_data.get('full_name')}
- **Language**: {repository_data.get('language')}
- **Stars**: {repository_data.get('stars', 0)}
- **Forks**: {repository_data.get('forks', 0)}
- **Open Issues**: {repository_data.get('open_issues', 0)}
- **Description**: {repository_data.get('description', 'No description')}
- **Private**: {repository_data.get('private', False)}

## Recent Commit Activity
{json.dumps(recent_commits[:10], indent=2)}

Provide a comprehensive health analysis in JSON format:

```json
{{
  "health_score": 85,
  "health_factors": {{
    "code_quality": 80,
    "activity_level": 90,
    "maintenance": 75,
    "documentation": 70,
    "community": 85,
    "security": 80
  }},
  "strengths": [
    "List of repository strengths"
  ],
  "concerns": [
    "List of areas needing attention"
  ],
  "recommendations": [
    {{
      "category": "code_quality|documentation|security|maintenance|community",
      "priority": "low|medium|high|critical",
      "title": "Recommendation title",
      "description": "Detailed recommendation",
      "implementation": "How to implement this recommendation",
      "expected_impact": "Expected positive impact"
    }}
  ],
  "trends": {{
    "commit_frequency": "analysis of commit patterns",
    "code_changes": "analysis of code change patterns",
    "issue_management": "assessment of issue handling"
  }},
  "next_steps": [
    "Prioritized list of next steps"
  ]
}}
```

Analyze this repository comprehensively:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior software architect analyzing repository health and providing strategic guidance."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            health_analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            health_analysis['metadata'] = {
                'analyzed_at': datetime.utcnow().isoformat(),
                'model_used': self.model,
                'repository': repository_data.get('full_name'),
                'commits_analyzed': len(recent_commits)
            }
            
            return health_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing repository health: {str(e)}")
            return {
                'health_score': 50,
                'error': str(e),
                'metadata': {
                    'analyzed_at': datetime.utcnow().isoformat(),
                    'error': 'Analysis failed'
                }
            }

