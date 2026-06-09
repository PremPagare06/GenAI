# Quick Start Guide - Ticket Analysis Agent

## Step-by-Step Instructions to Run and Test

### Step 1: Verify Installation

First, check if all packages are installed:

```powershell
pip list | Select-String "chromadb|sentence-transformers|pypdf|reportlab|numpy"
```

If any are missing, install them:

```powershell
pip install -r requirements.txt
```

### Step 2: Run the Setup Script

This will generate tickets, initialize the database, and run a test:

```powershell
python setup_and_run.py
```

**What this does:**
- Generates 15 dummy ticket PDFs in `past_tickets/` folder
- Creates ChromaDB vector database in `chroma_db/` folder
- Loads all tickets into the vector store
- Runs a test analysis on a sample VPN issue
- Creates `test_analysis_report.json`

### Step 3: Run the Main Application

To analyze tickets with the full demo:

```powershell
python ticket_agent.py
```

**What you'll see:**
- Analysis of an incoming VPN connection issue
- Top 3 similar historical tickets
- Similarity scores for each match
- Recommended solution based on the best match
- Confidence level (HIGH/MEDIUM/LOW)
- Analysis report saved to `analysis_report.json`

### Step 4: Test with Your Own Ticket

Create a file called `test_custom_ticket.py`:

```python
from vector_store import TicketVectorStore
from ticket_agent import TicketAnalysisAgent
from datetime import datetime

# Initialize
vector_store = TicketVectorStore()
agent = TicketAnalysisAgent(vector_store)

# Your custom ticket
my_ticket = {
    'ticket_number': 'INC9999',
    'category': 'Email',  # Try: Network, Email, Hardware, Software, etc.
    'priority': 'P2 - High',
    'issue': 'Outlook not syncing emails',
    'description': 'User reports that Outlook stopped syncing emails since this morning. Webmail works fine.',
    'requester': 'test.user@company.com',
    'created_date': datetime.now().isoformat()
}

# Analyze
results = agent.analyze_incoming_ticket(my_ticket, top_k=3)

# Save report
agent.save_analysis_report(results, "my_analysis.json")
```

Then run:

```powershell
python test_custom_ticket.py
```

### Step 5: View Generated Files

Check these files to see the results:

1. **past_tickets/** - Contains 15 PDF tickets
   ```powershell
   explorer past_tickets
   ```

2. **analysis_report.json** - Latest analysis results
   ```powershell
   notepad analysis_report.json
   ```

3. **chroma_db/** - Vector database storage
   ```powershell
   dir chroma_db
   ```

## Common Test Scenarios

### Test 1: Network Issue
```python
ticket = {
    'category': 'Network',
    'issue': 'Cannot connect to VPN',
    'description': 'VPN connection times out after entering credentials'
}
```

### Test 2: Email Problem
```python
ticket = {
    'category': 'Email',
    'issue': 'Outlook not syncing',
    'description': 'Emails not appearing in Outlook desktop client'
}
```

### Test 3: Hardware Issue
```python
ticket = {
    'category': 'Hardware',
    'issue': 'Laptop overheating',
    'description': 'Laptop gets very hot and shuts down during use'
}
```

### Test 4: Software Issue
```python
ticket = {
    'category': 'Software',
    'issue': 'Teams crashing',
    'description': 'Microsoft Teams crashes immediately on startup'
}
```

## Understanding the Output

### Similarity Scores
- **>70%** = HIGH confidence - Solution highly applicable
- **50-70%** = MEDIUM confidence - Solution may need adaptation  
- **<50%** = LOW confidence - Manual investigation recommended

### Example Output
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

Found 3 similar tickets

────────────────────────────────────────────────────────────────────────────────
SIMILAR TICKET #1 - INC1000
────────────────────────────────────────────────────────────────────────────────
  Similarity Score: 87.45%
  Category: Network
  Issue: Unable to connect to VPN
  Resolution: Reset VPN credentials in Active Directory...
```

## Troubleshooting

### Issue: "No module named 'chromadb'"
**Solution:**
```powershell
pip install chromadb sentence-transformers
```

### Issue: "No module named 'dotenv'"
**Solution:**
```powershell
pip install python-dotenv==0.21.0
```

### Issue: Unicode errors in output
**Solution:** Already fixed in the code - all special characters removed

### Issue: "past_tickets directory not found"
**Solution:**
```powershell
python generate_dummy_tickets.py
```

### Issue: Slow first run
**Explanation:** First run downloads the sentence transformer model (~80MB). Subsequent runs are fast.

## Advanced Usage

### Add More Historical Tickets

1. Create new PDFs in `past_tickets/` folder
2. Run:
```python
from ticket_agent import TicketAnalysisAgent
from vector_store import TicketVectorStore

vector_store = TicketVectorStore()
agent = TicketAnalysisAgent(vector_store)
agent.load_historical_tickets_from_pdfs("past_tickets")
```

### Reset the Database

```python
from vector_store import TicketVectorStore

vector_store = TicketVectorStore()
vector_store.reset_collection()
```

### Check Database Stats

```python
from vector_store import TicketVectorStore

vector_store = TicketVectorStore()
stats = vector_store.get_collection_stats()
print(stats)
```

## Next Steps

1. ✅ Run `python setup_and_run.py`
2. ✅ Run `python ticket_agent.py`
3. ✅ Create your own test ticket
4. ✅ Check the analysis reports
5. 🚀 Integrate with your ServiceNow instance!

## Need Help?

Check the main README.md for detailed documentation and API reference.