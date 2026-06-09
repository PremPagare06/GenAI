"""
Vector store management using ChromaDB for ticket embeddings
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os
from typing import List, Dict, Any
import json


class TicketVectorStore:
    """Manages the ChromaDB vector store for ticket data"""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "snow_tickets",
    ):
        """
        Initialize the vector store

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to store tickets
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Use sentence transformers for embeddings (free, no API key needed)
        self.embedding_function = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "ServiceNow ticket embeddings"},
        )

        print(f"Vector store initialized with collection: {collection_name}")
        print(f"Current collection size: {self.collection.count()} documents")

    def add_ticket(self, ticket_id: str, ticket_data: Dict[str, Any]):
        """
        Add a single ticket to the vector store

        Args:
            ticket_id: Unique identifier for the ticket
            ticket_data: Dictionary containing ticket information
        """
        # Create a comprehensive text representation for embedding
        text_for_embedding = self._create_embedding_text(ticket_data)

        # Add to collection
        self.collection.add(
            documents=[text_for_embedding], metadatas=[ticket_data], ids=[ticket_id]
        )

        print(f"Added ticket {ticket_id} to vector store")

    def add_tickets_batch(self, tickets: List[Dict[str, Any]]):
        """
        Add multiple tickets to the vector store in batch

        Args:
            tickets: List of ticket dictionaries, each must have 'ticket_number' field
        """
        if not tickets:
            print("No tickets to add")
            return

        documents = []
        metadatas = []
        ids = []

        for ticket in tickets:
            ticket_id = ticket.get("ticket_number", f"ticket_{len(ids)}")
            text_for_embedding = self._create_embedding_text(ticket)

            documents.append(text_for_embedding)
            metadatas.append(ticket)
            ids.append(ticket_id)

        # Add all tickets in batch
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

        print(f"Added {len(tickets)} tickets to vector store")

    def search_similar_tickets(
        self, query_ticket: Dict[str, Any], n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar tickets based on the query ticket

        Args:
            query_ticket: Dictionary containing the new ticket information
            n_results: Number of similar tickets to return

        Returns:
            List of similar tickets with their metadata and similarity scores
        """
        # Create query text
        query_text = self._create_embedding_text(query_ticket)

        # Search for similar tickets
        results = self.collection.query(query_texts=[query_text], n_results=n_results)

        # Format results
        similar_tickets = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                ticket = {
                    "ticket_id": results["ids"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": (
                        results["distances"][0][i] if "distances" in results else None
                    ),
                    "similarity_score": (
                        1 - results["distances"][0][i]
                        if "distances" in results
                        else None
                    ),
                }
                similar_tickets.append(ticket)

        return similar_tickets

    def _create_embedding_text(self, ticket_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive text representation of the ticket for embedding

        Args:
            ticket_data: Dictionary containing ticket information

        Returns:
            Formatted text string for embedding
        """
        # Combine relevant fields for better semantic search
        parts = []

        if "category" in ticket_data:
            parts.append(f"Category: {ticket_data['category']}")

        if "issue" in ticket_data:
            parts.append(f"Issue: {ticket_data['issue']}")

        if "description" in ticket_data:
            parts.append(f"Description: {ticket_data['description']}")

        if "resolution" in ticket_data:
            parts.append(f"Resolution: {ticket_data['resolution']}")

        return " | ".join(parts)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        return {
            "total_tickets": self.collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
        }

    def reset_collection(self):
        """Delete all data from the collection"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, embedding_function=self.embedding_function
        )
        print(f"Collection {self.collection_name} has been reset")


if __name__ == "__main__":
    # Test the vector store
    store = TicketVectorStore()

    # Test ticket
    test_ticket = {
        "ticket_number": "TEST001",
        "category": "Network",
        "issue": "VPN connection issues",
        "description": "Cannot connect to VPN",
        "resolution": "Reset credentials and updated client",
    }

    store.add_ticket("TEST001", test_ticket)
    print(f"\nCollection stats: {store.get_collection_stats()}")
