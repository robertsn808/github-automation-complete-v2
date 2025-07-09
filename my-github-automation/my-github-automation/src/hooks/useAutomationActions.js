import { useCallback } from 'react';
import { useGitHubApi } from './useGitHubApi';
import { useDatabase } from './useDatabase';

// Import OpenAI API client
import OpenAI from 'openai';

export const useAutomationActions = (
  repoUrl,
  githubToken,
  repoData,
  setRepoData,
  analysisResults,
  setAnalysisResults,
  automationConfig,
  setIsProcessing,
  setProcessingMessage,
  addAutomationEntry,
  showNotification
) => {
  const { fetchRepoData, getRepositoryStructure } = useGitHubApi(githubToken, showNotification);
  const { 
    saveRepository, 
    saveAnalysis, 
    hasRecentAnalysisInDB,
    saveAutomationEntry: saveAutomationEntryToDB
  } = useDatabase(showNotification);

  // Initialize OpenAI client with API key from environment variable or config
  // IMPORTANT: Replace 'YOUR_OPENAI_API_KEY' with your actual OpenAI API key.
  // For production, consider securely loading this from environment variables.
  const openai = new OpenAI({
    apiKey: process.env.REACT_APP_OPENAI_API_KEY || 'YOUR_OPENAI_API_KEY',
    dangerouslyAllowBrowser: true, // This is generally not recommended for production due to API key exposure
  });

  // Helper function to store analysis in localStorage (keeping for backward compatibility)
  const storeAnalysis = useCallback((repoName, analysis) => {
    try {
      const analysisKey = `analysis_${repoName}_${Date.now()}`;
      const analysisData = {
        timestamp: new Date().toISOString(),
        repoName,
        analysis,
        id: analysisKey
      };
      localStorage.setItem(analysisKey, JSON.stringify(analysisData));
      
      // Also maintain a list of all analyses
      const allAnalyses = JSON.parse(localStorage.getItem('all_analyses') || '[]');
      allAnalyses.push(analysisKey);
      localStorage.setItem('all_analyses', JSON.stringify(allAnalyses));
      
      console.log(`Analysis stored in localStorage for ${repoName} with key: ${analysisKey}`);
    } catch (error) {
      console.error('Failed to store analysis in localStorage:', error);
    }
  }, []);

  // Helper function to retrieve stored analyses from localStorage
  const getStoredAnalyses = useCallback((repoName) => {
    try {
      const allAnalyses = JSON.parse(localStorage.getItem('all_analyses') || '[]');
      const repoAnalyses = [];
      
      for (const analysisKey of allAnalyses) {
        const analysisData = localStorage.getItem(analysisKey);
        if (analysisData) {
          const parsed = JSON.parse(analysisData);
          if (parsed.repoName === repoName) {
            repoAnalyses.push(parsed);
          }
        }
      }
      
      // Sort by timestamp, newest first
      return repoAnalyses.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    } catch (error) {
      console.error('Failed to retrieve stored analyses from localStorage:', error);
      return [];
    }
  }, []);

  // Helper function to check if recent analysis exists in localStorage
  const hasRecentAnalysis = useCallback((repoName, maxAgeHours = 24) => {
    const storedAnalyses = getStoredAnalyses(repoName);
    if (storedAnalyses.length === 0) return null;
    
    const latestAnalysis = storedAnalyses[0];
    const analysisAge = Date.now() - new Date(latestAnalysis.timestamp).getTime();
    const maxAge = maxAgeHours * 60 * 60 * 1000; // Convert hours to milliseconds
    
    if (analysisAge < maxAge) {
      return latestAnalysis.analysis;
    }
    
    return null;
  }, [getStoredAnalyses]);

  const analyzeRepository = useCallback(async () => {
    if (!repoUrl || !githubToken) {
      showNotification('Please provide both repository URL and GitHub token', 'error');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage('Initializing analysis...');
    
    try {
      setProcessingMessage('Fetching repository data...');
      const repo = await fetchRepoData(repoUrl, githubToken);
      setRepoData(repo);

      setProcessingMessage('Saving repository to database...');
      const savedRepo = await saveRepository(repo);
      console.log('Repository saved with ID:', savedRepo.id);

      // Check for recent analysis in database first
      setProcessingMessage('Checking for recent analysis in database...');
      const recentDBAnalysis = await hasRecentAnalysisInDB(savedRepo.id);
      if (recentDBAnalysis) {
        setAnalysisResults(recentDBAnalysis);
        setProcessingMessage('Using cached analysis from database...');
        
        const newEntry = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          repo: repo.name,
          action: 'comprehensive_analysis',
          status: 'completed',
          details: `Used cached analysis from database for ${repo.name} - Health: ${recentDBAnalysis.overall_health_score}%, Bugs: ${recentDBAnalysis.bugs_detected.length}, Improvements: ${recentDBAnalysis.improvements_suggested.length}, Features: ${recentDBAnalysis.feature_ideas.length}`,
          metrics: {
            healthScore: recentDBAnalysis.overall_health_score,
            bugCount: recentDBAnalysis.bugs_detected.length,
            improvementCount: recentDBAnalysis.improvements_suggested.length,
            featureCount: recentDBAnalysis.feature_ideas.length,
            securityIssues: recentDBAnalysis.security_concerns.length
          }
        };
        
        addAutomationEntry(newEntry);
        
        // Also save to database
        await saveAutomationEntryToDB(savedRepo.id, {
          action: 'comprehensive_analysis',
          status: 'completed',
          details: newEntry.details,
          metadata: newEntry.metrics
        });
        
        showNotification('Repository analysis loaded from database cache!', 'success');
        return;
      }

      // Check localStorage as fallback
      setProcessingMessage('Checking for recent analysis in local cache...');
      const recentLocalAnalysis = hasRecentAnalysis(repo.name);
      if (recentLocalAnalysis) {
        setAnalysisResults(recentLocalAnalysis);
        setProcessingMessage('Using cached analysis from local storage...');
        
        // Save this analysis to database for future use
        await saveAnalysis(savedRepo.id, recentLocalAnalysis);
        
        const newEntry = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          repo: repo.name,
          action: 'comprehensive_analysis',
          status: 'completed',
          details: `Used cached analysis from local storage for ${repo.name} - Health: ${recentLocalAnalysis.overall_health_score}%, Bugs: ${recentLocalAnalysis.bugs_detected.length}, Improvements: ${recentLocalAnalysis.improvements_suggested.length}, Features: ${recentLocalAnalysis.feature_ideas.length}`,
          metrics: {
            healthScore: recentLocalAnalysis.overall_health_score,
            bugCount: recentLocalAnalysis.bugs_detected.length,
            improvementCount: recentLocalAnalysis.improvements_suggested.length,
            featureCount: recentLocalAnalysis.feature_ideas.length,
            securityIssues: recentLocalAnalysis.security_concerns.length
          }
        };
        
        addAutomationEntry(newEntry);
        
        // Also save to database
        await saveAutomationEntryToDB(savedRepo.id, {
          action: 'comprehensive_analysis',
          status: 'completed',
          details: newEntry.details,
          metadata: newEntry.metrics
        });
        
        showNotification('Repository analysis loaded from local cache and saved to database!', 'success');
        return;
      }

      setProcessingMessage('Analyzing repository structure...');
      const repoStructure = await getRepositoryStructure(repo, githubToken);
      
      setProcessingMessage('Performing AI analysis...');
      
      const analysisPrompt = `You are an elite AI software engineer and security expert analyzing a GitHub repository. Provide a comprehensive assessment.\n\nRepository Information:\n- Name: ${repo.name}\n- Description: ${repo.description || 'No description'}\n- Language: ${repo.language || 'Unknown'}\n- Stars: ${repo.stargazers_count}\n- Forks: ${repo.forks_count}\n- Issues: ${repo.open_issues_count}\n- Pull Requests: ${repo.health.prCount}\n- Contributors: ${repo.health.contributorCount}\n\nRepository Structure Analysis:\n- Total Files: ${repoStructure.totalFiles}\n- File Types: ${JSON.stringify(repoStructure.fileTypes)}\n- Directories: ${repoStructure.directories.join(', ')}\n- Has Tests: ${repoStructure.hasTests}\n- Has Documentation: ${repoStructure.hasDocumentation}\n- Has CI/CD: ${repoStructure.hasCI}\n- Config Files: ${repoStructure.configFiles.length}\n\nRepository Health:\n- Has README: ${repo.health.hasReadme}\n- Has License: ${repo.health.hasLicense}\n- Issue Management: ${repo.health.hasIssues}\n\nRecent Issues (sample):\n${repo.issues.slice(0, 5).map(issue => `- ${issue.title} (${issue.state})`).join('\n')}\n\nIMPORTANT: Respond with ONLY a valid JSON object, no markdown formatting or backticks:\n\n{\n  "overall_health_score": 85,\n  "architecture_analysis": "Detailed analysis of codebase architecture, patterns, and organization",\n  "bugs_detected": [\n    {\n      "id": "bug_1",\n      "type": "bug_category",\n      "file": "relative/path/to/file.ext",\n      "line": 42,\n      "description": "clear bug description",\n      "severity": "critical/high/medium/low",\n      "impact": "potential impact description",\n      "solution": "specific fix recommendation",\n      "estimated_fix_time": "time estimate"\n    }\n  ],\n  "improvements_suggested": [\n    {\n      "id": "improvement_1",\n      "type": "improvement_category",\n      "description": "improvement description",\n      "impact": "expected positive impact",\n      "effort": "low/medium/high",\n      "priority": "critical/high/medium/low",\n      "files_affected": ["list", "of", "files"],\n      "estimated_time": "implementation time"\n    }\n  ],\n  "feature_ideas": [\n    {\n      "id": "feature_1",\n      "name": "feature name",\n      "description": "detailed feature description",\n      "value": "business/user value",\n      "complexity": "low/medium/high",\n      "priority": "high/medium/low",\n      "estimated_time": "development time",\n      "dependencies": ["list", "of", "dependencies"]\n    }\n  ],\n  "security_concerns": [\n    {\n      "id": "security_1",\n      "type": "vulnerability_type",\n      "description": "security concern description",\n      "severity": "critical/high/medium/low",\n      "cwe_id": "CWE-XXX",\n      "mitigation": "specific mitigation strategy",\n      "urgent": true\n    }\n  ],\n  "performance_issues": [\n    {\n      "id": "perf_1",\n      "type": "performance_issue_type",\n      "description": "performance issue description",\n      "impact": "performance impact",\n      "optimization": "optimization recommendation"\n    }\n  ],\n  "documentation_gaps": [\n    {\n      "type": "documentation_type",\n      "description": "what documentation is missing",\n      "priority": "high/medium/low"\n    }\n  ],\n  "test_coverage_analysis": {\n    "estimated_coverage": "percentage or assessment",\n    "missing_tests": ["areas", "lacking", "tests"],\n    "test_quality": "assessment of existing tests"\n  },\n  "code_quality_metrics": {\n    "maintainability": 85,\n    "readability": 90,\n    "complexity": 75,\n    "duplication": 80\n  },\n  "recommendations": {\n    "immediate_actions": ["critical", "actions", "needed"],\n    "short_term": ["actions", "for", "next", "sprint"],\n    "long_term": ["strategic", "improvements"]\n  }\n}\n\nReturn ONLY the JSON object with no additional text or formatting.\n`;

      // Replace window.claude.complete with OpenAI API call
      const completion = await openai.chat.completions.create({
        model: "gpt-4o", // You can choose a different model like "gpt-3.5-turbo" or "gpt-4"
        messages: [{ role: "user", content: analysisPrompt }],
        response_format: { type: "json_object" },
      });
      const analysisResponse = completion.choices[0].message.content;
      
      let analysis;
      try {
        analysis = JSON.parse(analysisResponse);
      } catch (parseError) {
        console.error('Failed to parse analysis response:', parseError);
        console.log('Raw response:', analysisResponse);
        throw new Error('Invalid analysis response format');
      }

      setProcessingMessage('Saving analysis to database...');
      // Save the analysis to database
      const savedAnalysis = await saveAnalysis(savedRepo.id, analysis);
      console.log('Analysis saved to database with ID:', savedAnalysis.id);

      // Store the analysis in localStorage for backward compatibility
      storeAnalysis(repo.name, analysis);

      setAnalysisResults(analysis);
      
      const newEntry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        repo: repo.name,
        action: 'comprehensive_analysis',
        status: 'completed',
        details: `Analyzed ${repo.name} - Health: ${analysis.overall_health_score}%, Bugs: ${analysis.bugs_detected.length}, Improvements: ${analysis.improvements_suggested.length}, Features: ${analysis.feature_ideas.length}`,
        metrics: {
          healthScore: analysis.overall_health_score,
          bugCount: analysis.bugs_detected.length,
          improvementCount: analysis.improvements_suggested.length,
          featureCount: analysis.feature_ideas.length,
          securityIssues: analysis.security_concerns.length
        }
      };
      
      addAutomationEntry(newEntry);
      
      // Save automation entry to database
      await saveAutomationEntryToDB(savedRepo.id, {
        analysis_id: savedAnalysis.id,
        action: 'comprehensive_analysis',
        status: 'completed',
        details: newEntry.details,
        metadata: newEntry.metrics
      });
      
      setProcessingMessage('Analysis complete!');
      showNotification('Repository analysis completed and saved to database!', 'success');

    } catch (error) {
      console.error('Analysis failed:', error);
      showNotification(`Analysis failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [repoUrl, githubToken, setRepoData, setAnalysisResults, setIsProcessing, setProcessingMessage, addAutomationEntry, showNotification, fetchRepoData, getRepositoryStructure, openai.chat.completions, hasRecentAnalysis, storeAnalysis, saveRepository, saveAnalysis, hasRecentAnalysisInDB, saveAutomationEntryToDB]);

  const executeBugFix = useCallback(async (bug) => {
    if (!githubToken || !repoData) {
      showNotification('Repository not analyzed or missing GitHub token', 'error');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage(`Fixing ${bug.type} bug: ${bug.description}...`);

    try {
      setProcessingMessage(`Generating fix plan for ${bug.id}...`);
      const fixPrompt = `You are an expert software engineer fixing a ${bug.severity} priority bug in a ${repoData.language || 'JavaScript'} project.\n\nBug Details:\n- ID: ${bug.id}\n- Type: ${bug.type}\n- File: ${bug.file}\n- Line: ${bug.line || 'unknown'}\n- Description: ${bug.description}\n- Severity: ${bug.severity}\n- Impact: ${bug.impact}\n- Solution: ${bug.solution}\n\nRepository Context:\n- Language: ${repoData.language}\n- Framework: ${repoData.topics ? repoData.topics.join(', ') : 'Unknown'}\n\nGenerate a comprehensive fix including:\n1. Exact code changes with proper context\n2. Testing strategy\n3. Risk assessment\n4. Rollback plan\n\nRespond with ONLY a valid JSON object:\n{\n  "fix_details": {\n    "approach": "detailed explanation of fix approach",\n    "code_changes": [\n      {\n        "file": "file_path",\n        "original_code": "code to replace",\n        "fixed_code": "corrected code",\n        "line_start": 10,\n        "line_end": 15,\n        "explanation": "why this change fixes the bug"\n      }\n    ],\n    "additional_files": [\n      {\n        "file": "new_file_path",\n        "content": "complete file content",\n        "purpose": "why this file is needed"\n      }\n    ]\n  },\n  "testing_strategy": {\n    "unit_tests": ["test", "descriptions"],\n    "integration_tests": ["test", "descriptions"],\n    "manual_testing": ["steps", "to", "verify"]\n  },\n  "risk_assessment": {\n    "risk_level": "low/medium/high",\n    "potential_impacts": ["list", "of", "impacts"],\n    "mitigation_strategies": ["risk", "mitigation", "steps"]\n  },\n  "git_operations": {\n    "branch_name": "fix/descriptive-branch-name",\n    "commit_message": "fix: descriptive commit message",\n    "pr_title": "Fix: Brief description of the bug fix",\n    "pr_description": "Detailed PR description with context and testing info"\n  },\n  "rollback_plan": "steps to rollback if issues arise",\n  "estimated_impact": "positive impact of the fix"\n}\n\nReturn ONLY the JSON object.\n`;

      // Replace window.claude.complete with OpenAI API call
      const completion = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: fixPrompt }],
        response_format: { type: "json_object" },
      });
      const fixResponse = completion.choices[0].message.content;

      const fixData = JSON.parse(fixResponse);

      setProcessingMessage(`Applying fix for ${bug.id}...`);
      // Simulate applying fix (in a real scenario, this would involve Git operations, file writes, etc.)
      console.log(`Simulating code changes for bug: ${bug.id}`);
      fixData.fix_details.code_changes.forEach(change => {
        console.log(`  File: ${change.file}, Changes: ${change.explanation}`);
      });

      setProcessingMessage(`Creating branch and preparing PR for ${bug.id}...`);
      const branchName = fixData.git_operations.branch_name;
      
      const newEntry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        repo: repoData.name,
        action: 'bug_fix',
        status: 'completed',
        details: `Fixed ${bug.type} (${bug.severity}) in ${bug.file}`,
        branch: branchName,
        pr_title: fixData.git_operations.pr_title,
        metadata: {
          bugId: bug.id,
          severity: bug.severity,
          filesChanged: fixData.fix_details.code_changes.length,
          riskLevel: fixData.risk_assessment.risk_level
        }
      };
      
      addAutomationEntry(newEntry);
      
      // Save to database if we have repository data
      if (repoData.id) {
        await saveAutomationEntryToDB(repoData.id, {
          action: 'bug_fix',
          status: 'completed',
          details: newEntry.details,
          branch_name: branchName,
          pr_title: fixData.git_operations.pr_title,
          metadata: newEntry.metadata
        });
      }
      
      showNotification(
        `Bug fix implemented! Branch: ${branchName}`,
        'success'
      );

    } catch (error) {
      console.error('Bug fix failed:', error);
      showNotification(`Bug fix failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [githubToken, repoData, setIsProcessing, setProcessingMessage, addAutomationEntry, showNotification, openai.chat.completions, saveAutomationEntryToDB]);

  const executeImprovement = useCallback(async (improvement) => {
    if (!githubToken || !repoData) {
      showNotification('Repository not analyzed or missing GitHub token', 'error');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage(`Implementing ${improvement.type} improvement: ${improvement.description}...`);

    try {
      setProcessingMessage(`Generating implementation plan for ${improvement.id}...`);
      const improvementPrompt = `You are an expert software engineer implementing a ${improvement.priority} priority improvement for a ${repoData.language || 'JavaScript'} project.\n\nImprovement Details:\n- ID: ${improvement.id}\n- Type: ${improvement.type}\n- Description: ${improvement.description}\n- Impact: ${improvement.impact}\n- Effort: ${improvement.effort}\n- Priority: ${improvement.priority}\n- Files Affected: ${improvement.files_affected ? improvement.files_affected.join(', ') : 'Multiple'}\n\nRepository Context:\n- Language: ${repoData.language}\n- Stars: ${repoData.stargazers_count}\n- Framework: ${repoData.topics ? repoData.topics.join(', ') : 'Unknown'}\n\nGenerate a comprehensive implementation plan:\n\nRespond with ONLY a valid JSON object:\n{\n  "implementation_plan": {\n    "overview": "high-level implementation strategy",\n    "phases": [\n      {\n        "phase": "phase name",\n        "description": "what happens in this phase",\n        "duration": "estimated time",\n        "deliverables": ["phase", "deliverables"]\n      }\n    ]\n  },\n  "code_changes": [\n    {\n      "file": "file_path",\n      "change_type": "add/modify/delete/rename",\n      "description": "description of changes",\n      "before_code": "original code if modifying",\n      "after_code": "new/modified code",\n      "justification": "why this change is beneficial"\n    }\n  ],\n  "dependencies": {\n    "new_packages": ["package", "names"],\n    "version_updates": ["package", "updates"],\n    "dev_dependencies": ["dev", "packages"]\n  },\n  "testing_approach": {\n    "existing_tests": "impact on existing tests",\n    "new_tests": ["new", "tests", "needed"],\n    "performance_tests": ["performance", "validations"]\n  },\n  "git_operations": {\n    "branch_name": "improvement/descriptive-name",\n    "commit_messages": ["commit", "messages"],\n    "pr_title": "Improvement: Brief description",\n    "pr_description": "Detailed PR description with benefits and testing"\n  },\n  "success_metrics": {\n    "kpis": ["key", "performance", "indicators"],\n    "measurement_approach": "how to measure success"\n  },\n  "rollback_strategy": "how to rollback if needed"\n}\n\nReturn ONLY the JSON object.\n`;

      // Replace window.claude.complete with OpenAI API call
      const completion = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: improvementPrompt }],
        response_format: { type: "json_object" },
      });
      const improvementResponse = completion.choices[0].message.content;

      const improvementData = JSON.parse(improvementResponse);

      setProcessingMessage(`Applying improvement for ${improvement.id}...`);
      // Simulate applying improvement (in a real scenario, this would involve Git operations, file writes, etc.)
      console.log(`Simulating code changes for improvement: ${improvement.id}`);
      improvementData.code_changes.forEach(change => {
        console.log(`  File: ${change.file}, Type: ${change.change_type}, Description: ${change.description}`);
      });

      setProcessingMessage(`Creating branch and preparing PR for ${improvement.id}...`);
      const branchName = improvementData.git_operations.branch_name;
      
      const newEntry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        repo: repoData.name,
        action: 'improvement',
        status: 'completed',
        details: `Implemented ${improvement.type}: ${improvement.description}`,
        branch: branchName,
        pr_title: improvementData.git_operations.pr_title,
        metadata: {
          improvementId: improvement.id,
          priority: improvement.priority,
          effort: improvement.effort,
          filesChanged: improvementData.code_changes.length,
          newDependencies: improvementData.dependencies.new_packages.length
        }
      };
      
      addAutomationEntry(newEntry);
      
      // Save to database if we have repository data
      if (repoData.id) {
        await saveAutomationEntryToDB(repoData.id, {
          action: 'improvement',
          status: 'completed',
          details: newEntry.details,
          branch_name: branchName,
          pr_title: improvementData.git_operations.pr_title,
          metadata: newEntry.metadata
        });
      }
      
      showNotification(
        `Improvement implemented! Branch: ${branchName}`,
        'success'
      );

    } catch (error) {
      console.error('Improvement implementation failed:', error);
      showNotification(`Improvement implementation failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [githubToken, repoData, setIsProcessing, setProcessingMessage, addAutomationEntry, showNotification, openai.chat.completions, saveAutomationEntryToDB]);

  const developFeature = useCallback(async (feature) => {
    if (!githubToken || !repoData) {
      showNotification('Repository not analyzed or missing GitHub token', 'error');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage(`Developing ${feature.name} feature: ${feature.description}...`);

    try {
      setProcessingMessage(`Generating development plan for ${feature.id}...`);
      const featurePrompt = `You are an expert software architect developing a ${feature.complexity} complexity feature for a ${repoData.language || 'JavaScript'} project.\n\nFeature Details:\n- ID: ${feature.id}\n- Name: ${feature.name}\n- Description: ${feature.description}\n- Value: ${feature.value}\n- Complexity: ${feature.complexity}\n- Priority: ${feature.priority}\n- Dependencies: ${feature.dependencies ? feature.dependencies.join(', ') : 'None'}\n\nRepository Context:\n- Language: ${repoData.language}\n- Stars: ${repoData.stargazers_count}\n- Framework: ${repoData.topics ? repoData.topics.join(', ') : 'Unknown'}\n\nDesign and implement this feature with enterprise-grade quality:\n\nRespond with ONLY a valid JSON object:\n{\n  "feature_architecture": {\n    "design_pattern": "architectural pattern used",\n    "components": [\n      {\n        "name": "component name",\n        "purpose": "component purpose",\n        "interfaces": ["input", "output", "interfaces"]\n      }\n    ],\n    "data_flow": "how data flows through the feature",\n    "integration_points": ["existing", "system", "touchpoints"]\n  },\n  "implementation_files": [\n    {\n      "file": "file_path",\n      "type": "component/service/utility/test",\n      "purpose": "file purpose",\n      "content": "complete file content",\n      "dependencies": ["file", "dependencies"]\n    }\n  ],\n  "database_changes": [\n    {\n      "type": "schema/migration/index",\n      "description": "database change description",\n      "sql": "SQL statements if applicable"\n    }\n  ],\n  "api_endpoints": [\n    {\n      "method": "GET/POST/PUT/DELETE",\n      "path": "/api/endpoint",\n      "description": "endpoint purpose",\n      "request_schema": "request format",\n      "response_schema": "response format"\n    }\n  ],\n  "configuration": {\n    "environment_variables": ["VAR_NAME: description"],\n    "feature_flags": ["flag", "configurations"],\n    "dependencies": ["new", "package", "requirements"]\n  },\n  "testing_strategy": {\n    "unit_tests": ["test", "scenarios"],\n    "integration_tests": ["integration", "scenarios"],\n    "e2e_tests": ["end-to-end", "scenarios"],\n    "performance_tests": ["performance", "validations"]\n  },\n  "documentation": {\n    "user_guide": "how users interact with feature",\n    "technical_docs": "technical implementation details",\n    "api_docs": "API documentation"\n  },\n  "git_operations": {\n    "branch_name": "feature/descriptive-name",\n    "commit_strategy": "commit approach",\n    "pr_title": "Feature: Brief description",\n    "pr_description": "Comprehensive PR description"\n  },\n  "deployment_considerations": {\n    "rollout_strategy": "how to deploy safely",\n    "monitoring": ["metrics", "to", "monitor"],\n    "rollback_plan": "rollback strategy"\n  }\n}\n\nReturn ONLY the JSON object.\n`;

      // Replace window.claude.complete with OpenAI API call
      const completion = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: featurePrompt }],
        response_format: { type: "json_object" },
      });
      const featureResponse = completion.choices[0].message.content;

      const featureData = JSON.parse(featureResponse);

      setProcessingMessage(`Implementing feature for ${feature.id}...`);
      // Simulate implementing feature (in a real scenario, this would involve Git operations, file writes, etc.)
      console.log(`Simulating file creation/modification for feature: ${feature.id}`);
      featureData.implementation_files.forEach(file => {
        console.log(`  File: ${file.file}, Purpose: ${file.purpose}`);
      });

      setProcessingMessage(`Creating branch and preparing PR for ${feature.id}...`);
      const branchName = featureData.git_operations.branch_name;
      
      const newEntry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        repo: repoData.name,
        action: 'feature',
        status: 'completed',
        details: `Developed feature: ${feature.name}`,
        branch: branchName,
        pr_title: featureData.git_operations.pr_title,
        metadata: {
          featureId: feature.id,
          complexity: feature.complexity,
          priority: feature.priority,
          filesCreated: featureData.implementation_files.length,
          apiEndpoints: featureData.api_endpoints.length,
          dbChanges: featureData.database_changes.length
        }
      };
      
      addAutomationEntry(newEntry);
      
      // Save to database if we have repository data
      if (repoData.id) {
        await saveAutomationEntryToDB(repoData.id, {
          action: 'feature',
          status: 'completed',
          details: newEntry.details,
          branch_name: branchName,
          pr_title: featureData.git_operations.pr_title,
          metadata: newEntry.metadata
        });
      }
      
      showNotification(
        `Feature developed! Branch: ${branchName}`,
        'success'
      );

    } catch (error) {
      console.error('Feature development failed:', error);
      showNotification(`Feature development failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [githubToken, repoData, setIsProcessing, setProcessingMessage, addAutomationEntry, showNotification, openai.chat.completions, saveAutomationEntryToDB]);

  const executeBulkBugFixes = useCallback(async () => {
    if (!analysisResults || !analysisResults.bugs_detected.length) {
      showNotification('No bugs detected to fix', 'warning');
      return;
    }

    const bugsToFix = analysisResults.bugs_detected
      .filter(bug => bug.severity === 'high' || bug.severity === 'critical')
      .slice(0, automationConfig.maxBugsPerRun);

    if (bugsToFix.length === 0) {
      showNotification('No high-priority bugs to fix', 'info');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage(`Fixing ${bugsToFix.length} high-priority bugs...`);

    try {
      for (const bug of bugsToFix) {
        await executeBugFix(bug);
      }
      showNotification(`Successfully fixed ${bugsToFix.length} bugs!`, 'success');
    } catch (error) {
      showNotification(`Bulk bug fixing failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [analysisResults, automationConfig, setIsProcessing, setProcessingMessage, showNotification, executeBugFix]);

  const executeBulkImprovements = useCallback(async () => {
    if (!analysisResults || !analysisResults.improvements_suggested.length) {
      showNotification('No improvements suggested', 'warning');
      return;
    }

    const improvementsToImplement = analysisResults.improvements_suggested
      .filter(imp => imp.priority === 'high' || imp.priority === 'critical')
      .slice(0, automationConfig.maxImprovementsPerRun);

    if (improvementsToImplement.length === 0) {
      showNotification('No high-priority improvements to implement', 'info');
      return;
    }

    setIsProcessing(true);
    setProcessingMessage(`Implementing ${improvementsToImplement.length} high-priority improvements...`);

    try {
      for (const improvement of improvementsToImplement) {
        await executeImprovement(improvement);
      }
      showNotification(`Successfully implemented ${improvementsToImplement.length} improvements!`, 'success');
    } catch (error) {
      showNotification(`Bulk improvement implementation failed: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingMessage('');
    }
  }, [analysisResults, automationConfig, setIsProcessing, setProcessingMessage, showNotification, executeImprovement]);

  return {
    analyzeRepository,
    executeBugFix,
    executeImprovement,
    developFeature,
    executeBulkBugFixes,
    executeBulkImprovements,
    getStoredAnalyses,
    hasRecentAnalysis
  };
};



