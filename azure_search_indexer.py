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
    
    def _get_completion_client(self):
        """Get a client for text completions (lazy initialization)."""
        if not hasattr(self, '_completion_client') or self._completion_client is None:
            # Import here to avoid circular dependencies
            from openai import OpenAI, AzureOpenAI
            
            # Try Azure OpenAI first
            if config.AZURE_OPENAI_ENDPOINT:
                if config.AZURE_OPENAI_API_KEY:
                    self._completion_client = AzureOpenAI(
                        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                        api_key=config.AZURE_OPENAI_API_KEY,
                        api_version=config.AZURE_OPENAI_VERSION
                    )
                else:
                    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                    credential = DefaultAzureCredential()
                    token_provider = get_bearer_token_provider(
                        credential, "https://cognitiveservices.azure.com/.default"
                    )
                    self._completion_client = AzureOpenAI(
                        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                        azure_ad_token_provider=token_provider,
                        api_version=config.AZURE_OPENAI_VERSION
                    )
            elif config.OPENAI_API_KEY:
                self._completion_client = OpenAI(api_key=config.OPENAI_API_KEY)
            else:
                raise ValueError("No OpenAI or Azure OpenAI configuration found")
        
        return self._completion_client
    
    def create_index(self) -> None:
        """Create the search index with vector search configuration."""
        logger.info(f"Creating Azure AI Search index: {self.index_name}")
        
        # Define the fields for the index
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="keywords", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
            SimpleField(name="github_item_id", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SearchableField(name="github_item_title", type=SearchFieldDataType.String),
            SearchableField(name="github_item_content", type=SearchFieldDataType.String),
            SearchableField(name="github_item_facts", type=SearchFieldDataType.String),
            SearchableField(name="github_intent_summary", type=SearchFieldDataType.String),
            SearchField(
                name="github_intent_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.embedding_dimensions,
                vector_search_profile_name="ticket-vector-profile"
            ),
            SearchableField(name="github_actions_summary", type=SearchFieldDataType.String),
            SearchableField(name="github_solution_summary", type=SearchFieldDataType.String),
            SimpleField(name="complexity", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            
            # Keep legacy fields for backward compatibility
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
            # Create text representation for embedding (legacy)
            text = self._create_ticket_text(ticket)
            
            # Generate content embedding (legacy)
            content_embedding = self._generate_embedding(text)
            
            # Generate intent text and embedding (new)
            intent_summary = self._generate_intent_summary(ticket)
            intent_embedding = self._generate_embedding(intent_summary)
            
            # Generate actions summary (new)
            actions_summary = self._generate_actions_summary(ticket)
            
            # Generate solution summary (new)
            solution_summary = self._generate_solution_summary(ticket)
            
            # Calculate complexity (new)
            complexity = self._calculate_complexity(ticket)
            
            # Extract keywords (new)
            keywords = self._extract_keywords(ticket)
            
            # Create facts (new)
            facts = self._create_facts(ticket)
            
            # Prepare document with new schema
            doc = {
                'id': str(ticket['number']),
                # New required fields
                'keywords': keywords,
                'github_item_id': ticket['number'],
                'github_item_title': ticket['title'],
                'github_item_content': ticket['body'],
                'github_item_facts': facts,
                'github_intent_summary': intent_summary,
                'github_intent_vector': intent_embedding,
                'github_actions_summary': actions_summary,
                'github_solution_summary': solution_summary,
                'complexity': complexity,
                # Legacy fields for backward compatibility
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
                'content_vector': content_embedding,
            }
            
            documents.append(doc)
            
            if (i + 1) % 5 == 0:
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
                           category: Optional[str] = None, use_intent_vector: bool = True) -> List[Dict]:
        """
        Find similar tickets to a query using vector search.
        
        Args:
            query: Query text (new ticket description)
            top_k: Number of similar tickets to return
            category: Optional category filter
            use_intent_vector: Use github_intent_vector for search (default: True)
            
        Returns:
            List of similar tickets with similarity scores
        """
        logger.info(f"Searching for similar tickets with query: {query}")
        
        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        
        # Choose which vector field to search
        vector_field = "github_intent_vector" if use_intent_vector else "content_vector"
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields=vector_field
        )
        
        # Build search parameters - include new fields
        search_params = {
            "search_text": None,
            "vector_queries": [vector_query],
            "select": ["number", "title", "body", "state", "labels", "support_level", 
                      "category", "created_at", "updated_at", "closed_at", "url",
                      "github_item_id", "github_item_title", "github_intent_summary",
                      "github_actions_summary", "github_solution_summary", "complexity", "keywords"],
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
                    'number': result.get('number', result.get('github_item_id', 0)),
                    'title': result.get('title', result.get('github_item_title', '')),
                    'body': result.get('body', ''),
                    'state': result.get('state', ''),
                    'labels': result.get('labels', []),
                    'support_level': result.get('support_level', ''),
                    'category': result.get('category', 'general'),
                    'created_at': result.get('created_at', ''),
                    'updated_at': result.get('updated_at', ''),
                    'closed_at': result.get('closed_at', ''),
                    'url': result.get('url', ''),
                    'similarity_score': result.get('@search.score', 0.0),
                    'comments': [],  # Comments not stored in search index
                    # Add new fields
                    'intent_summary': result.get('github_intent_summary', ''),
                    'actions_summary': result.get('github_actions_summary', ''),
                    'solution_summary': result.get('github_solution_summary', ''),
                    'complexity': result.get('complexity', 0),
                    'keywords': result.get('keywords', []),
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
    
    def _generate_intent_summary(self, ticket: Dict) -> str:
        """
        Generate an AI summary of what the issue is asking for.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Summary of the intent
        """
        try:
            client = self._get_completion_client()
            model = config.COMPLETION_MODEL_NAME
            
            prompt = f"""Analyze this GitHub issue and provide a concise 2-3 sentence summary of what the user is asking for or requesting.

Title: {ticket['title']}
Body: {ticket['body'][:1000]}  # Limit to first 1000 chars
Labels: {', '.join(ticket['labels'])}

Provide only the summary, no preamble."""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a technical issue analyst. Provide concise summaries of issue intents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate intent summary: {e}")
            return f"Issue about: {ticket['title']}"
    
    def _generate_actions_summary(self, ticket: Dict) -> str:
        """
        Generate an AI summary of the activities and actions taken on the issue.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Summary of actions
        """
        try:
            client = self._get_completion_client()
            model = config.COMPLETION_MODEL_NAME
            
            comments_text = ""
            if ticket.get('comments'):
                # Get first few and last few comments
                comments = ticket['comments']
                sample_comments = comments[:3] + comments[-3:] if len(comments) > 6 else comments
                comments_text = "\n".join([f"- {c['body'][:200]}" for c in sample_comments])
            
            if not comments_text:
                return "No activities recorded yet."
            
            prompt = f"""Analyze the activities on this GitHub issue and provide a 2-3 sentence summary of key actions taken.

Title: {ticket['title']}
Comments:
{comments_text}

Provide only the summary, no preamble."""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a technical issue analyst. Summarize issue activities concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate actions summary: {e}")
            return "Activities not summarized."
    
    def _generate_solution_summary(self, ticket: Dict) -> str:
        """
        Generate an AI summary of how the issue was resolved (for closed issues).
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Summary of the solution
        """
        if ticket['state'] != 'closed':
            return "Issue is still open."
        
        try:
            client = self._get_completion_client()
            model = config.COMPLETION_MODEL_NAME
            
            # Get last few comments which likely contain resolution
            resolution_text = ""
            if ticket.get('comments'):
                resolution_comments = ticket['comments'][-5:]
                resolution_text = "\n".join([f"- {c['body'][:200]}" for c in resolution_comments])
            
            if not resolution_text:
                return "Issue closed without resolution comments."
            
            prompt = f"""Analyze how this GitHub issue was resolved and provide a 2-3 sentence summary of the solution.

Title: {ticket['title']}
Final Comments:
{resolution_text}

Provide only the summary, no preamble."""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a technical issue analyst. Summarize issue resolutions concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate solution summary: {e}")
            return "Resolution not summarized."
    
    def _calculate_complexity(self, ticket: Dict) -> int:
        """
        Calculate a complexity score for the issue (1-10 scale).
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Complexity score (1-10)
        """
        complexity = 1
        
        # Factors that increase complexity:
        # 1. Length of description
        body_length = len(ticket.get('body', ''))
        if body_length > 2000:
            complexity += 3
        elif body_length > 1000:
            complexity += 2
        elif body_length > 500:
            complexity += 1
        
        # 2. Number of comments (indicates discussion/iteration)
        comment_count = len(ticket.get('comments', []))
        if comment_count > 20:
            complexity += 3
        elif comment_count > 10:
            complexity += 2
        elif comment_count > 5:
            complexity += 1
        
        # 3. Support level
        support_level = ticket.get('support_level', '')
        if support_level == 'L3':
            complexity += 2
        elif support_level == 'L2':
            complexity += 1
        
        # 4. Time to resolution (if closed)
        if ticket['state'] == 'closed' and ticket.get('closed_at'):
            from datetime import datetime
            try:
                created = datetime.fromisoformat(ticket['created_at'].replace('Z', '+00:00'))
                closed = datetime.fromisoformat(ticket['closed_at'].replace('Z', '+00:00'))
                days_open = (closed - created).days
                if days_open > 30:
                    complexity += 2
                elif days_open > 14:
                    complexity += 1
            except:
                pass
        
        # Cap at 10
        return min(complexity, 10)
    
    def _extract_keywords(self, ticket: Dict) -> List[str]:
        """
        Extract keywords from the ticket.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Add category
        if ticket.get('category'):
            keywords.append(ticket['category'])
        
        # Add support level
        if ticket.get('support_level'):
            keywords.append(ticket['support_level'])
        
        # Add labels
        keywords.extend(ticket.get('labels', []))
        
        # Add state
        keywords.append(ticket['state'])
        
        # Deduplicate and return
        return list(set(keywords))
    
    def _create_facts(self, ticket: Dict) -> str:
        """
        Create a structured facts summary about the issue.
        
        Args:
            ticket: Ticket dictionary
            
        Returns:
            Formatted facts string
        """
        facts = []
        
        facts.append(f"Issue #{ticket['number']}")
        facts.append(f"State: {ticket['state']}")
        facts.append(f"Category: {ticket.get('category', 'general')}")
        
        if ticket.get('support_level'):
            facts.append(f"Support Level: {ticket['support_level']}")
        
        if ticket.get('labels'):
            facts.append(f"Labels: {', '.join(ticket['labels'])}")
        
        facts.append(f"Created: {ticket['created_at']}")
        
        if ticket.get('closed_at'):
            facts.append(f"Closed: {ticket['closed_at']}")
        
        comment_count = len(ticket.get('comments', []))
        facts.append(f"Comments: {comment_count}")
        
        return " | ".join(facts)
