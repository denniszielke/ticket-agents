"""
GitHub issue fetcher module.
Fetches issues from a GitHub repository for indexing.
"""
from typing import List, Dict, Optional
from github import Github
from github.Issue import Issue
import config


class GitHubIssueFetcher:
    """Fetches issues from GitHub repository."""
    
    def __init__(self, token: Optional[str] = None, repo_name: Optional[str] = None):
        """
        Initialize GitHub issue fetcher.
        
        Args:
            token: GitHub access token (defaults to config.GITHUB_TOKEN)
            repo_name: Repository name in format 'owner/repo' (defaults to config.GITHUB_REPO)
        """
        self.token = token or config.GITHUB_TOKEN
        self.repo_name = repo_name or config.GITHUB_REPO
        
        if not self.token:
            raise ValueError("GitHub token not provided")
        if not self.repo_name:
            raise ValueError("GitHub repository not provided")
            
        self.github = Github(self.token)
        self.repo = self.github.get_repo(self.repo_name)
    
    def fetch_issues(self, state: str = 'all', labels: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch issues from the repository.
        
        Args:
            state: Issue state ('open', 'closed', or 'all')
            labels: Optional list of label names to filter by
            
        Returns:
            List of issue dictionaries with relevant information
        """
        issues = []
        
        # Get issues from repository
        github_issues = self.repo.get_issues(state=state, labels=labels or [])
        
        for issue in github_issues:
            # Skip pull requests (they also appear as issues in GitHub API)
            if issue.pull_request:
                continue
                
            issue_data = self._extract_issue_data(issue)
            issues.append(issue_data)
        
        return issues
    
    def _extract_issue_data(self, issue: Issue) -> Dict:
        """
        Extract relevant data from a GitHub issue.
        
        Args:
            issue: GitHub Issue object
            
        Returns:
            Dictionary containing issue data
        """
        # Extract labels
        labels = [label.name for label in issue.labels]
        
        # Extract comments
        comments = []
        for comment in issue.get_comments():
            comments.append({
                'author': comment.user.login if comment.user else 'unknown',
                'body': comment.body,
                'created_at': comment.created_at.isoformat()
            })
        
        # Determine support level from labels
        support_level = self._determine_support_level(labels)
        
        # Determine ticket category
        category = self._determine_category(issue.title, issue.body, labels)
        
        return {
            'number': issue.number,
            'title': issue.title,
            'body': issue.body or '',
            'state': issue.state,
            'labels': labels,
            'support_level': support_level,
            'category': category,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat(),
            'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
            'comments': comments,
            'url': issue.html_url
        }
    
    def _determine_support_level(self, labels: List[str]) -> Optional[str]:
        """
        Determine support level from issue labels.
        
        Args:
            labels: List of label names
            
        Returns:
            Support level (L1, L2, L3) or None
        """
        for label in labels:
            label_lower = label.lower()
            if 'l1' in label_lower or 'level-1' in label_lower or 'first-level' in label_lower:
                return 'L1'
            elif 'l2' in label_lower or 'level-2' in label_lower or 'second-level' in label_lower:
                return 'L2'
            elif 'l3' in label_lower or 'level-3' in label_lower or 'third-level' in label_lower:
                return 'L3'
        return None
    
    def _determine_category(self, title: str, body: str, labels: List[str]) -> str:
        """
        Determine ticket category based on title, body, and labels.
        
        Args:
            title: Issue title
            body: Issue body
            labels: List of label names
            
        Returns:
            Category string
        """
        text = f"{title} {body}".lower()
        
        # Check labels first
        for label in labels:
            label_lower = label.lower()
            if 'documentation' in label_lower:
                return 'documentation'
            elif 'config' in label_lower or 'configuration' in label_lower:
                return 'configuration'
            elif 'operational' in label_lower or 'ops' in label_lower:
                return 'operational'
        
        # Check content
        if any(keyword in text for keyword in ['documentation', 'docs', 'guide', 'how to', 'tutorial']):
            return 'documentation'
        elif any(keyword in text for keyword in ['configuration', 'config', 'setting', 'parameter']):
            return 'configuration'
        elif any(keyword in text for keyword in ['operational', 'operation', 'incident', 'outage', 'down']):
            return 'operational'
        elif any(keyword in text for keyword in ['provision', 'create', 'setup', 'deploy']):
            return 'provisioning'
        
        return 'general'
