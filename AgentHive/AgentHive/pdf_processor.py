"""
PDF processor to extract ticket information from PDF files
"""

from pypdf import PdfReader
import os
from typing import Dict, Any, List
import re


class TicketPDFProcessor:
    """Process ticket PDFs and extract structured information"""

    def __init__(self):
        """Initialize the PDF processor"""
        pass

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text as string
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {str(e)}")
            return ""

    def parse_ticket_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse ticket information from extracted text

        Args:
            text: Extracted text from PDF

        Returns:
            Dictionary containing parsed ticket information
        """
        ticket_data = {}

        # Extract ticket number
        ticket_match = re.search(r"Ticket Number:\s*(\S+)", text)
        if ticket_match:
            ticket_data["ticket_number"] = ticket_match.group(1)

        # Extract priority
        priority_match = re.search(r"Priority:\s*(.+?)(?:\n|$)", text)
        if priority_match:
            ticket_data["priority"] = priority_match.group(1).strip()

        # Extract status
        status_match = re.search(r"Status:\s*(.+?)(?:\n|$)", text)
        if status_match:
            ticket_data["status"] = status_match.group(1).strip()

        # Extract category
        category_match = re.search(r"Category:\s*(.+?)(?:\n|$)", text)
        if category_match:
            ticket_data["category"] = category_match.group(1).strip()

        # Extract created date
        created_match = re.search(r"Created Date:\s*(.+?)(?:\n|$)", text)
        if created_match:
            ticket_data["created_date"] = created_match.group(1).strip()

        # Extract resolved date
        resolved_match = re.search(r"Resolved Date:\s*(.+?)(?:\n|$)", text)
        if resolved_match:
            ticket_data["resolved_date"] = resolved_match.group(1).strip()

        # Extract assigned to
        assigned_match = re.search(r"Assigned To:\s*(.+?)(?:\n|$)", text)
        if assigned_match:
            ticket_data["assigned_to"] = assigned_match.group(1).strip()

        # Extract requester
        requester_match = re.search(r"Requester:\s*(.+?)(?:\n|$)", text)
        if requester_match:
            ticket_data["requester"] = requester_match.group(1).strip()

        # Extract issue summary
        issue_match = re.search(
            r"Issue Summary\s*(.+?)(?=Detailed Description|$)", text, re.DOTALL
        )
        if issue_match:
            ticket_data["issue"] = issue_match.group(1).strip()

        # Extract detailed description
        desc_match = re.search(
            r"Detailed Description\s*(.+?)(?=Resolution|$)", text, re.DOTALL
        )
        if desc_match:
            ticket_data["description"] = desc_match.group(1).strip()

        # Extract resolution
        resolution_match = re.search(r"Resolution\s*(.+?)$", text, re.DOTALL)
        if resolution_match:
            ticket_data["resolution"] = resolution_match.group(1).strip()

        return ticket_data

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a single PDF file and extract ticket information

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing ticket information
        """
        text = self.extract_text_from_pdf(pdf_path)
        ticket_data = self.parse_ticket_from_text(text)
        ticket_data["source_file"] = os.path.basename(pdf_path)
        return ticket_data

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Process all PDF files in a directory

        Args:
            directory_path: Path to directory containing PDF files

        Returns:
            List of ticket dictionaries
        """
        tickets = []

        if not os.path.exists(directory_path):
            print(f"Directory not found: {directory_path}")
            return tickets

        pdf_files = [f for f in os.listdir(directory_path) if f.endswith(".pdf")]

        print(f"Found {len(pdf_files)} PDF files in {directory_path}")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(directory_path, pdf_file)
            print(f"Processing: {pdf_file}")

            ticket_data = self.process_pdf(pdf_path)

            if ticket_data:
                tickets.append(ticket_data)
                print(
                    f"  Extracted ticket: {ticket_data.get('ticket_number', 'Unknown')}"
                )
            else:
                print(f"  Failed to extract data from {pdf_file}")

        print(f"\nSuccessfully processed {len(tickets)} tickets")
        return tickets


if __name__ == "__main__":
    # Test the PDF processor
    processor = TicketPDFProcessor()

    # Process all PDFs in the past_tickets directory
    tickets = processor.process_directory("past_tickets")

    if tickets:
        print(f"\nSample ticket data:")
        print(f"Ticket Number: {tickets[0].get('ticket_number')}")
        print(f"Category: {tickets[0].get('category')}")
        print(f"Issue: {tickets[0].get('issue')}")
