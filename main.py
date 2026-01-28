"""
Main CLI application for the ticket agents system.
"""
import click
import json
from github_fetcher import GitHubIssueFetcher
from ticket_indexer import TicketIndexer
from resolution_agent import ResolutionRecommender
import config


@click.group()
def cli():
    """Ticket Agents - GitHub Issue Resolution Recommendation System"""
    pass


@cli.command()
@click.option('--repo', help='GitHub repository (owner/repo)')
@click.option('--token', help='GitHub access token')
@click.option('--state', default='all', help='Issue state (open, closed, all)')
@click.option('--labels', help='Comma-separated list of labels to filter by')
@click.option('--issue-ids', help='Comma-separated list of specific issue numbers to index')
@click.option('--issue-types', help='Comma-separated list of issue types/categories to filter by (documentation, configuration, operational, provisioning, general)')
@click.option('--use-azure-search', is_flag=True, help='Use Azure AI Search instead of local JSON file')
def index(repo, token, state, labels, issue_ids, issue_types, use_azure_search):
    """Index GitHub issues from a repository."""
    try:
        click.echo("Fetching issues from GitHub...")
        
        # Parse labels
        label_list = [l.strip() for l in labels.split(',') if l.strip()] if labels else None
        
        # Parse issue IDs
        issue_id_list = [int(i.strip()) for i in issue_ids.split(',') if i.strip()] if issue_ids else None
        
        # Parse issue types
        issue_type_list = [t.strip() for t in issue_types.split(',') if t.strip()] if issue_types else None
        
        # Fetch issues
        fetcher = GitHubIssueFetcher(token=token, repo_name=repo)
        tickets = fetcher.fetch_issues(state=state, labels=label_list, issue_ids=issue_id_list, issue_types=issue_type_list)
        
        click.echo(f"Fetched {len(tickets)} issues")
        
        # Determine which indexer to use
        use_search = use_azure_search or config.USE_AZURE_SEARCH
        
        if use_search:
            # Use Azure AI Search
            click.echo("Using Azure AI Search for indexing...")
            from azure_search_indexer import AzureSearchIndexer
            
            indexer = AzureSearchIndexer()
            
            # Check if index exists, create if not
            if not indexer.index_exists():
                click.echo(f"Creating Azure AI Search index: {indexer.index_name}")
                indexer.create_index()
                click.echo("✓ Index created successfully!")
            else:
                click.echo(f"Using existing Azure AI Search index: {indexer.index_name}")
            
            # Index tickets
            click.echo("Indexing tickets in Azure AI Search...")
            indexer.index_tickets(tickets)
        else:
            # Use local JSON file
            click.echo("Using local JSON file for indexing...")
            indexer = TicketIndexer()
            indexer.index_tickets(tickets)
        
        click.echo("✓ Indexing complete!")
        
        # Show statistics
        stats = indexer.get_stats()
        click.echo("\nIndex Statistics:")
        click.echo(f"  Total tickets: {stats['total_tickets']}")
        click.echo(f"  By state: {json.dumps(stats['by_state'], indent=4)}")
        click.echo(f"  By category: {json.dumps(stats['by_category'], indent=4)}")
        click.echo(f"  By support level: {json.dumps(stats['by_support_level'], indent=4)}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


@cli.command()
@click.argument('query')
@click.option('--top-k', default=5, help='Number of similar tickets to find')
@click.option('--use-azure-search', is_flag=True, help='Use Azure AI Search instead of local JSON file')
def search(query, top_k, use_azure_search):
    """Search for similar tickets."""
    try:
        use_search = use_azure_search or config.USE_AZURE_SEARCH
        
        if use_search:
            from azure_search_indexer import AzureSearchIndexer
            indexer = AzureSearchIndexer()
        else:
            indexer = TicketIndexer()
        
        if not use_search and not indexer.tickets:
            click.echo("No tickets indexed. Run 'index' command first.", err=True)
            return
        
        click.echo(f"Searching for similar tickets...")
        similar = indexer.find_similar_tickets(query, top_k=top_k)
        
        if not similar:
            click.echo("No similar tickets found.")
            return
        
        click.echo(f"\nFound {len(similar)} similar tickets:\n")
        
        for i, ticket in enumerate(similar, 1):
            click.echo(f"{i}. #{ticket['number']} - {ticket['title']}")
            click.echo(f"   Similarity: {ticket['similarity_score']:.2f}")
            click.echo(f"   State: {ticket['state']}")
            click.echo(f"   Category: {ticket.get('category', 'general')}")
            click.echo(f"   URL: {ticket['url']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


@cli.command()
@click.argument('query')
@click.option('--top-k', default=5, help='Number of similar tickets to consider')
@click.option('--output', help='Output file for the recommendation (JSON)')
@click.option('--use-azure-search', is_flag=True, help='Use Azure AI Search instead of local JSON file')
def recommend(query, top_k, output, use_azure_search):
    """Get resolution recommendation for a new ticket."""
    try:
        # Find similar tickets
        use_search = use_azure_search or config.USE_AZURE_SEARCH
        
        if use_search:
            from azure_search_indexer import AzureSearchIndexer
            indexer = AzureSearchIndexer()
        else:
            indexer = TicketIndexer()
        
        if not use_search and not indexer.tickets:
            click.echo("No tickets indexed. Run 'index' command first.", err=True)
            return
        
        click.echo(f"Analyzing ticket and finding similar issues...")
        similar = indexer.find_similar_tickets(query, top_k=top_k)
        
        # Generate recommendation
        click.echo("Generating resolution recommendation...")
        recommender = ResolutionRecommender()
        result = recommender.recommend_resolution(query, similar)
        
        # Display results
        click.echo("\n" + "=" * 80)
        click.echo("RESOLUTION RECOMMENDATION")
        click.echo("=" * 80)
        click.echo(f"\nConfidence: {result['confidence'].upper()}")
        click.echo(f"Based on {result['similar_tickets_count']} similar ticket(s)")
        click.echo(f"Average similarity: {result.get('average_similarity', 0):.2f}\n")
        click.echo("-" * 80)
        click.echo(result['recommendation'])
        click.echo("-" * 80)
        
        # Show similar tickets
        click.echo("\nSimilar Tickets Referenced:")
        for ticket in result['similar_tickets']:
            click.echo(f"  - #{ticket['number']}: {ticket['title']}")
            click.echo(f"    Similarity: {ticket['similarity_score']:.2f}, State: {ticket['state']}")
            click.echo(f"    URL: {ticket['url']}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            click.echo(f"\n✓ Recommendation saved to {output}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


@cli.command()
@click.option('--use-azure-search', is_flag=True, help='Use Azure AI Search instead of local JSON file')
def stats(use_azure_search):
    """Show statistics about indexed tickets."""
    try:
        use_search = use_azure_search or config.USE_AZURE_SEARCH
        
        if use_search:
            from azure_search_indexer import AzureSearchIndexer
            indexer = AzureSearchIndexer()
        else:
            indexer = TicketIndexer()
        
        if not use_search and not indexer.tickets:
            click.echo("No tickets indexed. Run 'index' command first.", err=True)
            return
        
        stats = indexer.get_stats()
        
        click.echo("\n" + "=" * 80)
        click.echo("TICKET INDEX STATISTICS")
        click.echo("=" * 80)
        click.echo(f"\nTotal tickets indexed: {stats['total_tickets']}\n")
        
        click.echo("By State:")
        for state, count in stats['by_state'].items():
            click.echo(f"  {state}: {count}")
        
        click.echo("\nBy Category:")
        for category, count in stats['by_category'].items():
            click.echo(f"  {category}: {count}")
        
        click.echo("\nBy Support Level:")
        for level, count in stats['by_support_level'].items():
            click.echo(f"  {level}: {count}")
        
        click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


if __name__ == '__main__':
    cli()
