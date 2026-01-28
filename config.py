"""
Configuration module for the ticket agents system.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GitHub settings
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_EMBEDDING_MODEL = os.getenv('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
AZURE_OPENAI_VERSION = os.getenv('AZURE_OPENAI_VERSION', '2024-02-15')

# Azure AI Project settings
AZURE_AI_PROJECT_ENDPOINT = os.getenv('AZURE_AI_PROJECT_ENDPOINT')

# Application settings
INDEX_FILE = os.getenv('INDEX_FILE', 'ticket_index.json')
COMPLETION_MODEL_NAME = os.getenv('COMPLETION_MODEL_NAME', 'gpt-4o-mini')
