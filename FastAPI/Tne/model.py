from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class TransactionRequest(BaseModel):
    raw_json: Dict[str, Any] = Field(..., description="Transaction input JSON")

    receipt_base64: Optional[Any] = Field(
        None, description="Can be dict OR JSON string of receipt"
    )

    justification_text: Optional[str] = None

    # optional dynamic policy flag
    is_dp_active: Optional[bool] = False


class TransactionResponse(BaseModel):
    policy_response: Dict[str, Any]
    policy_response_notification: Dict[str, Any]
    used_dynamic_policy: Optional[bool] = False


# from pydantic import BaseModel, Field, validator
# from typing import Optional, Dict, Any, List
# from datetime import datetime


# class TransactionRequest(BaseModel):
#     """Request model for transaction validation"""

#     merchantName: str = Field(..., description="Name of the merchant")
#     merchantCategoryCode: str = Field(..., description="MCC code for the merchant")
#     amount: float = Field(..., gt=0, description="Transaction amount")
#     currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
#     receipt_base64: Optional[str] = Field(
#         None, description="Base64 encoded receipt image or JSON receipt data"
#     )
#     justification_text: Optional[str] = Field(
#         None, description="Justification for the expense"
#     )
#     is_dp_active: Optional[bool] = Field(
#         False, description="Whether dynamic policy is active"
#     )

#     @validator("merchantCategoryCode")
#     def validate_mcc(cls, v):
#         if not v.isdigit() or len(v) > 4:
#             raise ValueError("MCC must be a numeric string with max 4 digits")
#         return v.zfill(4)

#     @validator("currency")
#     def validate_currency(cls, v):
#         if len(v) != 3:
#             raise ValueError("Currency must be a 3-letter code")
#         return v.upper()

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "merchantName": "Starbucks",
#                 "merchantCategoryCode": "5814",
#                 "amount": 25.50,
#                 "currency": "USD",
#                 "receipt_base64": None,
#                 "justification_text": "Client meeting coffee",
#                 "is_dp_active": False,
#             }
#         }


# class PolicyResponse(BaseModel):
#     """Response model for policy validation"""

#     Response: str = Field(..., description="Policy decision status")
#     Reason: str = Field(..., description="Reason for the decision")
#     External_Information: Optional[str] = Field(
#         None, description="Additional context from external sources"
#     )
#     ExceedsPolicyLimit: Optional[str] = Field(
#         None, description="Whether transaction exceeds policy limits"
#     )

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "Response": "Approved",
#                 "Reason": "Transaction complies with company policy",
#                 "External_Information": None,
#             }
#         }


# class TransactionResponse(BaseModel):
#     """Complete response for transaction validation"""

#     transaction_id: Optional[str] = Field(
#         None, description="Unique transaction identifier"
#     )
#     policy_response: PolicyResponse
#     used_dynamic_policy: bool = Field(
#         False, description="Whether dynamic policy was applied"
#     )
#     timestamp: datetime = Field(default_factory=datetime.utcnow)

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "transaction_id": "txn_123456",
#                 "policy_response": {
#                     "Response": "Approved",
#                     "Reason": "Transaction complies with company policy",
#                 },
#                 "used_dynamic_policy": False,
#                 "timestamp": "2026-05-05T06:37:00Z",
#             }
#         }


# class HealthResponse(BaseModel):
#     """Health check response"""

#     status: str = Field(..., description="Service status")
#     timestamp: datetime = Field(default_factory=datetime.utcnow)
#     version: str = Field("1.0.0", description="API version")

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "status": "healthy",
#                 "timestamp": "2026-05-05T06:37:00Z",
#                 "version": "1.0.0",
#             }
#         }


# class ErrorResponse(BaseModel):
#     """Error response model"""

#     error: str = Field(..., description="Error type")
#     message: str = Field(..., description="Error message")
#     detail: Optional[Dict[str, Any]] = Field(
#         None, description="Additional error details"
#     )
#     timestamp: datetime = Field(default_factory=datetime.utcnow)

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "error": "ValidationError",
#                 "message": "Invalid transaction data",
#                 "detail": {"field": "amount", "issue": "must be greater than 0"},
#                 "timestamp": "2026-05-05T06:37:00Z",
#             }
#         }
