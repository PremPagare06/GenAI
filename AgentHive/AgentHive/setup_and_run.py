"""
Setup script to initialize the ticket analysis system
"""

import os
import sys


def setup_system():
    """Setup the ticket analysis system"""
    print("=" * 80)
    print("TICKET ANALYSIS AGENT - SETUP")
    print("=" * 80)

    # Step 1: Generate dummy tickets
    print("\n[1/3] Generating dummy historical ticket PDFs...")
    try:
        from generate_dummy_tickets import generate_all_tickets

        generate_all_tickets(num_tickets=15)
    except Exception as e:
        print(f"Error generating tickets: {str(e)}")
        return False

    # Step 2: Initialize vector store and load tickets
    print("\n[2/3] Initializing vector store and loading tickets...")
    try:
        from vector_store import TicketVectorStore
        from ticket_agent import TicketAnalysisAgent

        vector_store = TicketVectorStore(persist_directory="./chroma_db")
        agent = TicketAnalysisAgent(vector_store)
        agent.load_historical_tickets_from_pdfs("past_tickets")
    except Exception as e:
        print(f"Error loading tickets: {str(e)}")
        return False

    # Step 3: Run a test analysis
    print("\n[3/3] Running test analysis...")
    try:
        from datetime import datetime

        test_ticket = {
            "ticket_number": "TEST_INC001",
            "category": "Network",
            "priority": "P2 - High",
            "issue": "Cannot connect to VPN",
            "description": "User experiencing VPN connection issues. Getting timeout error when trying to connect from home.",
            "requester": "test.user@company.com",
            "created_date": datetime.now().isoformat(),
        }

        results = agent.analyze_incoming_ticket(test_ticket, top_k=3)
        agent.save_analysis_report(results, "test_analysis_report.json")

    except Exception as e:
        print(f"Error running test: {str(e)}")
        return False

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print("\nThe system is ready to use. You can now:")
    print("1. Run 'python ticket_agent.py' to analyze tickets")
    print("2. Import and use the TicketAnalysisAgent class in your own code")
    print("3. Check 'test_analysis_report.json' for the sample analysis")
    print("\n" + "=" * 80)

    return True


if __name__ == "__main__":
    success = setup_system()
    sys.exit(0 if success else 1)
