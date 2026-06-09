from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime
import uuid

from Tne.model import (
    TransactionRequest,
    TransactionResponse,
    PolicyResponse,
    HealthResponse,
    ErrorResponse,
)
from .service import build_policy_graph, TransactionState
from langchain_core.prompts import PromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["transactions"])


# Initialize the policy graph (you'll need to provide the actual prompt template and mcc_map path)
def get_policy_graph():
    """Initialize and return the policy graph"""
    try:
        # Define the policy prompt template
        policy_prompt = PromptTemplate.from_template("""
You are an AI assistant analyzing expense transactions against company policy.

Policy Documents:
{policy_documents}

Transaction Details:
{transaction_details}

Scenario Context:
{scenario_context}

Transaction Amount: {transaction_amount}
Merchant Category Code: {merchant_category_code}
Merchant City: {merchant_city}

Analyze the transaction and provide a response in the following JSON format:
{{
    "Response": "Approved/Rejected/Review: More details needed",
    "Reason": "Detailed explanation of the decision",
    "ExceedsPolicyLimit": "yes/no"
}}

Be thorough and consider all policy requirements.
""")

        # Path to MCC mapping file (adjust as needed)
        mcc_map_path = "mcc_mapping.yaml"

        return build_policy_graph(policy_prompt, mcc_map_path)
    except Exception as e:
        logger.error(f"Error initializing policy graph: {str(e)}")
        raise


@router.post(
    "/validate-transaction",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def validate_transaction(transaction: TransactionRequest) -> TransactionResponse:
    """
    Validate a transaction against company policy.

    This endpoint processes expense transactions and validates them against
    company policies using RAG (Retrieval-Augmented Generation) and LLM analysis.

    Args:
        transaction: Transaction details including merchant info, amount, and optional receipt/justification

    Returns:
        TransactionResponse with policy decision and reasoning

    Raises:
        HTTPException: If validation fails or an error occurs
    """
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    try:
        logger.info(
            f"Processing transaction {transaction_id}: {transaction.merchantName}"
        )

        # Prepare the initial state for the policy graph
        initial_state: TransactionState = {
            "raw_json": {
                "merchantName": transaction.merchantName,
                "merchantCategoryCode": transaction.merchantCategoryCode,
                "amount": transaction.amount,
                "currency": transaction.currency,
            },
            "receipt_base64": transaction.receipt_base64,
            "justification_text": transaction.justification_text,
            "is_dp_active": transaction.is_dp_active or False,
        }

        # Get the policy graph
        graph = get_policy_graph()

        # Execute the graph
        logger.info(f"Executing policy graph for transaction {transaction_id}")
        result = graph.invoke(initial_state)

        # Extract the policy response
        policy_response_data = result.get("policy_response_notification") or result.get(
            "policy_response", {}
        )

        if not policy_response_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No policy response generated",
            )

        # Create the response
        policy_response = PolicyResponse(**policy_response_data)

        response = TransactionResponse(
            transaction_id=transaction_id,
            policy_response=policy_response,
            used_dynamic_policy=result.get("used_dynamic_policy", False),
            timestamp=datetime.utcnow(),
        )

        logger.info(
            f"Transaction {transaction_id} processed successfully: {policy_response.Response}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing transaction {transaction_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing transaction: {str(e)}",
        )


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify the service is running.

    Returns:
        HealthResponse with service status and version
    """
    return HealthResponse(
        status="healthy", timestamp=datetime.utcnow(), version="1.0.0"
    )


@router.get(
    "/transaction/{transaction_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse, "description": "Transaction not found"}},
)
async def get_transaction(transaction_id: str) -> Dict[str, Any]:
    """
    Retrieve transaction details by ID.

    Note: This is a placeholder endpoint. In a production system,
    you would retrieve this from a database.

    Args:
        transaction_id: Unique transaction identifier

    Returns:
        Transaction details

    Raises:
        HTTPException: If transaction is not found
    """
    # Placeholder - implement actual database lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction retrieval not yet implemented. This requires database integration.",
    )


@router.post(
    "/batch-validate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def batch_validate_transactions(
    transactions: list[TransactionRequest],
) -> Dict[str, Any]:
    """
    Validate multiple transactions in batch.

    Args:
        transactions: List of transactions to validate

    Returns:
        Dictionary with results for each transaction

    Raises:
        HTTPException: If batch validation fails
    """
    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No transactions provided"
        )

    if len(transactions) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 transactions allowed per batch",
        )

    results = []
    errors = []

    for idx, transaction in enumerate(transactions):
        try:
            result = await validate_transaction(transaction)
            results.append(
                {
                    "index": idx,
                    "transaction_id": result.transaction_id,
                    "status": "success",
                    "response": result.dict(),
                }
            )
        except Exception as e:
            errors.append({"index": idx, "status": "error", "error": str(e)})

    return {
        "total": len(transactions),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
