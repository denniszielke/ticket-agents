"""
Resolution recommendation engine.
Provides resolution recommendations based on similar historical tickets.
"""
from typing import List, Dict
from openai import OpenAI
import config


class ResolutionRecommender:
    """Provides resolution recommendations for new tickets."""
    
    def __init__(self):
        """Initialize the resolution recommender."""
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not provided")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
    
    def recommend_resolution(self, new_ticket: str, similar_tickets: List[Dict]) -> Dict:
        """
        Generate resolution recommendation based on similar tickets.
        
        Args:
            new_ticket: Description of the new ticket
            similar_tickets: List of similar historical tickets
            
        Returns:
            Dictionary with recommendation details
        """
        if not similar_tickets:
            return {
                'recommendation': 'No similar tickets found. This appears to be a new type of issue.',
                'confidence': 'low',
                'similar_tickets': []
            }
        
        # Build context from similar tickets
        context = self._build_context(similar_tickets)
        
        # Generate recommendation using LLM
        prompt = self._create_recommendation_prompt(new_ticket, context)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Kubernetes support engineer providing resolution recommendations for troubleshooting tickets. Analyze similar past tickets and provide actionable recommendations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        recommendation = response.choices[0].message.content
        
        # Determine confidence based on similarity scores
        avg_similarity = sum(t['similarity_score'] for t in similar_tickets) / len(similar_tickets)
        confidence = self._calculate_confidence(avg_similarity, len(similar_tickets))
        
        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'average_similarity': avg_similarity,
            'similar_tickets_count': len(similar_tickets),
            'similar_tickets': [
                {
                    'number': t['number'],
                    'title': t['title'],
                    'url': t['url'],
                    'similarity_score': t['similarity_score'],
                    'state': t['state'],
                    'category': t.get('category', 'general')
                }
                for t in similar_tickets
            ]
        }
    
    def _build_context(self, similar_tickets: List[Dict]) -> str:
        """
        Build context string from similar tickets.
        
        Args:
            similar_tickets: List of similar tickets
            
        Returns:
            Context string
        """
        context_parts = []
        
        for i, ticket in enumerate(similar_tickets, 1):
            part = f"\n--- Similar Ticket #{i} (Similarity: {ticket['similarity_score']:.2f}) ---\n"
            part += f"Title: {ticket['title']}\n"
            part += f"Body: {ticket['body'][:500]}...\n"  # Limit body length
            part += f"State: {ticket['state']}\n"
            part += f"Category: {ticket.get('category', 'general')}\n"
            part += f"Support Level: {ticket.get('support_level', 'unspecified')}\n"
            
            # Add resolution information if ticket is closed
            if ticket['state'] == 'closed' and ticket.get('comments'):
                # Get last few comments that might contain resolution
                resolution_comments = ticket['comments'][-2:]
                if resolution_comments:
                    part += "Resolution comments:\n"
                    for comment in resolution_comments:
                        part += f"- {comment['body'][:300]}...\n"
            
            context_parts.append(part)
        
        return '\n'.join(context_parts)
    
    def _create_recommendation_prompt(self, new_ticket: str, context: str) -> str:
        """
        Create prompt for the LLM to generate recommendations.
        
        Args:
            new_ticket: New ticket description
            context: Context from similar tickets
            
        Returns:
            Prompt string
        """
        prompt = f"""I need help resolving a Kubernetes support ticket. Based on similar historical tickets, please provide a resolution recommendation.

NEW TICKET:
{new_ticket}

SIMILAR HISTORICAL TICKETS:
{context}

Please provide:
1. A summary of what the issue appears to be
2. Step-by-step resolution recommendations based on the similar tickets
3. Any relevant documentation or configuration that should be checked
4. Potential root causes to investigate
5. Preventive measures to avoid this issue in the future

Focus on actionable steps that the support team can take."""
        
        return prompt
    
    def _calculate_confidence(self, avg_similarity: float, num_tickets: int) -> str:
        """
        Calculate confidence level based on similarity and number of tickets.
        
        Args:
            avg_similarity: Average similarity score
            num_tickets: Number of similar tickets
            
        Returns:
            Confidence level string
        """
        # High confidence: high similarity and multiple tickets
        if avg_similarity >= 0.8 and num_tickets >= 3:
            return 'high'
        # Medium confidence: moderate similarity or fewer tickets
        elif avg_similarity >= 0.6 and num_tickets >= 2:
            return 'medium'
        # Low confidence: low similarity or very few tickets
        else:
            return 'low'
