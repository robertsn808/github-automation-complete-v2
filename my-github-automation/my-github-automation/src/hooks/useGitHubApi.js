import { useCallback } from 'react';

export const useGitHubApi = (githubToken, showNotification) => {
  const cleanClaudeResponse = (response) => {
    let clean = response.trim();
    if (clean.includes('```json')) {
      clean = clean.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    }
    if (clean.includes('```')) {
      clean = clean.replace(/```\n?/g, '').trim();
    }
    return clean;
  };

  const fetchRepoData = useCallback(async (url, token) => {
    try {
      const repoPath = url.replace('https://github.com/', '');
      const [owner, repo] = repoPath.split('/');
      
      if (!owner || !repo) {
        throw new Error('Invalid GitHub URL format');
      }

      const headers = {
        'Authorization': `token ${token}`,
        'Accept': 'application/vnd.github.v3+json'
      };

      const [repoResponse, issuesResponse, prsResponse, contributorsResponse] = await Promise.all([
        fetch(`https://api.github.com/repos/${repoPath}`, { headers }),
        fetch(`https://api.github.com/repos/${repoPath}/issues?state=open&per_page=100`, { headers }),
        fetch(`https://api.github.com/repos/${repoPath}/pulls?state=open&per_page=100`, { headers }),
        fetch(`https://api.github.com/repos/${repoPath}/contributors?per_page=100`, { headers })
      ]);

      if (!repoResponse.ok) {
        throw new Error(`GitHub API error: ${repoResponse.status} - ${repoResponse.statusText}`);
      }

      const repoData = await repoResponse.json();
      const issues = issuesResponse.ok ? await issuesResponse.json() : [];
      const prs = prsResponse.ok ? await prsResponse.json() : [];
      const contributors = contributorsResponse.ok ? await contributorsResponse.json() : [];

      return {
        ...repoData,
        issues,
        pullRequests: prs,
        contributors,
        health: {
          issueCount: issues.length,
          prCount: prs.length,
          contributorCount: contributors.length,
          hasReadme: repoData.has_readme || false,
          hasLicense: repoData.license !== null,
          hasIssues: repoData.has_issues,
          hasWiki: repoData.has_wiki
        }
      };
    } catch (error) {
      console.error('Error fetching repo data:', error);
      showNotification(`Error fetching repo data: ${error.message}`, 'error');
      throw error;
    }
  }, [showNotification]);

  const getRepositoryStructure = useCallback(async (repo, token) => {
    try {
      const headers = {
        'Authorization': `token ${token}`,
        'Accept': 'application/vnd.github.v3+json'
      };

      const treeResponse = await fetch(`https://api.github.com/repos/${repo.full_name}/git/trees/${repo.default_branch}?recursive=1`, { headers });
      
      if (!treeResponse.ok) {
        throw new Error(`Failed to fetch repository tree: ${treeResponse.status}`);
      }

      const treeData = await treeResponse.json();
      const files = treeData.tree.filter(item => item.type === 'blob');
      
      const fileTypes = {};
      const directories = new Set();
      
      files.forEach(file => {
        const extension = file.path.split('.').pop();
        fileTypes[extension] = (fileTypes[extension] || 0) + 1;
        
        const dir = file.path.includes('/') ? file.path.split('/')[0] : 'root';
        directories.add(dir);
      });

      const structure = {
        totalFiles: files.length,
        fileTypes,
        directories: Array.from(directories),
        hasTests: files.some(f => f.path.includes('test') || f.path.includes('spec')),
        hasDocumentation: files.some(f => f.path.toLowerCase().includes('readme') || f.path.toLowerCase().includes('doc')),
        hasCI: files.some(f => f.path.includes('.github/workflows') || f.path.includes('.ci')),
        configFiles: files.filter(f => f.path.includes('config') || f.path.includes('.json') || f.path.includes('.yml')),
        mainLanguage: repo.language
      };

      return structure;
    } catch (error) {
      console.error('Error fetching repository structure:', error);
      showNotification(`Error fetching repository structure: ${error.message}`, 'error');
      return {
        totalFiles: 0,
        fileTypes: {},
        directories: [],
        hasTests: false,
        hasDocumentation: false,
        hasCI: false,
        configFiles: [],
        mainLanguage: repo.language || 'Unknown'
      };
    }
  }, [showNotification]);

  return { cleanClaudeResponse, fetchRepoData, getRepositoryStructure };
};

