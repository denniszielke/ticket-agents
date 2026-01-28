# Ticket Agents

An intelligent GitHub issue resolution recommendation system for Kubernetes support teams. This application indexes historical GitHub issues (troubleshooting tickets) and provides AI-powered resolution recommendations for new tickets based on similar past issues.

## Features

- 🔍 **Issue Indexing**: Fetches and indexes GitHub issues with semantic embeddings
- 🎯 **Smart Search**: Finds similar historical tickets using semantic similarity
- 🤖 **AI Recommendations**: Generates resolution recommendations based on similar resolved tickets
- 📊 **Multi-Level Support**: Handles first, second, and third-level support categorization
- 📝 **Category Detection**: Automatically categorizes tickets (documentation, configuration, operational, provisioning)
- 📈 **Statistics**: Provides insights into your ticket database

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

Edit `.env` and add your credentials:
- `GITHUB_TOKEN`: Your GitHub personal access token
- `GITHUB_REPO`: Repository in format `owner/repository`
- `OPENAI_API_KEY`: Your OpenAI API key

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

Example:
```bash
python main.py index --repo "owner/repo" --state closed --labels "kubernetes,support"
```

### 2. Search for Similar Tickets

Search for tickets similar to a query:

```bash
python main.py search "cluster fails to provision in Azure"
```

Options:
- `--top-k`: Number of similar tickets to return (default: 5)

### 3. Get Resolution Recommendations

Get AI-powered resolution recommendations for a new ticket:

```bash
python main.py recommend "My AKS cluster is not starting after configuration change"
```

Options:
- `--top-k`: Number of similar tickets to consider (default: 5)
- `--output`: Save recommendation to JSON file

Example:
```bash
python main.py recommend "Pods stuck in pending state" --output recommendation.json
```

### 4. View Statistics

View statistics about your indexed tickets:

```bash
python main.py stats
```

## How It Works

### Indexing Process

1. **Fetch Issues**: Retrieves issues from GitHub using the GitHub API
2. **Extract Metadata**: Extracts title, body, labels, comments, and state
3. **Categorize**: Automatically categorizes tickets based on content and labels
4. **Generate Embeddings**: Creates semantic embeddings using OpenAI's embedding model
5. **Store Index**: Saves tickets and embeddings to `ticket_index.json`

### Recommendation Process

1. **Query Analysis**: Generates embedding for the new ticket description
2. **Similarity Search**: Finds most similar historical tickets using cosine similarity
3. **Context Building**: Builds context from similar tickets including resolutions
4. **AI Generation**: Uses GPT model to generate actionable recommendations
5. **Confidence Scoring**: Calculates confidence based on similarity and ticket count

## Architecture

```
ticket-agents/
├── config.py                    # Configuration management
├── github_fetcher.py            # GitHub API integration
├── ticket_indexer.py            # Indexing and similarity search
├── resolution_recommender.py    # AI-powered recommendations
├── main.py                      # CLI interface
├── requirements.txt             # Python dependencies
└── ticket_index.json            # Indexed tickets (generated)
```

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

## Example Workflow

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

## Requirements

- Python 3.8+
- GitHub account with API access
- OpenAI API key
- Internet connection for API calls

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub personal access token | Yes |
| `GITHUB_REPO` | Repository name (owner/repo) | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_MODEL` | OpenAI model to use | No (default: gpt-4o-mini) |
| `INDEX_FILE` | Path to index file | No (default: ticket_index.json) |

## Troubleshooting

### No tickets indexed
- Ensure your GitHub token has read access to issues
- Check that the repository name is correct
- Verify issues exist in the repository

### API rate limits
- GitHub: 5,000 requests/hour for authenticated users
- OpenAI: Depends on your plan

### Low-quality recommendations
- Index more tickets (at least 20+ recommended)
- Ensure tickets have detailed descriptions
- Include resolved tickets with resolution comments

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details