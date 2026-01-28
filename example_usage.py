#!/usr/bin/env python3
"""
Example usage of the ticket agents system.
This script demonstrates how to use the ticket-agents programmatically.
"""
import os
from github_fetcher import GitHubIssueFetcher
from ticket_indexer import TicketIndexer
from resolution_recommender import ResolutionRecommender


def main():
    """Example workflow for ticket-agents."""
    
    print("=" * 80)
    print("Ticket Agents - Example Usage")
    print("=" * 80)
    
    # Example 1: Fetch and index issues
    print("\n1. Fetching GitHub issues...")
    print("-" * 80)
    
    # Initialize fetcher (uses environment variables from .env)
    try:
        fetcher = GitHubIssueFetcher()
        
        # Fetch all issues
        tickets = fetcher.fetch_issues(state='all')
        
        print(f"✓ Fetched {len(tickets)} issues")
        
        # Show sample ticket
        if tickets:
            sample = tickets[0]
            print(f"\nSample ticket:")
            print(f"  Number: #{sample['number']}")
            print(f"  Title: {sample['title']}")
            print(f"  Category: {sample['category']}")
            print(f"  Support Level: {sample.get('support_level', 'unspecified')}")
    
    except Exception as e:
        print(f"✗ Error fetching issues: {e}")
        print("Make sure GITHUB_TOKEN and GITHUB_REPO are set in .env")
        tickets = []
    
    # Example 2: Index tickets
    if tickets:
        print("\n2. Indexing tickets...")
        print("-" * 80)
        
        try:
            indexer = TicketIndexer()
            indexer.index_tickets(tickets)
            
            # Show statistics
            stats = indexer.get_stats()
            print(f"\n✓ Indexed {stats['total_tickets']} tickets")
            print(f"  - Open: {stats['by_state'].get('open', 0)}")
            print(f"  - Closed: {stats['by_state'].get('closed', 0)}")
            
        except Exception as e:
            print(f"✗ Error indexing: {e}")
            print("Make sure OPENAI_API_KEY is set in .env")
            indexer = None
    else:
        indexer = None
    
    # Example 3: Search for similar tickets
    if indexer and indexer.tickets:
        print("\n3. Searching for similar tickets...")
        print("-" * 80)
        
        query = "How to provision a Kubernetes cluster in Azure?"
        print(f"Query: {query}\n")
        
        try:
            similar = indexer.find_similar_tickets(query, top_k=3)
            
            print(f"✓ Found {len(similar)} similar tickets:\n")
            for i, ticket in enumerate(similar, 1):
                print(f"{i}. #{ticket['number']}: {ticket['title']}")
                print(f"   Similarity: {ticket['similarity_score']:.3f}")
                print(f"   Category: {ticket['category']}\n")
                
        except Exception as e:
            print(f"✗ Error searching: {e}")
    
    # Example 4: Get resolution recommendation
    if indexer and indexer.tickets:
        print("\n4. Getting resolution recommendation...")
        print("-" * 80)
        
        new_ticket = """
        Title: AKS cluster nodes not starting after upgrade
        
        Description: After upgrading our AKS cluster to version 1.28, 
        the nodes are stuck in 'NotReady' state. The pods cannot be scheduled 
        and we're seeing errors in the node logs about network plugin issues.
        """
        
        print(f"New ticket:\n{new_ticket}\n")
        
        try:
            similar = indexer.find_similar_tickets(new_ticket, top_k=3)
            
            recommender = ResolutionRecommender()
            result = recommender.recommend_resolution(new_ticket, similar)
            
            print(f"✓ Recommendation (Confidence: {result['confidence']})\n")
            print("-" * 80)
            print(result['recommendation'])
            print("-" * 80)
            
            print(f"\nBased on {len(result['similar_tickets'])} similar ticket(s)")
            
        except Exception as e:
            print(f"✗ Error generating recommendation: {e}")
    
    print("\n" + "=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
