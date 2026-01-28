"""
Model client for both Azure OpenAI and OpenAI endpoints.
Based on: https://github.com/denniszielke/omni-agent-mesh/blob/main/samples/shared/model_client.py
"""
import os
import logging
from typing import Optional

from agent_framework import BaseChatClient
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient
from agent_framework.openai import OpenAIChatClient
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION", "2024-02-15")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Azure AI Project settings
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")


def create_embedding_client() -> AzureOpenAI | OpenAI:
    """
    Create an embedding client (Azure OpenAI or OpenAI).
    
    Returns:
        AzureOpenAI or OpenAI client for embeddings
    """
    # Try Azure OpenAI first
    if AZURE_OPENAI_ENDPOINT:
        logger.info("Using Azure OpenAI for embeddings")
        openai_credential = None
        token_provider = None
        api_key = AZURE_OPENAI_API_KEY or None

        if not api_key:
            logger.info("Using Azure AD authentication for embeddings")
            openai_credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                openai_credential, "https://cognitiveservices.azure.com/.default"
            )
            return AzureOpenAI(
                azure_deployment=AZURE_OPENAI_EMBEDDING_MODEL,
                api_version=AZURE_OPENAI_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
            )
        
        logger.info("Using API key authentication for embeddings")
        return AzureOpenAI(
            azure_deployment=AZURE_OPENAI_EMBEDDING_MODEL,
            api_version=AZURE_OPENAI_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=api_key,
        )
    
    # Fall back to OpenAI
    if OPENAI_API_KEY:
        logger.info("Using OpenAI for embeddings")
        return OpenAI(api_key=OPENAI_API_KEY)
    
    raise ValueError(
        "No embedding client configuration found. Set either AZURE_OPENAI_ENDPOINT or OPENAI_API_KEY"
    )


async def setup_azure_ai_observability(enable_sensitive_data: Optional[bool] = None) -> None:
    """
    Set up tracing in Azure AI Project.
    
    This will take the connection string from the AIProjectClient instance.
    It will override any connection string that is set in the environment variables.
    It will disable any OTLP endpoint that might have been set.
    
    Args:
        enable_sensitive_data: Whether to enable sensitive data logging
    """
    conn_string = None

    try:
        project_endpoint = AZURE_AI_PROJECT_ENDPOINT.strip()

        if project_endpoint:
            logger.info("AZURE_AI_PROJECT_ENDPOINT found: %s", project_endpoint)
            print("Using Azure AI Project Endpoint authentication.")
        
            credential = DefaultAzureCredential()
            project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)
            conn_string = project_client.telemetry.get_application_insights_connection_string()

        app_insights_connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()

        if not conn_string and app_insights_connection_string:
            logger.info("Using Application Insights connection string from environment variable.")
            conn_string = app_insights_connection_string
        
        logger.info("Fetched Application Insights connection string from Azure AI Project.")
    except ResourceNotFoundError:
        print("No Application Insights connection string found for the Azure AI Project.")
        return
    
    from agent_framework.observability import setup_observability

    if not conn_string:
        logger.warning("No Application Insights connection string found. Observability will not be set up.")
        return
    
    setup_observability(
        applicationinsights_connection_string=conn_string,
        enable_sensitive_data=enable_sensitive_data
    )
    logger.info("Observability is set up with Application Insights connection string from Azure AI Project.")


def create_chat_client(model_name: str, agent_name: str = "") -> BaseChatClient:
    """
    Create a chat client (Azure OpenAI, Azure AI Agent, or OpenAI).
    
    Args:
        model_name: Name of the model/deployment
        agent_name: Optional agent name for Azure AI Agent
        
    Returns:
        BaseChatClient instance
    """
    if (not model_name) or model_name.strip() == "":
        logger.error("Model name is missing.")
        raise ValueError(
            "Model name for chat client is not set. Please provide a model name."
        )

    # Try Azure AI Project first
    project_endpoint = AZURE_AI_PROJECT_ENDPOINT.strip()
    
    if project_endpoint:
        logger.info("AZURE_AI_PROJECT_ENDPOINT found: %s", project_endpoint)
        print("Using Azure AI Project Endpoint authentication.")
        credential = DefaultAzureCredential()
        return AzureAIAgentClient(
            project_endpoint=project_endpoint,
            credential=credential,
            model_deployment_name=model_name,
            agent_name=agent_name,
            should_cleanup_agent=False
        )
    
    # Try Azure OpenAI
    azure_endpoint = AZURE_OPENAI_ENDPOINT.strip()
    azure_api_key = AZURE_OPENAI_API_KEY.strip()
    
    if azure_endpoint:
        logger.info("AZURE_OPENAI_ENDPOINT found: %s", azure_endpoint)

        if azure_api_key:
            print("Using Azure OpenAI API key authentication.")
            logger.info("Using API key authentication.")
            return AzureOpenAIChatClient(
                deployment_name=model_name,
                azure_api_key=azure_api_key,
                endpoint=azure_endpoint,
            )
        else:
            print("Using Azure OpenAI AAD authentication.")
            logger.info("Using AAD authentication.")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            return AzureOpenAIChatClient(
                deployment_name=model_name,
                ad_token_provider=token_provider,
                endpoint=azure_endpoint,
            )
    
    # Fall back to OpenAI
    if OPENAI_API_KEY:
        logger.info("Using OpenAI")
        print("Using OpenAI authentication.")
        return OpenAIChatClient(
            model=model_name,
            api_key=OPENAI_API_KEY,
        )
    
    raise ValueError(
        "No chat client configuration found. Set AZURE_AI_PROJECT_ENDPOINT, "
        "AZURE_OPENAI_ENDPOINT, or OPENAI_API_KEY"
    )
