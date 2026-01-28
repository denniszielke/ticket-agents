"""
Simple tests for the ticket agents system.
"""
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest


def test_github_fetcher_initialization():
    """Test GitHubIssueFetcher initialization."""
    from github_fetcher import GitHubIssueFetcher
    
    # Test with no credentials
    with pytest.raises(ValueError, match="GitHub token not provided"):
        GitHubIssueFetcher(token=None, repo_name=None)
    
    # Test with token but no repo
    with pytest.raises(ValueError, match="GitHub repository not provided"):
        GitHubIssueFetcher(token="test_token", repo_name=None)


def test_fetch_issues_with_ids():
    """Test fetching specific issues by ID."""
    from github_fetcher import GitHubIssueFetcher
    
    with patch('github_fetcher.Github') as mock_github, patch('github_fetcher.config'):
        # Mock the GitHub client
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo
        
        # Mock a single issue
        mock_issue = MagicMock()
        mock_issue.number = 123
        mock_issue.title = "Test Issue"
        mock_issue.body = "Test body"
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.created_at = MagicMock()
        mock_issue.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_issue.updated_at = MagicMock()
        mock_issue.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_issue.closed_at = None
        mock_issue.html_url = "https://github.com/test/repo/issues/123"
        mock_issue.pull_request = None
        mock_issue.get_comments.return_value = []
        
        mock_repo.get_issue.return_value = mock_issue
        
        # Create fetcher and fetch specific issue
        fetcher = GitHubIssueFetcher(token="test_token", repo_name="test/repo")
        tickets = fetcher.fetch_issues(issue_ids=[123])
        
        assert len(tickets) == 1
        assert tickets[0]['number'] == 123
        assert tickets[0]['title'] == "Test Issue"


def test_fetch_issues_with_types():
    """Test fetching issues filtered by type."""
    from github_fetcher import GitHubIssueFetcher
    
    with patch('github_fetcher.Github') as mock_github, patch('github_fetcher.config'):
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo
        
        # Mock multiple issues with different categories
        mock_issues = []
        for i, category in enumerate(['documentation', 'configuration', 'operational']):
            mock_issue = MagicMock()
            mock_issue.number = i + 1
            mock_issue.title = f"Test {category}"
            mock_issue.body = f"This is a {category} issue"
            mock_issue.state = "open"
            mock_issue.labels = []
            mock_issue.created_at = MagicMock()
            mock_issue.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_issue.updated_at = MagicMock()
            mock_issue.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_issue.closed_at = None
            mock_issue.html_url = f"https://github.com/test/repo/issues/{i+1}"
            mock_issue.pull_request = None
            mock_issue.get_comments.return_value = []
            mock_issues.append(mock_issue)
        
        mock_repo.get_issues.return_value = mock_issues
        
        # Fetch with type filter
        fetcher = GitHubIssueFetcher(token="test_token", repo_name="test/repo")
        tickets = fetcher.fetch_issues(issue_types=['documentation'])
        
        # Should only get documentation issues
        assert len(tickets) == 1
        assert tickets[0]['category'] == 'documentation'


def test_determine_support_level():
    """Test support level determination."""
    from github_fetcher import GitHubIssueFetcher
    
    # Mock the initialization to avoid GitHub API calls
    with patch('github_fetcher.Github'), patch('github_fetcher.config'):
        fetcher = GitHubIssueFetcher.__new__(GitHubIssueFetcher)
        
        # Test L1
        assert fetcher._determine_support_level(['bug', 'L1']) == 'L1'
        assert fetcher._determine_support_level(['level-1']) == 'L1'
        
        # Test L2
        assert fetcher._determine_support_level(['L2', 'urgent']) == 'L2'
        assert fetcher._determine_support_level(['level-2']) == 'L2'
        
        # Test L3
        assert fetcher._determine_support_level(['L3']) == 'L3'
        assert fetcher._determine_support_level(['level-3']) == 'L3'
        
        # Test no support level
        assert fetcher._determine_support_level(['bug', 'enhancement']) is None


def test_determine_category():
    """Test category determination."""
    from github_fetcher import GitHubIssueFetcher
    
    with patch('github_fetcher.Github'), patch('github_fetcher.config'):
        fetcher = GitHubIssueFetcher.__new__(GitHubIssueFetcher)
        
        # Test documentation
        assert fetcher._determine_category(
            "How to provision cluster",
            "I need documentation on cluster setup",
            []
        ) == 'documentation'
        
        # Test configuration
        assert fetcher._determine_category(
            "Configuration issue",
            "The cluster configuration is wrong",
            []
        ) == 'configuration'
        
        # Test operational
        assert fetcher._determine_category(
            "Cluster is down",
            "We have an operational incident",
            []
        ) == 'operational'
        
        # Test provisioning
        assert fetcher._determine_category(
            "Create new cluster",
            "Need to provision a cluster in Azure",
            []
        ) == 'provisioning'


def test_ticket_indexer_initialization():
    """Test TicketIndexer initialization."""
    from ticket_indexer import TicketIndexer
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        index_file = f.name
    
    try:
        indexer = TicketIndexer(index_file=index_file)
        
        assert indexer.index_file == index_file
        assert indexer.tickets == []
        assert indexer.embeddings == []
    finally:
        if os.path.exists(index_file):
            os.unlink(index_file)


def test_ticket_indexer_stats():
    """Test ticket statistics."""
    from ticket_indexer import TicketIndexer
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        index_file = f.name
    
    try:
        indexer = TicketIndexer(index_file=index_file)
        
        # Test empty stats
        stats = indexer.get_stats()
        assert stats['total_tickets'] == 0
        
        # Add some test tickets
        indexer.tickets = [
            {'state': 'open', 'category': 'documentation', 'support_level': 'L1'},
            {'state': 'closed', 'category': 'configuration', 'support_level': 'L2'},
            {'state': 'closed', 'category': 'documentation', 'support_level': 'L1'},
        ]
        
        stats = indexer.get_stats()
        assert stats['total_tickets'] == 3
        assert stats['by_state']['open'] == 1
        assert stats['by_state']['closed'] == 2
        assert stats['by_category']['documentation'] == 2
        assert stats['by_category']['configuration'] == 1
        assert stats['by_support_level']['L1'] == 2
        assert stats['by_support_level']['L2'] == 1
    finally:
        if os.path.exists(index_file):
            os.unlink(index_file)


@pytest.mark.asyncio
async def test_resolution_agent_confidence():
    """Test confidence calculation in ResolutionAgent."""
    from resolution_agent import ResolutionAgent
    
    agent = ResolutionAgent()
    
    # Test high confidence
    assert agent._calculate_confidence(0.9, 5) == 'high'
    assert agent._calculate_confidence(0.85, 3) == 'high'
    
    # Test medium confidence
    assert agent._calculate_confidence(0.7, 3) == 'medium'
    assert agent._calculate_confidence(0.65, 2) == 'medium'
    
    # Test low confidence
    assert agent._calculate_confidence(0.5, 2) == 'low'
    assert agent._calculate_confidence(0.7, 1) == 'low'


def test_azure_search_indexer_initialization():
    """Test AzureSearchIndexer initialization."""
    import config as test_config
    
    # Test without endpoint configured
    original_endpoint = test_config.AZURE_AI_SEARCH_ENDPOINT
    test_config.AZURE_AI_SEARCH_ENDPOINT = None
    
    try:
        from azure_search_indexer import AzureSearchIndexer
        with pytest.raises(ValueError, match="Azure AI Search endpoint not provided"):
            AzureSearchIndexer()
    finally:
        test_config.AZURE_AI_SEARCH_ENDPOINT = original_endpoint


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
