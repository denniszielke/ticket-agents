# Ticket Agents

An intelligent GitHub issue resolution recommendation system for Kubernetes support teams, built with the **Microsoft Agent Framework**. This application indexes historical GitHub issues (troubleshooting tickets) and provides AI-powered resolution recommendations for new tickets based on similar past issues.

## Features

- 🤖 **Microsoft Agent Framework**: Built on Microsoft's agent-framework for robust, scalable AI agents
- 🔄 **Flexible Model Support**: Works with OpenAI, Azure OpenAI, and Azure AI Project endpoints
- 🗄️ **Azure AI Search**: Enterprise-grade vector database with managed identity support
- 🔍 **Issue Indexing**: Fetches and indexes GitHub issues with semantic embeddings
- 🎯 **Smart Filtering**: Filter by issue IDs, types, labels, or state
- 🔎 **Smart Search**: Finds similar historical tickets using vector similarity
- 💡 **AI Recommendations**: Generates resolution recommendations based on similar resolved tickets
- 📊 **Multi-Level Support**: Handles first, second, and third-level support categorization
- 📝 **Category Detection**: Automatically categorizes tickets (documentation, configuration, operational, provisioning)
- 📈 **Statistics**: Provides insights into your ticket database
- 🔭 **Observability**: Optional Azure Application Insights integration

## Use Cases

This system is designed for Kubernetes support teams dealing with:
- Documentation requests (how to provision Kubernetes clusters in Azure)
- Configuration issues (cluster settings, parameters)
- Operational problems (incidents, outages, performance issues)
- Provisioning and deployment challenges

## Installation

1. Clone the repository:
```bash
git clone https://github.com/denniszielke/ticket-agents.git
cd ticket-agents
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and configure your preferred AI provider:

**Option 1: OpenAI (Direct)**
```env
OPENAI_API_KEY=your_openai_api_key
COMPLETION_MODEL_NAME=gpt-4o-mini
```

**Option 2: Azure OpenAI**
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
COMPLETION_MODEL_NAME=gpt-4o-mini
```

**Option 3: Azure AI Project (with Azure AI Agents)**
```env
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
COMPLETION_MODEL_NAME=gpt-4o-mini
```

**Option 4: Azure AI Search (Vector Database)**
```env
# Enable Azure AI Search
USE_AZURE_SEARCH=true
AZURE_AI_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_AI_SEARCH_KEY=your_api_key  # Optional - uses managed identity if not provided
AZURE_AI_SEARCH_INDEX_NAME=tickets-index
EMBEDDING_DIMENSIONS=1536
```

Also configure GitHub access:
```env
GITHUB_TOKEN=your_github_token
GITHUB_REPO=owner/repository
```

## Usage

### 1. Index GitHub Issues

First, index your existing GitHub issues:

```bash
python main.py index
```

Options:
- `--repo`: GitHub repository (overrides .env)
- `--token`: GitHub token (overrides .env)
- `--state`: Issue state (`open`, `closed`, or `all`, default: `all`)
- `--labels`: Filter by labels (comma-separated)
- `--issue-ids`: Index specific issue numbers (comma-separated)
- `--issue-types`: Filter by types (documentation, configuration, operational, provisioning, general)
- `--use-azure-search`: Use Azure AI Search instead of local JSON file

Examples:
```bash
# Index all closed issues
python main.py index --repo "owner/repo" --state closed --labels "kubernetes,support"

# Index specific issues
python main.py index --issue-ids 123,456,789

# Index only documentation issues
python main.py index --issue-types documentation,configuration

# Use Azure AI Search (creates index automatically)
python main.py index --use-azure-search
```

### 2. Search for Similar Tickets

Search for tickets similar to a query:

```bash
python main.py search "cluster fails to provision in Azure"
```

Options:
- `--top-k`: Number of similar tickets to return (default: 5)
- `--use-azure-search`: Use Azure AI Search instead of local JSON file

Example:
```bash
python main.py search "node pool scaling issue" --top-k 10 --use-azure-search
```

### 3. Get Resolution Recommendations

Get AI-powered resolution recommendations for a new ticket:

```bash
python main.py recommend "My AKS cluster nodes are stuck in NotReady state after upgrade"
```

Options:
- `--top-k`: Number of similar tickets to consider (default: 5)
- `--output`: Save recommendation to JSON file
- `--use-azure-search`: Use Azure AI Search instead of local JSON file

```bash
python main.py recommend "My AKS cluster is not starting after configuration change"
```

Options:
- `--top-k`: Number of similar tickets to consider (default: 5)
- `--output`: Save recommendation to JSON file

Example:
```bash
python main.py recommend "Pods stuck in pending state" --output recommendation.json --use-azure-search
```

### 4. View Statistics

View statistics about your indexed tickets:

```bash
python main.py stats
```

Options:
- `--use-azure-search`: Use Azure AI Search instead of local JSON file

## How It Works

### Indexing Process

1. **Fetch Issues**: Retrieves issues from GitHub using the GitHub API
2. **Filter Issues**: Optionally filters by IDs, types, labels, or state
3. **Extract Metadata**: Extracts title, body, labels, comments, and state
4. **Categorize**: Automatically categorizes tickets based on content and labels
5. **Generate Embeddings**: Creates semantic embeddings using OpenAI's embedding model
6. **Store Index**: Saves to Azure AI Search (with automatic index creation) or local JSON file

### Recommendation Process

1. **Query Analysis**: Generates embedding for the new ticket description
2. **Vector Search**: Finds most similar historical tickets using HNSW algorithm (Azure AI Search) or cosine similarity (local)
3. **Context Building**: Builds context from similar tickets including resolutions
4. **AI Generation**: Uses GPT model to generate actionable recommendations
5. **Confidence Scoring**: Calculates confidence based on similarity and ticket count

## Architecture

The system is built on the **Microsoft Agent Framework**, providing a robust foundation for AI agent orchestration and flexible model deployment.

```
ticket-agents/
├── config.py                    # Configuration management
├── model_client.py              # Flexible model client (Azure OpenAI + OpenAI)
├── github_fetcher.py            # GitHub API integration with filtering
├── ticket_indexer.py            # Local JSON indexing and similarity search
├── azure_search_indexer.py      # Azure AI Search integration (NEW)
├── resolution_agent.py          # AI agent for recommendations (Agent Framework)
├── resolution_recommender.py    # Legacy sync interface (deprecated)
├── main.py                      # CLI interface
├── requirements.txt             # Python dependencies
└── ticket_index.json            # Indexed tickets (generated, local mode)
```

### Model Client

The `model_client.py` provides a unified interface supporting:
- **OpenAI**: Direct OpenAI API access
- **Azure OpenAI**: Azure-hosted OpenAI models with API key or AAD auth
- **Azure AI Project**: Full Azure AI Agent service with observability

### Azure AI Search Integration

The `azure_search_indexer.py` provides enterprise-grade vector storage:
- **Authentication**: API key or managed identity (DefaultAzureCredential)
- **Auto Index Creation**: Creates index schema automatically on first run
- **Vector Search**: HNSW algorithm for efficient similarity search
- **Scalability**: Handles large ticket datasets efficiently
- **Hybrid Storage**: Can be used alongside local JSON storage

The system automatically selects the appropriate client based on environment variables.

## Support Level Detection

The system automatically detects support levels from labels:
- **L1/Level-1/First-level**: Basic support issues
- **L2/Level-2/Second-level**: Intermediate technical issues
- **L3/Level-3/Third-level**: Complex technical issues

## Category Detection

Automatic categorization based on content and labels:
- **Documentation**: Missing guides, how-to requests
- **Configuration**: Settings, parameters, config issues
- **Operational**: Incidents, outages, performance
- **Provisioning**: Cluster creation, deployment
- **General**: Other issues

## Example Workflows

### Basic Workflow
```bash
# 1. Index your GitHub issues
python main.py index --repo "myorg/k8s-support" --state all

# 2. View statistics
python main.py stats

# 3. Get recommendation for a new ticket
python main.py recommend "AKS node pool not scaling automatically" --output rec.json

# 4. Search for similar historical tickets
python main.py search "node pool scaling issue"
```

### Azure AI Search Workflow
```bash
# 1. Index with Azure AI Search (creates index automatically)
python main.py index --use-azure-search

# 2. Index specific issues
python main.py index --issue-ids 123,456,789 --use-azure-search

# 3. Search with Azure AI Search
python main.py search "scaling issue" --use-azure-search

# 4. Get recommendations with Azure AI Search
python main.py recommend "Pod networking failure" --use-azure-search --output rec.json
```

### Filtered Indexing
```bash
# Index only documentation issues
python main.py index --issue-types documentation

# Index specific issues by ID
python main.py index --issue-ids 1,2,3,4,5

# Index with multiple filters
python main.py index --state closed --labels "L2,urgent" --issue-types operational
```

## Requirements

- Python 3.8+
- GitHub account with API access
- OpenAI API key
- Internet connection for API calls

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | Yes | - |
| `GITHUB_REPO` | Repository name (owner/repo) | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Conditional* | - |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Conditional* | - |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | No | - |
| `AZURE_OPENAI_EMBEDDING_MODEL` | Embedding model deployment name | No | text-embedding-3-small |
| `AZURE_OPENAI_VERSION` | Azure OpenAI API version | No | 2024-02-15 |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Project endpoint | Conditional* | - |
| `AZURE_AI_SEARCH_ENDPOINT` | Azure AI Search endpoint | No | - |
| `AZURE_AI_SEARCH_KEY` | Azure AI Search API key | No | Uses managed identity if not set |
| `AZURE_AI_SEARCH_INDEX_NAME` | Search index name | No | tickets-index |
| `USE_AZURE_SEARCH` | Use Azure Search by default | No | false |
| `EMBEDDING_DIMENSIONS` | Vector embedding dimensions | No | 1536 |
| `COMPLETION_MODEL_NAME` | Model/deployment name for completions | No | gpt-4o-mini |
| `INDEX_FILE` | Path to local index file | No | ticket_index.json |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights for observability | No | - |

\* At least one AI provider must be configured: `OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, or `AZURE_AI_PROJECT_ENDPOINT`

## Troubleshooting

### No tickets indexed
- Ensure your GitHub token has read access to issues
- Check that the repository name is correct
- Verify issues exist in the repository
- If using Azure AI Search, check endpoint and authentication

### Azure AI Search issues
- Verify `AZURE_AI_SEARCH_ENDPOINT` is correct
- Ensure API key is valid or managed identity has permissions
- Check index name doesn't contain invalid characters
- Index is created automatically on first run

### API rate limits
- GitHub: 5,000 requests/hour for authenticated users
- OpenAI: Depends on your plan
- Azure AI Search: Depends on tier (Basic, Standard, etc.)

### Low-quality recommendations
- Index more tickets (at least 20+ recommended)
- Ensure tickets have detailed descriptions
- Include resolved tickets with resolution comments

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details