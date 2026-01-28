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

# Application settings
INDEX_FILE = os.getenv('INDEX_FILE', 'ticket_index.json')
