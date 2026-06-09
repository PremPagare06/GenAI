"""
Main Agentic AI application for analyzing ServiceNow tickets
"""

from vector_store import TicketVectorStore
from pdf_processor import TicketPDFProcessor
from typing import Dict, Any, List
import json
from datetime import datetime


class TicketAnalysisAgent:
    """AI Agent for analyzing incoming tickets and finding similar historical tickets"""

    def __init__(self, vector_store: TicketVectorStore):
        """
        Initialize the ticket analysis agent

        Args:
            vector_store: Instance of TicketVectorStore
        """
        self.vector_store = vector_store
        self.pdf_processor = TicketPDFProcessor()

    def analyze_incoming_ticket(
        self, ticket_data: Dict[str, Any], top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze an incoming ticket and find similar historical tickets with solutions

        Args:
            ticket_data: Dictionary containing the new ticket information
            top_k: Number of similar tickets to retrieve

        Returns:
            Analysis results with similar tickets and recommended solutions
        """
        print("\n" + "=" * 80)
        print("TICKET ANALYSIS AGENT")
        print("=" * 80)

        # Display incoming ticket information
        print("\nINCOMING TICKET:")
        print(f"  Ticket Number: {ticket_data.get('ticket_number', 'N/A')}")
        print(f"  Category: {ticket_data.get('category', 'N/A')}")
        print(f"  Issue: {ticket_data.get('issue', 'N/A')}")
        print(f"  Description: {ticket_data.get('description', 'N/A')[:100]}...")

        # Search for similar tickets
        print(f"\nSearching for {top_k} similar historical tickets...")
        similar_tickets = self.vector_store.search_similar_tickets(
            ticket_data, n_results=top_k
        )

        # Prepare analysis results
        analysis_results = {
            "incoming_ticket": ticket_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "similar_tickets_found": len(similar_tickets),
            "similar_tickets": [],
            "recommended_solution": None,
        }

        if similar_tickets:
            print(f"\nFound {len(similar_tickets)} similar tickets\n")

            for idx, ticket in enumerate(similar_tickets, 1):
                similarity_score = ticket.get("similarity_score", 0)
                similarity_percentage = (
                    similarity_score * 100 if similarity_score else 0
                )

                ticket_info = {
                    "rank": idx,
                    "ticket_id": ticket["ticket_id"],
                    "similarity_score": similarity_percentage,
                    "category": ticket["metadata"].get("category", "N/A"),
                    "issue": ticket["metadata"].get("issue", "N/A"),
                    "resolution": ticket["metadata"].get("resolution", "N/A"),
                    "resolved_date": ticket["metadata"].get("resolved_date", "N/A"),
                }

                analysis_results["similar_tickets"].append(ticket_info)

                # Display similar ticket
                print(f"{'-'*80}")
                print(f"SIMILAR TICKET #{idx} - {ticket['ticket_id']}")
                print(f"{'-'*80}")
                print(f"  Similarity Score: {similarity_percentage:.2f}%")
                print(f"  Category: {ticket_info['category']}")
                print(f"  Issue: {ticket_info['issue']}")
                print(f"  Resolution: {ticket_info['resolution'][:200]}...")
                print(f"  Resolved Date: {ticket_info['resolved_date']}")

            # Use the most similar ticket's resolution as recommended solution
            best_match = similar_tickets[0]
            if best_match.get("similarity_score", 0) > 0.7:  # 70% similarity threshold
                analysis_results["recommended_solution"] = {
                    "confidence": "HIGH",
                    "source_ticket": best_match["ticket_id"],
                    "similarity_score": best_match.get("similarity_score", 0) * 100,
                    "resolution": best_match["metadata"].get("resolution", "N/A"),
                }

                print(f"\n{'='*80}")
                print("RECOMMENDED SOLUTION (High Confidence)")
                print(f"{'='*80}")
                print(f"Based on ticket: {best_match['ticket_id']}")
                print(f"Similarity: {best_match.get('similarity_score', 0) * 100:.2f}%")
                print(f"\nSolution:\n{best_match['metadata'].get('resolution', 'N/A')}")

            elif (
                best_match.get("similarity_score", 0) > 0.5
            ):  # 50% similarity threshold
                analysis_results["recommended_solution"] = {
                    "confidence": "MEDIUM",
                    "source_ticket": best_match["ticket_id"],
                    "similarity_score": best_match.get("similarity_score", 0) * 100,
                    "resolution": best_match["metadata"].get("resolution", "N/A"),
                }

                print(f"\n{'='*80}")
                print("RECOMMENDED SOLUTION (Medium Confidence)")
                print(f"{'='*80}")
                print(f"Based on ticket: {best_match['ticket_id']}")
                print(f"Similarity: {best_match.get('similarity_score', 0) * 100:.2f}%")
                print(
                    f"\nSuggested Solution:\n{best_match['metadata'].get('resolution', 'N/A')}"
                )
                print("\nNote: Please review and adapt this solution as needed.")

            else:
                analysis_results["recommended_solution"] = {
                    "confidence": "LOW",
                    "message": "No highly similar tickets found. Manual investigation recommended.",
                }

                print(f"\n{'='*80}")
                print("LOW CONFIDENCE - Manual Investigation Recommended")
                print(f"{'='*80}")
                print("The most similar ticket has low similarity score.")
                print(
                    "Consider reviewing all similar tickets or escalating to a specialist."
                )

        else:
            print("\nNo similar tickets found in the database.")
            analysis_results["recommended_solution"] = {
                "confidence": "NONE",
                "message": "No similar historical tickets found. This appears to be a new type of issue.",
            }

        print(f"\n{'='*80}\n")

        return analysis_results

    def load_historical_tickets_from_pdfs(self, pdf_directory: str = "past_tickets"):
        """
        Load historical tickets from PDF files into the vector store

        Args:
            pdf_directory: Directory containing historical ticket PDFs
        """
        print(f"\nLoading historical tickets from: {pdf_directory}")

        # Process all PDFs
        tickets = self.pdf_processor.process_directory(pdf_directory)

        if tickets:
            # Add tickets to vector store
            print(f"\nAdding {len(tickets)} tickets to vector store...")
            self.vector_store.add_tickets_batch(tickets)

            # Display stats
            stats = self.vector_store.get_collection_stats()
            print(f"\nVector store updated successfully")
            print(f"  Total tickets in database: {stats['total_tickets']}")
        else:
            print("\nNo tickets were loaded")

    def save_analysis_report(
        self,
        analysis_results: Dict[str, Any],
        output_file: str = "analysis_report.json",
    ):
        """
        Save analysis results to a JSON file

        Args:
            analysis_results: Analysis results dictionary
            output_file: Output file path
        """
        with open(output_file, "w") as f:
            json.dump(analysis_results, f, indent=2)
        print(f"\nAnalysis report saved to: {output_file}")


def main():
    """Main function to demonstrate the ticket analysis agent"""

    # Initialize vector store
    print("Initializing Ticket Analysis Agent...")
    vector_store = TicketVectorStore(persist_directory="./chroma_db")
    agent = TicketAnalysisAgent(vector_store)

    # Load historical tickets from PDFs (only needed once or when new tickets are added)
    agent.load_historical_tickets_from_pdfs("past_tickets")

    # Example: Analyze a new incoming ticket
    print("\n" + "=" * 80)
    print("SIMULATING INCOMING TICKET FROM SERVICENOW")
    print("=" * 80)

    incoming_ticket = {
        "ticket_number": "INC9999",
        "category": "Network",
        "priority": "P2 - High",
        "issue": "VPN connection timeout error",
        "description": "User is unable to connect to the corporate VPN from home office. Getting connection timeout error after entering credentials. This started happening after the latest Windows update.",
        "requester": "john.doe@company.com",
        "created_date": datetime.now().isoformat(),
    }

    # Analyze the ticket
    results = agent.analyze_incoming_ticket(incoming_ticket, top_k=3)

    # Save analysis report
    agent.save_analysis_report(results, "analysis_report.json")

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
