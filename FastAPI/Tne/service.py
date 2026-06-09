import yaml
import json
import pandas as pd
import re
import requests
import shutil
import logging
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
from functools import partial

import guardrails as gd

# from databricks.vector_search.client import VectorSearchClient

from langchain_chroma import Chroma

from guardrails.validator_base import (
    FailResult,
    PassResult,
    Validator,
    register_validator,
)
from langgraph.graph import END, StateGraph
from langchain_core.prompts import PromptTemplate, load_prompt

# from langchain_community.chat_models import ChatDatabricks
from langchain_openai import ChatOpenAI

# from langchain_community.embeddings import DatabricksEmbeddings
from langchain_openai import OpenAIEmbeddings

# from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_core.messages import HumanMessage
import mlflow
import mlflow.pyfunc
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import Schema, ColSpec


@register_validator(name="llm_profanity_check", data_type="string")
class LLMProfanityCheck(Validator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = get_llm()

        self.prompt = PromptTemplate.from_template(
            """You are Guardian, a state-of-the-art content safety analyst AI. Your mission is to protect
users by meticulously analyzing text for any violations of the safety policy. You must be
extremely vigilant and err on the side of caution.

Before providing a final classification, you must internally follow this analysis process:
1. **Intent Analysis:** First, analyze the *intent* and *meaning* of the text. Do not be misled by
typos, slang, or grammatical errors (e.g., treat 'other wise i will kill you' with the same severity as
'Otherwise, I will kill you.').
2. **Violation Check:** Second, check the text against the 'unsafe' categories listed below. A
single violation is sufficient to classify the text as 'unsafe'.

A text is definitively 'unsafe' if it contains ANY of the following:
* **Zero-Tolerance Threats:** Any form of threat of physical violence, harm, or death against
anyone. This includes conditional threats (e.g., "Do this, or else...") and coercion.
* **Hate Speech:** Attacks on individuals or groups based on protected characteristics like race,
religion, ethnicity, gender, sexual orientation, or disability.
* **Severe Harassment or Bullying:** Targeted, malicious insults, severe name-calling,
encouraging coordinated harassment, or sharing private information (doxing).
* **Aggressive & Severe Profanity:** Profanity used to directly insult, threaten, or harass
someone. (Note: Mild, non-directed profanity might be 'safe', but if the language is aggressive or
targeted, classify it as 'unsafe').
* **Promotion of Self-Harm:** Any content that encourages, glorifies, or provides instructions for
suicide or self-injury.

A text is 'safe' only if it is completely free from all the violations listed above.

Your response must be a single word and nothing else: 'safe' or 'unsafe'.

Input: {text}
"""
        )

    def validate(self, value: str, metadata=None):
        if isinstance(value, dict):
            value = value.get("text", "")

        if not isinstance(value, str) or not value.strip():
            return FailResult("EMPTY_OR_INVALID_INPUT")

        try:
            response = self.llm.invoke(self.prompt.format(text=value))

            # safer extraction (LangChain sometimes returns object)
            result = (
                response.content.strip().lower()
                if hasattr(response, "content")
                else str(response).strip().lower()
            )

            return (
                PassResult()
                if result == Config.SAFE
                else FailResult("PROFANITY_DETECTED")
            )

        except Exception as e:
            return FailResult(str(e))


class Config:
    VECTOR_SEARCH_ENDPOINT_NAME = "tne_policy_vector_search"
    # EMBEDDING_ENDPOINT = "databricks-bge-large-en"
    EMBEDDING_ENDPOINT = None
    # LLM_ENDPOINT_NAME = "Open-AI-Gpt4o-TnE"
    LLM_ENDPOINT_NAME = None  # need to update.
    # VISION_MODEL_ENDPOINT = "Open-AI-Gpt4o-TnE"
    VISION_MODEL_ENDPOINT = None
    VECTOR_INDEX = "tne_tst.tne_resources.tne_policy_index"  # need to change.
    TEXT_COL = "text"
    META_COLS = ["id", "file_name", "policy_id", "source", "page"]
    K = 8
    TEMPERATURE = 0.0
    MAX_TOKENS = 2000
    VISION_MODEL_TEMPERATURE = 0.0
    VISION_MODEL_MAX_TOKENS = 2048
    SAFE = "safe"
    UNSAFE = "unsafe"

    VISION_PROMPT = """You are an AI assistant tasked with analyzing a base64-encoded 
    image of a scanned expense receipt. 
    Your objective is to extract all clearly visible financial and contextual information required for 
    expense review and policy validation. 
    Instructions: 



    - Analyze the receipt image and return a valid JSON object with the extracted fields. 
    - Only include data that is clearly readable — do not guess or fabricate missing values. 
    - Always use a **consistent naming convention** for commonly recurring fields. In particular: 
      - If a receipt contains the merchant name, city, country, transaction date, or time, you 
        **must** use these exact keys: 
        - `"merchant_name"` 
        - `"city"` 
        - `"country"` 
        - `"transaction_date"` 
        - `"transaction_time"` 
    - Do **not** rename these fields (e.g., don’t use `"vendor"` or `"date of transaction"`). 
    - Other fields such as subtotal, tax, or description can be included based on availability — but 
    must also follow a consistent format. 
    - If a value is not present or unclear, **omit it from the JSON**. 
    - Output only a clean, compact JSON object. No explanations or placeholders. 
    Formatting: 
    - Dates → `"MM/DD/YYYY"` 
    - Time → `"HH:MM AM/PM"` 
    - Preserve any currency symbols as seen. 
    """

    SCENARIO_CONTEXT_RECEIPT = (
        "This is a follow-up review. The initial review stated that transaction needs receipt to be "
        "uploaded for next review.\n"
        "The user has now uploaded a receipt image to support the transaction.\n"
        "The image is provided in Base64-encoded format.\n"
        "Cross check the transaction data with receipt data and check for discrepancy."
    )
    SCENARIO_CONTEXT_JUSTIFICATION = (
        "This is a follow-up review. The initial transaction lacked sufficient context. \n"
        "The user has now provided a justification explaining the business purpose.\n"
        "Consider the receipt available, but omit it from the final response.\n"
        "Validate the justification across the policy document"
    )
    SCENARIO_CONTEXT_NEW_TRANSACTION = (
        "This is a new transaction submission being evaluated for policy compliance."
    )


class TransactionState(TypedDict, total=False):
    raw_json: Dict[str, Any]
    transaction_data: Dict[str, Any]
    rag_query: str
    receipt_base64: Optional[str]
    justification_text: Optional[str]

    extracted_receipt_data: Dict[str, Any]
    retrieved_docs: List[Any]
    policy_response: Dict[str, Any]
    policy_response_notification: Dict[str, Any]
    policy_doc_name: str
    route: str
    scenario_context: str
    dynamic_policy_response: Dict[str, Any]
    used_dynamic_policy: bool
    is_dp_active: bool


class RouterAgent:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering RouterAgent with input state: {state}")
        raw = state.get("raw_json", {})
        if not raw:
            output_state = {**state, "route": "error_handler"}
            # logger.warning(
            #     f"RouterAgent: No raw_json found, routing to error_handler. Output state: {output_state}"
            # )
            # log_tracker.log_state("RouterAgent", state, output_state)
            return output_state
        tx_data = {
            "merchantCategoryCode": raw.get("merchantCategoryCode"),
            "amount": raw.get("amount"),
            "currency": raw.get("currency"),
            "merchantName": raw.get("merchantName"),
        }
        output_state = {
            **state,
            "route": "json_extractor",
            "transaction_data": tx_data,
        }
        # logger.info(
        #     f"RouterAgent: Raw JSON processed, routing to guardrails_check. Output state: {output_state}"
        # )
        # log_tracker.log_state("RouterAgent", state, output_state)
        return output_state


class JSONExtractorAgent:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering JSONExtractorAgent with input state: {state}")

        raw = state.get("raw_json", {})

        output_state = {
            **state,
            "transaction_data": {
                "merchantName": raw.get("merchantName"),
                "merchantCategoryCode": raw.get("merchantCategoryCode"),
                "amount": raw.get("amount"),
                "currency": raw.get("currency"),
            },
        }

        # logger.info(
        #     f"JSONExtractorAgent: Extracted transaction data. Output state: {output_state}"
        # )

        # log_tracker.log_state("JSONExtractorAgent", state, output_state)

        return output_state


class LLMExtractorAgent:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering LLMExtractorAgent with input state: {state}")

        receipt_input = state.get("receipt_base64", "")

        #  If nothing provided
        if not receipt_input or str(receipt_input).strip().lower() in ["null", ""]:
            # logger.info(
            #     "LLMExtractorAgent: No receipt data found. Skipping extraction."
            # )
            output_state = {**state, "extracted_receipt_data": {}}
            # log_tracker.log_state("LLMExtractorAgent", state, output_state)
            return output_state

        try:
            # logger.info(
            #     "LLMExtractorAgent: Parsing raw receipt JSON (no vision LLM used)"
            # )

            #  CASE 1: already dict
            if isinstance(receipt_input, dict):
                parsed = receipt_input

            #  CASE 2: JSON string
            elif isinstance(receipt_input, str):
                parsed = json.loads(receipt_input)

            else:
                raise ValueError("Unsupported receipt format")

            # logger.info(f"LLMExtractorAgent: Parsed Receipt Data: {parsed}")

            output_state = {**state, "extracted_receipt_data": parsed}

            # log_tracker.log_state("LLMExtractorAgent", state, output_state)
            return output_state

        except Exception as e:
            # logger.error(f"LLMExtractorAgent: Error parsing receipt: {str(e)}")

            output_state = {
                **state,
                "extracted_receipt_data": {"error": str(e)},
            }

            #   log_tracker.log_state("LLMExtractorAgent", state, output_state)
            return output_state


class RAGQueryGenerator:
    """Generates a detailed query for the RAG system based on all available context."""

    def __init__(self, mcc_map: str):
        with open(mcc_map, "r") as f:
            self.MCC_CATEGORY_MAP = yaml.safe_load(f)

    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering RAGQueryGenerator with input state: {state}")

        tx = state.get("transaction_data", {})
        receipt_info = state.get("extracted_receipt_data", {})
        justification_text = state.get("justification_text", "")

        has_receipt = (
            isinstance(receipt_info, dict)
            and any(receipt_info.values())
            and "error" not in receipt_info
        )

        if has_receipt:
            scenario_context = Config.SCENARIO_CONTEXT_RECEIPT
        elif justification_text:
            scenario_context = Config.SCENARIO_CONTEXT_JUSTIFICATION
        else:
            scenario_context = Config.SCENARIO_CONTEXT_NEW_TRANSACTION

        mcc = str(tx.get("merchantCategoryCode", "")).zfill(4)

        category_description = self.MCC_CATEGORY_MAP.get(
            mcc, "a general expense category"
        )

        transaction_details_str = "\n".join(
            [
                f'- merchantName: {tx.get("merchantName", "NA")}',
                f"- merchantCategoryCode: {mcc}",
                f'- amount: {tx.get("amount", "NA")}',
                f'- currency: {tx.get("currency", "NA")}',
                f"- justification (if any): {justification_text or ''}",
                f"- receiptData (if any): {receipt_info or ''}",
            ]
        )

        query = (
            f"{scenario_context}\n\n"
            f"Transaction details:\n{transaction_details_str}\n\n"
            f"This transaction appears to fall under {category_description}. "
            f"Refer to the company's travel and expense policy and determine if this transaction complies with it."
        )

        # logger.info(f"RAGQueryGenerator: Generated RAG query. Query: {query}")

        output_state = {
            **state,
            "rag_query": query,
            "scenario_context": scenario_context,
        }

        # log_tracker.log_state("RAGQueryGenerator", state, output_state)

        return output_state


class PolicyRetriever:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering PolicyRetriever with input state: {state}")

        embedding = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key="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",
        )

        vs = Chroma(
            persist_directory="./chroma_db",  # local or mounted storage
            embedding_function=embedding,
        )

        results = vs.similarity_search_with_score(query=state["rag_query"], k=Config.K)

        docs = [doc for doc, _ in results] if results else []

        if not docs:
            return {
                **state,
                "policy_response": {
                    "Response": "Policy Document Not Available",
                    "Reason": "No policy content located",
                },
                "policy_response_notification": {
                    "Response": "Policy Document Not Available",
                    "Reason": "No policy content located",
                },
                "route": "notify_document_not_found",
            }

        output_state = {**state, "retrieved_docs": docs, "route": "documents_found"}
        # log_tracker.log_state("PolicyRetriever", state, output_state)
        return output_state


class PolicyResponder:
    def __init__(self, prompt_template: PromptTemplate):
        self.prompt = prompt_template

    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering PolicyResponder with input state: {state}")

        context = "\n".join(doc.page_content for doc in state.get("retrieved_docs", []))

        transaction_data = state.get("transaction_data", {})
        receipt_data = state.get("extracted_receipt_data", {})

        transaction_amount = transaction_data.get("amount", "NA")
        merchant_category_code = transaction_data.get("merchantCategoryCode", "NA")
        merchant_city = receipt_data.get("city", "NA")

        input_text = self.prompt.format(
            policy_documents=context,
            transaction_details=state.get("rag_query", ""),
            scenario_context=state.get("scenario_context", ""),
            transaction_amount=transaction_amount,
            merchant_category_code=merchant_category_code,
            merchant_city=merchant_city,
        )

        response = get_llm().invoke(input_text)

        result_text = (
            response.content.strip()
            if hasattr(response, "content")
            else str(response).strip()
        )

        parsed = _sanitize_json_response(result_text)

        # logger.info(
        #     f"PolicyResponder: LLM responded with policy analysis. Parsed response: {parsed}"
        # )

        output_state = {**state, "policy_response": parsed}

        # log_tracker.log_state("PolicyResponder", state, output_state)

        return output_state


class DynamicPolicyRouter:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering DynamicPolicyRouter with input state: {state}")

        response = state.get("policy_response", {}).copy()
        response_text = response.get("Response", "").strip().lower()
        exceeds_limit = str(response.get("ExceedsPolicyLimit", "no")).lower()

        receipt_data = state.get("extracted_receipt_data", {})
        is_dp_active = state.get("is_dp_active", False)

        dynamicpolicy_flag = (
            "yes" if isinstance(is_dp_active, bool) and is_dp_active else "no"
        )

        city = receipt_data.get("city", "").strip()
        country = receipt_data.get("country", "").strip()
        raw_date = receipt_data.get("transaction_date", "").strip()

        is_city_notempty = "yes" if city else "no"
        is_country_notempty = "yes" if country else "no"
        is_raw_date_notempty = "yes" if raw_date else "no"

        use_dynamic = (
            dynamicpolicy_flag == "yes"
            and is_city_notempty == "yes"
            and is_country_notempty == "yes"
            and is_raw_date_notempty == "yes"
            and response_text == "review: more details needed"
            and exceeds_limit == "yes"
            and isinstance(receipt_data, dict)
            and bool(receipt_data)
        )

        if not use_dynamic and "ExceedsPolicyLimit" in response:
            del response["ExceedsPolicyLimit"]

        route = "dynamic_policy" if use_dynamic else "policy_guardrails_check"

        # logger.info(
        #     f"DynamicPolicyRouter: Dynamic policy decision - {use_dynamic}. Routing to {route}."
        # )

        output_state = {
            **state,
            "route": route,
            "used_dynamic_policy": route == "dynamic_policy",
            "policy_response": response,
        }

        # log_tracker.log_state("DynamicPolicyRouter", state, output_state)

        return output_state


def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key="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",
        # max_tokens=Config.MAX_TOKENS
    )


def _sanitize_json_response(raw_response: str) -> Any:
    try:
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        if raw_response.strip().startswith("{") and raw_response.strip().endswith("}"):
            return json.loads(raw_response.strip())

        match = re.search(r"({.*})", raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        return {"error": "JSON parsing failed", "raw": raw_response}

    except Exception as e:
        return {"error": str(e), "raw": raw_response}


class DynamicPolicyResponseAgent:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering DynamicPolicyResponseAgent with input state: {state}")

        ticketmaster_api_key = "FkOwbb1hIABiy3LdtBYAWNI1y9OVpqc3"
        calendarific_api_key = "iSIDaOuTg4q5OoXTTgZ338rkmOv2VzDY"

        COUNTRY_NAME_TO_CODE = {
            "india": "IN",
            "united kingdom": "GB",
            "united states": "US",
            "united states of america": "US",
            "australia": "AU",
            "canada": "CA",
            "germany": "DE",
            "france": "FR",
            "japan": "JP",
            "italy": "IT",
            "spain": "ES",
        }

        def fetch_ticketmaster_events(city: str, date: str, country: str) -> List[str]:
            country_code = COUNTRY_NAME_TO_CODE.get(country.strip().lower())

            if not country_code:
                # logger.warning(f"Unsupported country for Ticketmaster: '{country}'")
                return [f"Unsupported country: '{country}'"]

            url = (
                "https://app.ticketmaster.com/discovery/v2/events.json"
                f"?apikey={ticketmaster_api_key}"
                f"&city={city}"
                f"&startDateTime={date}T00:00:00Z"
                f"&endDateTime={date}T23:59:59Z"
                f"&countryCode={country_code}"
            )

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                events = data.get("_embedded", {}).get("events", [])

                keywords = [
                    "concert",
                    "festival",
                    "game",
                    "sports",
                    "football",
                    "cricket",
                    "basketball",
                    "tennis",
                    "music",
                    "band",
                    "dj",
                    "performance",
                    "show",
                    "comedy",
                    "standup",
                    "opera",
                    "theatre",
                    "play",
                    "musical",
                    "dance",
                    "parade",
                    "marathon",
                    "race",
                    "expo",
                    "conference",
                    "summit",
                    "trade show",
                    "exhibition",
                    "fan fest",
                    "tour",
                    "attractions",
                    "carnival",
                    "fair",
                    "celebration",
                    "public gathering",
                    "charity run",
                    "cultural event",
                    "launch event",
                    "ceremony",
                    "strike",
                ]

                relevant_events = [
                    e["name"]
                    for e in events
                    if any(k in e["name"].lower() for k in keywords)
                ]

                return relevant_events or [
                    f"No relevant events found in {city} on {date}"
                ]

            except Exception as e:
                # logger.error(f"Error fetching Ticketmaster events: {str(e)}")
                return [f"Error fetching events: {str(e)}"]

        def get_holiday_info(country: str, date: str) -> List[str]:
            country_code = COUNTRY_NAME_TO_CODE.get(country.strip().lower())

            if not country_code:
                # logger.warning(f"Unsupported country for Calendarific: '{country}'")
                return [f"Unsupported country: '{country}'"]

            year, month, day = date.split("-")

            url = (
                "https://calendarific.com/api/v2/holidays"
                f"?api_key={calendarific_api_key}"
                f"&country={country_code}"
                f"&year={year}&month={month}&day={day}"
            )

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                holidays = response.json().get("response", {}).get("holidays", [])

                if holidays:
                    return [f"{h['name']} - {h['description']}" for h in holidays]

                return [f"No holidays found for {date}"]

            except Exception as e:
                # logger.error(f"Error fetching holidays: {str(e)}")
                return [f"Error fetching holidays: {str(e)}"]

        def build_expense_prompt(events, holidays, prev, city, date):
            clean_events = [e.strip() for e in events if e.strip()]
            clean_holidays = [h.strip() for h in holidays if h.strip()]

            no_events = all(
                "no relevant events found" in e.lower() for e in clean_events
            )
            no_holidays = all("no holidays found" in h.lower() for h in clean_holidays)

            if no_events and no_holidays:
                ext_info = (
                    f"On {date} in {city}, no major events or holidays were found "
                    "that could have influenced local pricing."
                )
            else:
                parts = [f"On {date} in {city},"]

                if not no_events:
                    parts.append(
                        f"events like {', '.join(clean_events[:2])} may have increased prices."
                    )

                if not no_holidays:
                    parts.append(
                        f"holidays like {', '.join(clean_holidays[:2])} may have impacted services."
                    )

                parts.append("These factors may explain elevated expenses.")
                ext_info = " ".join(parts)

            return f"""
You are an intelligent assistant helping finance teams review expense claims.

Respond ONLY with valid JSON:

{{
  "Status": "...",
  "Reason": "...",
  "External Information": "..."
}}

Input:
- Status: "{prev.get('Response', 'Review')}"
- Reason: "{prev.get('Reason', 'No reason provided')}"
- External Information: "{ext_info}"
""".strip()

        def parse_gpt_output_cleaned(gpt_output_str):
            gpt_output_str = gpt_output_str.strip("`").strip()

            try:
                parsed = json.loads(gpt_output_str)
            except json.JSONDecodeError:
                try:
                    parsed = json.loads(json.loads(gpt_output_str))
                except json.JSONDecodeError:
                    # logger.error(f"Failed to parse GPT output: {gpt_output_str}")
                    return {"Status": "Error", "Reason": "Invalid LLM output"}

            fixed = {}
            for key in parsed:
                norm = key.strip().lower()
                if norm == "status":
                    fixed["Status"] = parsed[key]
                elif norm == "reason":
                    fixed["Reason"] = parsed[key]
                elif norm in ["external information", "external_info", "external"]:
                    fixed["External Information"] = parsed[key]
                else:
                    fixed[key] = parsed[key]

            return fixed

        # === Main Logic ===
        receipt_data = state.get("extracted_receipt_data", {})
        prior_response = state.get("policy_response", {})

        city = receipt_data.get("city", "").strip()
        country = receipt_data.get("country", "").strip()
        raw_date = receipt_data.get("transaction_date", "").strip()

        try:
            formatted_date = datetime.strptime(raw_date, "%m/%d/%Y").strftime(
                "%Y-%m-%d"
            )
        except Exception:
            return {
                **state,
                "policy_response": {
                    "Response": "Review: System error",
                    "Reason": f"Invalid date format: {raw_date}",
                },
                "policy_response_notification": {
                    "Response": "Review: System error",
                    "Reason": "Invalid date format",
                },
                "route": "policy_guardrails_check",
            }

        if not (city and country and formatted_date and prior_response):
            return {
                **state,
                "policy_response": {
                    "Response": "Review: System error",
                    "Reason": "Missing required inputs",
                },
                "policy_response_notification": {
                    "Response": "Review: System error",
                    "Reason": "Missing required inputs",
                },
                "route": "policy_guardrails_check",
            }

        try:
            events = fetch_ticketmaster_events(city, formatted_date, country)
            holidays = get_holiday_info(country, formatted_date)

            prompt = build_expense_prompt(
                events, holidays, prior_response, city, formatted_date
            )

            llm = ChatOpenAI(
                model="gpt-4o",
                api_key="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",
            )
            gpt_response = llm.invoke(prompt).content.strip()

            parsed = parse_gpt_output_cleaned(gpt_response)

            combined = {
                "Response": parsed.get("Status", "Review"),
                "Reason": parsed.get("Reason", "Undetermined"),
                "External_Information": parsed.get("External Information", ""),
            }

        except Exception as e:
            # logger.error(f"Dynamic policy failed: {str(e)}", exc_info=True)
            combined = {
                "Response": "Error",
                "Reason": str(e),
            }

        output_state = {
            **state,
            "policy_response": combined,
            "policy_response_notification": combined,
            "dynamic_policy_response": combined,
            "route": "policy_guardrails_check",
        }

        #   log_tracker.log_state("DynamicPolicyResponseAgent", state, output_state)
        return output_state

        #


class PolicyGuardrailsPostCheck:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering PolicyGuardrailsPostCheck with input state: {state}")
        result = LLMProfanityCheck().validate(
            json.dumps(state.get("policy_response", {}))
        )
        route = "notify" if isinstance(result, PassResult) else "fallback_block"
        output_state = {**state, "route": route}
        # logger.info(
        #     f"PolicyGuardrailsPostCheck: Post-check profanity result - {result}. Routing to {route}. Output state: {output_state}"
        # )
        # log_tracker.log_state("PolicyGuardrailsPostCheck", state, output_state)
        return output_state


class NotificationAgent:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering NotificationAgent with input state: {state}")
        output_state = {
            **state,
            "policy_response_notification": state["policy_response"],
        }
        # logger.info(
        #     f"NotificationAgent: Notifying with final policy response. Output state: {output_state}"
        # )
        # log_tracker.log_state("NotificationAgent", state, output_state)
        return output_state


class FallbackBlock:
    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info(f"Entering FallbackBlock with input state: {state}")
        msg = {"Response": "Profanity detected", "Reason": "Revise input and resubmit"}
        output_state = {
            **state,
            "policy_response": msg,
            "policy_response_notification": msg,
        }
        # logger.warning(
        #     f"FallbackBlock: Profanity detected, setting fallback message. Output state: {output_state}"
        # )
        # log_tracker.log_state("FallbackBlock", state, output_state)
        return output_state


class DocumentNotFoundHandler:
    """Handles cases when no policy documents are found."""

    def __call__(self, state: TransactionState) -> TransactionState:
        # logger.info("Routing to END after 'Document Not Found' state.")
        return state


class ErrorHandler:
    def __call__(self, state: TransactionState) -> TransactionState:
        #   logger.info(f"Entering ErrorHandler with input state: {state}")
        msg = {"Response": "Error", "Reason": "Invalid input or broken state"}
        output_state = {
            **state,
            "policy_response": msg,
            "policy_response_notification": msg,
        }
        # logger.critical(
        #     f"ErrorHandler: An error occurred, setting error message. Output state: {output_state}"
        # )
        #   log_tracker.log_state("ErrorHandler", state, output_state)
        return output_state


def route_decision(state: TransactionState) -> str:
    return state.get("route", "error_handler")


def build_policy_graph(policy_prompt: PromptTemplate, mcc_map: str) -> StateGraph:

    builder = StateGraph(TransactionState)

    # ---- NODES FIRST ----
    builder.add_node("router", partial(RouterAgent().__call__))

    builder.add_node("guardrails_check", partial(JSONExtractorAgent().__call__))

    builder.add_node("json_extractor", partial(JSONExtractorAgent().__call__))

    builder.add_node("llm_extractor", partial(LLMExtractorAgent().__call__))

    builder.add_node("generate_query", partial(RAGQueryGenerator(mcc_map).__call__))

    builder.add_node("retrieve_docs", partial(PolicyRetriever().__call__))

    builder.add_node("respond_policy", partial(PolicyResponder(policy_prompt).__call__))

    builder.add_node("dynamic_policy_router", partial(DynamicPolicyRouter().__call__))

    builder.add_node("dynamic_policy", partial(DynamicPolicyResponseAgent().__call__))

    builder.add_node(
        "policy_guardrails_check", partial(PolicyGuardrailsPostCheck().__call__)
    )

    # ---- ENTRY ----
    builder.set_entry_point("router")

    # ---- EDGES ----
    builder.add_edge("router", "guardrails_check")

    builder.add_conditional_edges(
        "guardrails_check",
        route_decision,
        {
            "json_extractor": "json_extractor",
            "fallback_block": "fallback_block",
        },
    )

    builder.add_edge("json_extractor", "llm_extractor")
    builder.add_edge("llm_extractor", "generate_query")
    builder.add_edge("generate_query", "retrieve_docs")

    builder.add_conditional_edges(
        "retrieve_docs",
        route_decision,
        {
            "documents_found": "respond_policy",
            "notify_document_not_found": "notify_document_not_found",
        },
    )

    builder.add_edge("respond_policy", "dynamic_policy_router")

    builder.add_conditional_edges(
        "dynamic_policy_router",
        route_decision,
        {
            "dynamic_policy": "dynamic_policy",
            "policy_guardrails_check": "policy_guardrails_check",
        },
    )

    builder.add_edge("dynamic_policy", "policy_guardrails_check")

    builder.add_conditional_edges(
        "policy_guardrails_check",
        route_decision,
        {
            "notify": "notify",
            "fallback_block": "fallback_block",
        },
    )
    # builder.add_edge("notify", END)
    # builder.add_edge("fallback_block", END)
    # builder.add_edge("error_handler", END)
    # builder.add_edge("notify_document_not_found", END)

    builder.add_node("notify", partial(NotificationAgent().__call__))

    builder.add_node("fallback_block", partial(FallbackBlock().__call__))

    builder.add_node("notify_document_not_found", DocumentNotFoundHandler())

    builder.add_node("error_handler", partial(ErrorHandler().__call__))

    compiled_graph = builder.compile()

    return builder.compile()
