"""
Ticket indexer module.
Indexes tickets with embeddings for similarity search and resolution recommendations.
"""
import json
import os
from typing import List, Dict, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import config


class TicketIndexer:
    """Indexes tickets and provides similarity search capabilities."""
    
    def __init__(self, index_file: Optional[str] = None):
        """
        Initialize ticket indexer.
        
        Args:
            index_file: Path to the index file (defaults to config.INDEX_FILE)
        """
        self.index_file = index_file or config.INDEX_FILE
        self.tickets = []
        self.embeddings = []
        
        # Initialize OpenAI client
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not provided")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Load existing index if available
        self.load_index()
    
    def index_tickets(self, tickets: List[Dict]) -> None:
        """
        Index a list of tickets with embeddings.
        
        Args:
            tickets: List of ticket dictionaries
        """
        print(f"Indexing {len(tickets)} tickets...")
        
        for i, ticket in enumerate(tickets):
            # Create text representation for embedding
            text = self._create_ticket_text(ticket)
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Store ticket and embedding
            self.tickets.append(ticket)
            self.embeddings.append(embedding)
            
            if (i + 1) % 10 == 0:
                print(f"Indexed {i + 1}/{len(tickets)} tickets")
        
        # Save index
        self.save_index()
        print(f"Successfully indexed {len(tickets)} tickets")
    
    def find_similar_tickets(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Find similar tickets to a query.
        
        Args:
            query: Query text (new ticket description)
            top_k: Number of similar tickets to return
            
        Returns:
            List of similar tickets with similarity scores
        """
        if not self.tickets:
            return []
        
        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        
        # Calculate similarities
        similarities = cosine_similarity(
            [query_embedding],
            self.embeddings
        )[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Prepare results
        results = []
        for idx in top_indices:
            ticket = self.tickets[idx].copy()
            ticket['similarity_score'] = float(similarities[idx])
            results.append(ticket)
        
        return results
    
    def _create_ticket_text(self, ticket: Dict) -> str:
        """
        Create a text representation of a ticket for embedding.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Text representation
        """
        parts = [
            f"Title: {ticket['title']}",
            f"Body: {ticket['body']}",
            f"Labels: {', '.join(ticket['labels'])}",
            f"Category: {ticket.get('category', 'general')}",
        ]
        
        # Add support level if available
        if ticket.get('support_level'):
            parts.append(f"Support Level: {ticket['support_level']}")
        
        # Add resolution comments if ticket is closed
        if ticket['state'] == 'closed' and ticket['comments']:
            # Add last few comments which might contain resolution
            resolution_comments = ticket['comments'][-3:]
            comments_text = ' '.join([c['body'] for c in resolution_comments])
            parts.append(f"Resolution: {comments_text}")
        
        return '\n'.join(parts)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def save_index(self) -> None:
        """Save the index to disk."""
        data = {
            'tickets': self.tickets,
            'embeddings': [emb for emb in self.embeddings]
        }
        
        with open(self.index_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Index saved to {self.index_file}")
    
    def load_index(self) -> None:
        """Load the index from disk."""
        if not os.path.exists(self.index_file):
            print(f"No existing index found at {self.index_file}")
            return
        
        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
            
            self.tickets = data.get('tickets', [])
            self.embeddings = data.get('embeddings', [])
            
            print(f"Loaded index with {len(self.tickets)} tickets")
        except Exception as e:
            print(f"Error loading index: {e}")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the indexed tickets.
        
        Returns:
            Dictionary with statistics
        """
        if not self.tickets:
            return {
                'total_tickets': 0,
                'by_state': {},
                'by_category': {},
                'by_support_level': {}
            }
        
        stats = {
            'total_tickets': len(self.tickets),
            'by_state': {},
            'by_category': {},
            'by_support_level': {}
        }
        
        for ticket in self.tickets:
            # Count by state
            state = ticket['state']
            stats['by_state'][state] = stats['by_state'].get(state, 0) + 1
            
            # Count by category
            category = ticket.get('category', 'general')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Count by support level
            support_level = ticket.get('support_level', 'unspecified')
            stats['by_support_level'][support_level] = stats['by_support_level'].get(support_level, 0) + 1
        
        return stats
