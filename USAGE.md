# Ticket Agents - Usage Guide

This guide demonstrates how to use the ticket-agents system for Kubernetes support ticket management.

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/denniszielke/ticket-agents.git
cd ticket-agents

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configuration

Edit `.env` and choose your AI provider:

#### Option A: OpenAI (Simplest)
```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=your-org/your-repo
OPENAI_API_KEY=sk-your_key_here
COMPLETION_MODEL_NAME=gpt-4o-mini
```

#### Option B: Azure OpenAI
```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=your-org/your-repo
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
COMPLETION_MODEL_NAME=gpt-4o-mini
```

#### Option C: Azure AI Project (Full Observability)
```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=your-org/your-repo
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
COMPLETION_MODEL_NAME=gpt-4o-mini
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

## Command Reference

### Index GitHub Issues

Index all issues from your repository:

```bash
python main.py index
```

Index only closed issues:

```bash
python main.py index --state closed
```

Index issues with specific labels:

```bash
python main.py index --labels "kubernetes,support,L2"
```

Index from a different repository:

```bash
python main.py index --repo "other-org/other-repo" --token ghp_different_token
```

### View Statistics

Get an overview of your indexed tickets:

```bash
python main.py stats
```

Example output:
```
================================================================================
TICKET INDEX STATISTICS
================================================================================

Total tickets indexed: 127

By State:
  open: 23
  closed: 104

By Category:
  documentation: 42
  configuration: 35
  operational: 28
  provisioning: 15
  general: 7

By Support Level:
  L1: 45
  L2: 52
  L3: 18
  unspecified: 12
```

### Search for Similar Tickets

Find tickets similar to a query:

```bash
python main.py search "AKS cluster fails to provision in Azure East US"
```

Customize number of results:

```bash
python main.py search "Node pool scaling issue" --top-k 10
```

Example output:
```
Found 5 similar tickets:

1. #142 - AKS provisioning timeout in East US region
   Similarity: 0.89
   State: closed
   Category: provisioning
   URL: https://github.com/org/repo/issues/142

2. #98 - Cluster creation fails with quota error
   Similarity: 0.82
   State: closed
   Category: provisioning
   URL: https://github.com/org/repo/issues/98
...
```

### Get Resolution Recommendations

Get AI-powered recommendations for a new ticket:

```bash
python main.py recommend "My AKS cluster nodes are stuck in NotReady state after upgrade"
```

Save recommendation to file:

```bash
python main.py recommend "Pods stuck in pending state" --output recommendation.json
```

Example output:
```
================================================================================
RESOLUTION RECOMMENDATION
================================================================================

Confidence: HIGH
Based on 5 similar ticket(s)
Average similarity: 0.87

--------------------------------------------------------------------------------
ISSUE SUMMARY:
The AKS cluster nodes are in NotReady state following an upgrade, which is 
preventing pods from being scheduled. This is a common post-upgrade issue.

RESOLUTION STEPS:

1. Check Node Status and Events:
   ```
   kubectl get nodes
   kubectl describe node <node-name>
   ```
   Look for errors in the events section.

2. Verify Network Plugin Status:
   This appears to be a network plugin issue based on similar tickets.
   ```
   kubectl get pods -n kube-system | grep -E "calico|cilium|azure-cni"
   ```

3. Check Node Logs:
   SSH to the node and check logs:
   ```
   journalctl -u kubelet | tail -100
   ```

4. Restart Kubelet (if needed):
   ```
   systemctl restart kubelet
   ```

5. If nodes remain NotReady, consider:
   - Cordoning and draining the problematic nodes
   - Recreating the node pool
   - Checking Azure subscription quota

RELEVANT DOCUMENTATION:
- AKS Upgrade Best Practices: https://docs.microsoft.com/azure/aks/upgrade-cluster
- Troubleshooting Node Issues: https://docs.microsoft.com/azure/aks/troubleshooting

ROOT CAUSES TO INVESTIGATE:
- Network plugin compatibility with new Kubernetes version
- Azure CNI configuration issues
- Resource constraints on nodes
- Azure platform issues in the region

PREVENTIVE MEASURES:
- Always test upgrades in non-production environments first
- Use node image upgrade before cluster upgrade
- Monitor node health metrics during upgrades
- Keep Azure CLI and kubectl updated
--------------------------------------------------------------------------------

Similar Tickets Referenced:
  - #156: Nodes NotReady after 1.27 upgrade
    Similarity: 0.92, State: closed
    URL: https://github.com/org/repo/issues/156
  - #134: Network plugin issues post-upgrade
    Similarity: 0.88, State: closed
    URL: https://github.com/org/repo/issues/134
...
```

## Programmatic Usage

You can also use the system programmatically in your Python code:

```python
from github_fetcher import GitHubIssueFetcher
from ticket_indexer import TicketIndexer
from resolution_agent import ResolutionRecommender

# Fetch and index issues
fetcher = GitHubIssueFetcher()
tickets = fetcher.fetch_issues(state='all')

indexer = TicketIndexer()
indexer.index_tickets(tickets)

# Find similar tickets
query = "How to configure AKS networking?"
similar = indexer.find_similar_tickets(query, top_k=5)

# Get recommendation
recommender = ResolutionRecommender()
result = recommender.recommend_resolution(query, similar)

print(f"Confidence: {result['confidence']}")
print(f"Recommendation: {result['recommendation']}")
```

## Best Practices

### For Best Results

1. **Index Regularly**: Re-index weekly to include new resolved tickets
   ```bash
   # Add to cron
   0 2 * * 1 cd /path/to/ticket-agents && python main.py index
   ```

2. **Include Resolution Information**: Ensure closed tickets have detailed resolution comments

3. **Use Labels Consistently**: Apply support level (L1/L2/L3) and category labels to issues

4. **Provide Context**: When searching or requesting recommendations, include as much detail as possible

5. **Review Recommendations**: AI recommendations should be reviewed by experienced engineers before application

### Label Conventions

For optimal categorization, use these label patterns:

**Support Levels:**
- `L1`, `level-1`, `first-level`: Basic support
- `L2`, `level-2`, `second-level`: Intermediate support
- `L3`, `level-3`, `third-level`: Advanced support

**Categories:**
- `documentation`: Missing or unclear documentation
- `configuration`: Configuration issues
- `operational`: Operational incidents
- `provisioning`: Cluster provisioning issues

## Troubleshooting

### "No tickets indexed"
```bash
# Check if index file exists
ls -la ticket_index.json

# Re-index
python main.py index
```

### "OpenAI API key not provided"
```bash
# Verify .env file
cat .env | grep -E "OPENAI_API_KEY|AZURE_OPENAI"

# Make sure .env is in the same directory as main.py
```

### "GitHub token not provided"
```bash
# Check GitHub token
cat .env | grep GITHUB_TOKEN

# Verify token has correct permissions (repo read access)
```

### Low-quality recommendations
- Index more tickets (minimum 20-30 recommended)
- Ensure closed tickets have resolution comments
- Use more specific queries

## Advanced Usage

### Custom Index Location

```bash
INDEX_FILE=/path/to/custom-index.json python main.py index
```

### Multiple Repositories

Create separate index files for different repositories:

```bash
# Index repo 1
GITHUB_REPO=org/repo1 INDEX_FILE=repo1-index.json python main.py index

# Index repo 2
GITHUB_REPO=org/repo2 INDEX_FILE=repo2-index.json python main.py index

# Search repo 1
INDEX_FILE=repo1-index.json python main.py search "query"
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
name: Update Ticket Index
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  update-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py index
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_REPO: ${{ github.repository }}
      - uses: actions/upload-artifact@v3
        with:
          name: ticket-index
          path: ticket_index.json
```

## Getting Help

- Review the [README.md](README.md) for architecture details
- Check [example_usage.py](example_usage.py) for programmatic examples
- Report issues on GitHub

## License

MIT License - See LICENSE file for details
