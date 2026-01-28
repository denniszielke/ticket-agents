"""
Resolution recommendation agent using Microsoft Agent Framework.
Provides resolution recommendations based on similar historical tickets.
"""
import asyncio
from typing import List, Dict
from agent_framework import ChatAgent
import config
from model_client import create_chat_client


class ResolutionAgent:
    """AI agent for providing resolution recommendations using Microsoft Agent Framework."""
    
    def __init__(self):
        """Initialize the resolution agent."""
        self.model_name = config.COMPLETION_MODEL_NAME
        self.agent = None
    
    async def _ensure_agent(self):
        """Ensure the agent is initialized."""
        if self.agent is None:
            chat_client = create_chat_client(
                model_name=self.model_name,
                agent_name="TicketResolutionAgent"
            )
            
            self.agent = ChatAgent(
                chat_client=chat_client,
                instructions="""You are an expert Kubernetes support engineer providing resolution recommendations for troubleshooting tickets.

Your role is to:
1. Analyze new support tickets related to Kubernetes and Azure AKS
2. Review similar historical tickets that were previously resolved
3. Provide actionable, step-by-step resolution recommendations
4. Focus on practical solutions for documentation, configuration, operational, and provisioning issues

When providing recommendations:
- Be specific and actionable
- Reference similar resolved tickets when relevant
- Provide step-by-step instructions
- Include relevant documentation or configuration checks
- Suggest root cause investigations
- Recommend preventive measures

Always prioritize helping the support team quickly resolve the issue.""",
                name="TicketResolutionAgent"
            )
    
    async def recommend_resolution(self, new_ticket: str, similar_tickets: List[Dict]) -> Dict:
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
        
        # Create prompt for the agent
        prompt = self._create_recommendation_prompt(new_ticket, context)
        
        # Ensure agent is initialized
        await self._ensure_agent()
        
        # Generate recommendation using the agent
        response = await self.agent.run(prompt)
        
        # Extract the text response
        recommendation = response.messages[-1].content if response.messages else "Unable to generate recommendation"
        
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
        Create prompt for the agent to generate recommendations.
        
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


# Synchronous wrapper for backward compatibility
class ResolutionRecommender:
    """Synchronous wrapper for ResolutionAgent."""
    
    def __init__(self):
        """Initialize the resolution recommender."""
        self.agent = ResolutionAgent()
    
    def recommend_resolution(self, new_ticket: str, similar_tickets: List[Dict]) -> Dict:
        """
        Generate resolution recommendation (synchronous).
        
        Args:
            new_ticket: Description of the new ticket
            similar_tickets: List of similar historical tickets
            
        Returns:
            Dictionary with recommendation details
        """
        return asyncio.run(self.agent.recommend_resolution(new_ticket, similar_tickets))
