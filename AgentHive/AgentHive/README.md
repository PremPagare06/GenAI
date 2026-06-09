# ServiceNow Ticket Analysis Agent 🤖

An Agentic AI application that analyzes incoming ServiceNow tickets and automatically searches for similar historical tickets to provide solutions based on past resolutions.

## 🎯 Features

- **Automated Ticket Analysis**: Analyzes incoming tickets and finds similar historical cases
- **Vector-Based Search**: Uses ChromaDB with sentence transformers for semantic similarity matching
- **PDF Processing**: Extracts and processes ticket information from PDF documents
- **Solution Recommendations**: Provides confidence-scored solution recommendations based on historical data
- **Batch Processing**: Efficiently handles multiple tickets at once

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Setup Script

This will generate dummy tickets, initialize the vector store, and run a test analysis:

```bash
python setup_and_run.py
```

### 3. Analyze Tickets

Run the main application:

```bash
python ticket_agent.py
```

## 📁 Project Structure

```
BOB/
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── README.md                     # This file
├── setup_and_run.py             # Setup and initialization script
├── generate_dummy_tickets.py    # Generate sample ticket PDFs
├── pdf_processor.py             # PDF extraction and parsing
├── vector_store.py              # ChromaDB vector store management
├── ticket_agent.py              # Main AI agent application
├── past_tickets/                # Directory for historical ticket PDFs
├── chroma_db/                   # ChromaDB persistence directory
└── analysis_report.json         # Generated analysis reports
```

## 🔧 Components

### 1. Ticket Generation (`generate_dummy_tickets.py`)

Generates realistic ServiceNow ticket PDFs with:
- Ticket metadata (number, priority, status, dates)
- Issue descriptions
- Detailed resolutions
- 15 different ticket templates covering common IT issues

### 2. PDF Processor (`pdf_processor.py`)

Extracts structured data from ticket PDFs:
- Parses ticket metadata
- Extracts issue descriptions
- Captures resolution details
- Batch processes entire directories

### 3. Vector Store (`vector_store.py`)

Manages the ChromaDB vector database:
- Uses sentence-transformers for embeddings (no API key needed)
- Stores ticket embeddings for semantic search
- Provides similarity search functionality
- Persists data locally

### 4. Ticket Analysis Agent (`ticket_agent.py`)

Main AI agent that:
- Analyzes incoming tickets
- Searches for similar historical tickets
- Provides confidence-scored recommendations
- Generates detailed analysis reports

## 💡 Usage Examples

### Analyze a New Ticket

```python
from vector_store import TicketVectorStore
from ticket_agent import TicketAnalysisAgent
from datetime import datetime

# Initialize
vector_store = TicketVectorStore()
agent = TicketAnalysisAgent(vector_store)

# Define incoming ticket
incoming_ticket = {
    'ticket_number': 'INC9999',
    'category': 'Network',
    'priority': 'P2 - High',
    'issue': 'VPN connection timeout',
    'description': 'User cannot connect to VPN from home. Getting timeout error.',
    'requester': 'user@company.com',
    'created_date': datetime.now().isoformat()
}

# Analyze
results = agent.analyze_incoming_ticket(incoming_ticket, top_k=3)

# Save report
agent.save_analysis_report(results, "analysis_report.json")
```

### Load New Historical Tickets

```python
# Load tickets from PDF directory
agent.load_historical_tickets_from_pdfs("past_tickets")
```

### Search Similar Tickets Directly

```python
from vector_store import TicketVectorStore

vector_store = TicketVectorStore()

query_ticket = {
    'category': 'Email',
    'issue': 'Outlook not syncing',
    'description': 'Emails not appearing in Outlook client'
}

similar = vector_store.search_similar_tickets(query_ticket, n_results=5)
```

## 🎨 Confidence Levels

The agent provides three confidence levels for recommendations:

- **HIGH (>70% similarity)**: Strong match found, solution highly applicable
- **MEDIUM (50-70% similarity)**: Relevant match, solution may need adaptation
- **LOW (<50% similarity)**: Weak match, manual investigation recommended

## 📊 Sample Output

```
================================================================================
TICKET ANALYSIS AGENT
================================================================================

📋 INCOMING TICKET:
  Ticket Number: INC9999
  Category: Network
  Issue: VPN connection timeout error
  Description: User is unable to connect to the corporate VPN...

🔍 Searching for 3 similar historical tickets...

✓ Found 3 similar tickets

────────────────────────────────────────────────────────────────────────────────
SIMILAR TICKET #1 - INC1000
────────────────────────────────────────────────────────────────────────────────
  Similarity Score: 87.45%
  Category: Network
  Issue: Unable to connect to VPN
  Resolution: Reset VPN credentials in Active Directory...
  Resolved Date: 2025-12-15 14:30:00

================================================================================
💡 RECOMMENDED SOLUTION (High Confidence)
================================================================================
Based on ticket: INC1000
Similarity: 87.45%

Solution:
Reset VPN credentials in Active Directory. Instructed user to download 
latest VPN client version 5.2.1. Verified firewall rules allow VPN 
traffic on port 443. Issue resolved after client update and credential reset.
```

## 🔒 Security Notes

- No API keys required for basic functionality
- All data stored locally
- Sentence transformers run locally (no external API calls)
- Optional: Can integrate OpenAI embeddings by setting `OPENAI_API_KEY` in `.env`

## 🛠️ Customization

### Add More Ticket Templates

Edit `generate_dummy_tickets.py` and add to `TICKET_TEMPLATES` list:

```python
{
    "category": "Your Category",
    "issue": "Issue summary",
    "description": "Detailed description",
    "resolution": "How it was resolved"
}
```

### Adjust Similarity Thresholds

Modify confidence thresholds in `ticket_agent.py`:

```python
if best_match.get('similarity_score', 0) > 0.7:  # HIGH confidence
    # ...
elif best_match.get('similarity_score', 0) > 0.5:  # MEDIUM confidence
    # ...
```

### Change Embedding Model

In `vector_store.py`, change the model:

```python
self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2"  # More accurate but slower
)
```

## 📝 Generated Files

- `past_tickets/*.pdf` - Historical ticket PDFs
- `chroma_db/` - Vector database storage
- `analysis_report.json` - Latest analysis results
- `test_analysis_report.json` - Test run results

## 🐛 Troubleshooting

### ChromaDB Issues

If you encounter ChromaDB errors, try:

```bash
pip install --upgrade chromadb
```

### PDF Processing Issues

Ensure reportlab and pypdf are installed:

```bash
pip install reportlab pypdf
```

### Embedding Model Download

First run will download the sentence transformer model (~80MB). Ensure internet connection.

## 🚀 Future Enhancements

- [ ] REST API for ticket submission
- [ ] Web UI for ticket analysis
- [ ] Integration with actual ServiceNow API
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Automated ticket routing
- [ ] Solution effectiveness tracking

## 📄 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Feel free to extend and customize this application for your specific use case!

---

**Built with ❤️ using ChromaDB, LangChain, and Sentence Transformers**