from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import json

from Tne.model import TransactionRequest, TransactionResponse

# import your service layer
from Tne.service import build_policy_graph, TransactionState
from langchain_core.prompts import PromptTemplate

app = FastAPI(title="TnE Policy Engine API")


# ---------- INIT GRAPH ----------
def load_graph():
    policy_prompt = PromptTemplate.from_template("""
You are a policy evaluation engine.

Policy:
{policy_documents}

Transaction:
{transaction_details}

Scenario:
{scenario_context}

Return JSON:
{
 "Response": "...",
 "Reason": "...",
 "ExceedsPolicyLimit": "yes/no"
}
""")

    graph = build_policy_graph(policy_prompt=policy_prompt, mcc_map="mcc_map.yaml")

    return graph


graph = load_graph()


# ---------- NORMAL API ----------
@app.post("/evaluate", response_model=TransactionResponse)
def evaluate_transaction(request: TransactionRequest):

    try:
        state: TransactionState = {
            "raw_json": request.raw_json,
            "receipt_base64": request.receipt_base64,
            "justification_text": request.justification_text,
            "is_dp_active": request.is_dp_active,
        }

        result = graph.invoke(state)

        return TransactionResponse(
            policy_response=result.get("policy_response", {}),
            policy_response_notification=result.get("policy_response_notification", {}),
            used_dynamic_policy=result.get("used_dynamic_policy", False),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- STREAMING API ----------
@app.post("/evaluate/stream")
def evaluate_transaction_stream(request: TransactionRequest):

    def event_stream():
        try:
            state: TransactionState = {
                "raw_json": request.raw_json,
                "receipt_base64": request.receipt_base64,
                "justification_text": request.justification_text,
                "is_dp_active": request.is_dp_active,
            }

            # Stream graph execution
            for step in graph.stream(state):

                # each step is partial state
                yield f"data: {json.dumps(step, default=str)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------- HEALTH CHECK ----------
@app.get("/health")
def health():
    return {"status": "ok"}


# from fastapi import FastAPI, Request, status
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from fastapi.exceptions import RequestValidationError
# from contextlib import asynccontextmanager
# import logging
# import time
# from datetime import datetime

# from Tne.controller import router as transaction_router
# from Tne.model import ErrorResponse

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Lifespan context manager for startup and shutdown events"""
#     # Startup
#     logger.info("Starting FastAPI application...")
#     logger.info("Initializing policy graph and dependencies...")
#     yield
#     # Shutdown
#     logger.info("Shutting down FastAPI application...")


# # Initialize FastAPI app with metadata
# app = FastAPI(
#     title="Travel & Expense Policy Validator API",
#     description="""
#     API for validating travel and expense transactions against company policies.

#     """,
#     version="1.0.0",
#     lifespan=lifespan,
#     docs_url="/docs",
#     redoc_url="/redoc",
#     openapi_url="/openapi.json"
# )

# # CORS Middleware - Configure based on your needs
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, specify actual origins
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Trusted Host Middleware (optional, for production)
# # app.add_middleware(
# #     TrustedHostMiddleware,
# #     allowed_hosts=["example.com", "*.example.com"]
# # )


# # Request timing middleware
# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     """Add processing time to response headers"""
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(process_time)
#     return response


# # Global exception handlers
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     """Handle validation errors"""
#     logger.error(f"Validation error: {exc.errors()}")
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content=ErrorResponse(
#             error="ValidationError",
#             message="Invalid request data",
#             detail={"errors": exc.errors()},
#             timestamp=datetime.utcnow()
#         ).dict()
#     )


# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     """Handle all unhandled exceptions"""
#     logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content=ErrorResponse(
#             error="InternalServerError",
#             message="An unexpected error occurred",
#             detail={"error": str(exc)},
#             timestamp=datetime.utcnow()
#         ).dict()
#     )


# # Include routers
# app.include_router(transaction_router)


# # Root endpoint
# @app.get("/", tags=["root"])
# async def read_root():
#     """Root endpoint with API information"""
#     return {
#         "message": "Travel & Expense Policy Validator API",
#         "version": "1.0.0",
#         "docs": "/docs",
#         "health": "/api/v1/health",
#         "timestamp": datetime.utcnow().isoformat()
#     }


# # Legacy endpoints (keeping for backward compatibility)
# @app.get("/items/{item_id}", tags=["legacy"])
# def read_item(item_id: int, q: str | None = None):
#     """Legacy endpoint - kept for backward compatibility"""
#     logger.warning("Legacy endpoint /items/{item_id} called")
#     return {
#         "item_id": item_id,
#         "q": q,
#         "note": "This is a legacy endpoint. Please use /api/v1/* endpoints."
#     }


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )
