"""
Azure AI Search indexer module.
Indexes tickets with embeddings in Azure AI Search for similarity search.
"""
import logging
from typing import List, Dict, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
import config
from model_client import create_embedding_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureSearchIndexer:
    """Indexes tickets in Azure AI Search with vector embeddings."""
    
    def __init__(self, index_name: Optional[str] = None):
        """
        Initialize Azure Search indexer.
        
        Args:
            index_name: Name of the search index (defaults to config.AZURE_AI_SEARCH_INDEX_NAME)
        """
        self.index_name = index_name or config.AZURE_AI_SEARCH_INDEX_NAME
        self.endpoint = config.AZURE_AI_SEARCH_ENDPOINT
        
        if not self.endpoint:
            raise ValueError("Azure AI Search endpoint not provided. Set AZURE_AI_SEARCH_ENDPOINT.")
        
        # Setup credentials - support both key and managed identity
        if config.AZURE_AI_SEARCH_KEY:
            logger.info("Using Azure AI Search with API key authentication")
            self.credential = AzureKeyCredential(config.AZURE_AI_SEARCH_KEY)
        else:
            logger.info("Using Azure AI Search with managed identity authentication")
            self.credential = DefaultAzureCredential()
        
        # Initialize clients
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        self.embedding_client = None
        self.embedding_dimensions = config.EMBEDDING_DIMENSIONS
    
    def _ensure_embedding_client(self):
        """Ensure embedding client is initialized."""
        if self.embedding_client is None:
            self.embedding_client = create_embedding_client()
    
    def create_index(self) -> None:
        """Create the search index with vector search configuration."""
        logger.info(f"Creating Azure AI Search index: {self.index_name}")
        
        # Define the fields for the index
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="body", type=SearchFieldDataType.String),
            SimpleField(name="state", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="labels", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
            SimpleField(name="support_level", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.String),
            SimpleField(name="updated_at", type=SearchFieldDataType.String),
            SimpleField(name="closed_at", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="url", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.embedding_dimensions,
                vector_search_profile_name="ticket-vector-profile"
            ),
        ]
        
        # Configure vector search
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="ticket-vector-profile",
                    algorithm_configuration_name="ticket-hnsw-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="ticket-hnsw-config")
            ]
        )
        
        # Create the search index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        try:
            result = self.index_client.create_or_update_index(index)
            logger.info(f"Index '{result.name}' created or updated successfully")
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise
    
    def index_exists(self) -> bool:
        """Check if the index exists."""
        try:
            self.index_client.get_index(self.index_name)
            return True
        except Exception:
            return False
    
    def index_tickets(self, tickets: List[Dict]) -> None:
        """
        Index a list of tickets with embeddings.
        
        Args:
            tickets: List of ticket dictionaries
        """
        if not tickets:
            logger.info("No tickets to index")
            return
        
        # Ensure index exists
        if not self.index_exists():
            logger.info("Index does not exist, creating it...")
            self.create_index()
        
        logger.info(f"Indexing {len(tickets)} tickets in Azure AI Search...")
        
        # Prepare documents for indexing
        documents = []
        
        for i, ticket in enumerate(tickets):
            # Create text representation for embedding
            text = self._create_ticket_text(ticket)
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Prepare document
            doc = {
                'id': str(ticket['number']),
                'number': ticket['number'],
                'title': ticket['title'],
                'body': ticket['body'],
                'state': ticket['state'],
                'labels': ticket['labels'],
                'support_level': ticket.get('support_level', ''),
                'category': ticket.get('category', 'general'),
                'created_at': ticket['created_at'],
                'updated_at': ticket['updated_at'],
                'closed_at': ticket.get('closed_at', ''),
                'url': ticket['url'],
                'content_vector': embedding,
            }
            
            documents.append(doc)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Prepared {i + 1}/{len(tickets)} tickets for indexing")
        
        # Upload documents in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                result = self.search_client.upload_documents(documents=batch)
                logger.info(f"Uploaded batch {i//batch_size + 1}: {len(result)} documents")
            except Exception as e:
                logger.error(f"Error uploading batch: {e}")
                raise
        
        logger.info(f"Successfully indexed {len(tickets)} tickets in Azure AI Search")
    
    def find_similar_tickets(self, query: str, top_k: int = 5, 
                           category: Optional[str] = None) -> List[Dict]:
        """
        Find similar tickets to a query using vector search.
        
        Args:
            query: Query text (new ticket description)
            top_k: Number of similar tickets to return
            category: Optional category filter
            
        Returns:
            List of similar tickets with similarity scores
        """
        logger.info(f"Searching for similar tickets with query: {query}")
        
        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )
        
        # Build search parameters
        search_params = {
            "search_text": None,
            "vector_queries": [vector_query],
            "select": ["number", "title", "body", "state", "labels", "support_level", 
                      "category", "created_at", "updated_at", "closed_at", "url"],
            "top": top_k,
        }
        
        # Add category filter if specified
        if category:
            search_params["filter"] = f"category eq '{category}'"
        
        # Execute search
        try:
            results = self.search_client.search(**search_params)
            
            # Process results
            similar_tickets = []
            for result in results:
                ticket = {
                    'number': result['number'],
                    'title': result['title'],
                    'body': result['body'],
                    'state': result['state'],
                    'labels': result['labels'],
                    'support_level': result.get('support_level', ''),
                    'category': result.get('category', 'general'),
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at'],
                    'closed_at': result.get('closed_at', ''),
                    'url': result['url'],
                    'similarity_score': result.get('@search.score', 0.0),
                    'comments': []  # Comments not stored in search index
                }
                similar_tickets.append(ticket)
            
            logger.info(f"Found {len(similar_tickets)} similar tickets")
            return similar_tickets
            
        except Exception as e:
            logger.error(f"Error searching for similar tickets: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the indexed tickets.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Search for all documents to get stats
            results = self.search_client.search(
                search_text="*",
                select=["state", "category", "support_level"],
                top=1000,  # Limit for performance
                include_total_count=True
            )
            
            stats = {
                'total_tickets': 0,
                'by_state': {},
                'by_category': {},
                'by_support_level': {}
            }
            
            # Count total (this might be limited by top parameter)
            for result in results:
                stats['total_tickets'] += 1
                
                # Count by state
                state = result.get('state', 'unknown')
                stats['by_state'][state] = stats['by_state'].get(state, 0) + 1
                
                # Count by category
                category = result.get('category', 'general')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                
                # Count by support level
                support_level = result.get('support_level', 'unspecified')
                if not support_level:
                    support_level = 'unspecified'
                stats['by_support_level'][support_level] = stats['by_support_level'].get(support_level, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_tickets': 0,
                'by_state': {},
                'by_category': {},
                'by_support_level': {}
            }
    
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
        if ticket['state'] == 'closed' and ticket.get('comments'):
            # Add last few comments which might contain resolution
            resolution_comments = ticket['comments'][-3:]
            comments_text = ' '.join([c['body'] for c in resolution_comments])
            parts.append(f"Resolution: {comments_text}")
        
        return '\n'.join(parts)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using the embedding client.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        self._ensure_embedding_client()
        
        model = config.AZURE_OPENAI_EMBEDDING_MODEL if config.AZURE_OPENAI_ENDPOINT else "text-embedding-3-small"
        
        response = self.embedding_client.embeddings.create(
            model=model,
            input=text,
            dimensions=self.embedding_dimensions
        )
        return response.data[0].embedding
