"""Evaluation service for scientific paper analysis using LLMs."""

import logging
import json
import httpx
from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.core.json_utils import coerce_jsonable
from backend.models.scoring import DIMENSION_NAMES

logger = logging.getLogger(__name__)

class ScientificEvaluator:
    """Orchestrates scientific due diligence using LLM synthesis."""

    def __init__(self):
        self.api_key = settings.zai_api_key
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    async def _evaluate_with_gemini(self, prompt: str) -> Dict[str, Any]:
        api_key = settings.gemini_api_key
        if not api_key:
            return {}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                if not text:
                    return {"error": "Gemini returned empty content", "raw": data}
                return json.loads(text)
            except Exception as exc:
                logger.error(f"Gemini evaluation failed: {exc}")
                return {"error": str(exc)}

    async def evaluate_content(
        self, 
        text_content: str, 
        enriched_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send paper text and API metadata to LLM for 9-dimension scoring.
        
        Args:
            text_content: Extracted text from PDF.
            enriched_data: Metadata from OpenAlex, Semantic Scholar, etc.
        """
        metadata = coerce_jsonable(enriched_data or {})
        metadata_str = json.dumps(metadata, indent=2)
        
        prompt = f"""
        You are the Head of Scientific Due Diligence at MatDAO.
        Your task is to evaluate a scientific paper for investment and research support.
        
        ### DATA SOURCES
        1. Extracted Paper Text:
        {text_content[:20000]}
        
        2. API Metadata (OpenAlex, Semantic Scholar, Google Scholar theme matches):
        {metadata_str}

        ### ANALYSIS RULES
        - Use document_profile + similar_papers to infer closest research theme before scoring.
        - If metadata has conflicting signals, explain conflict in rationale.
        - Do not output generic statements. Tie conclusions to concrete snippets and metadata evidence.

        ### EVALUATION CRITERIA (9 Dimensions)
        1. Novelty (0.0-5.0): Originality of the concept/discovery.
        2. Rigor (0.0-5.0): Methodological soundness, statistical power.
        3. Reproducibility (0.0-5.0): Clarity of protocols, data availability.
        4. Impact (0.0-5.0): Potential to shift paradigms or solve large problems.
        5. Feasibility (0.0-5.0): Practicality of implementation/translation.
        6. Team (0.0-5.0): Expertise and track record (if authors visible).
        7. Market (0.0-5.0): Commercial potential or DAO integration value.
        8. Ethics (0.0-5.0): Safety concerns, bioethics, data privacy.
        9. Governance (0.0-5.0): Integrity gate. SCORE 1.0 IF FRAUD IS SUSPECTED.

        ### RESPONSE REQUIREMENTS
        - Return a strictly structured JSON object.
        - For each dimension, provide a score (float), a brief rationale, and a 'origin_snippet' from the text that justifies the score.
        - The 'origin_snippet' is critical for auditability.

        JSON FORMAT:
        {{
            "scores": {{
                "1": {{"score": 4.5, "rationale": "...", "origin_snippet": "..."}},
                ...
                "9": {{"score": 5.0, "rationale": "...", "origin_snippet": "..."}}
            }},
            "executive_summary": "...",
            "investment_recommendation": "Tier A/B/C/Reject",
            "insight": "One concise insight sentence tailored to this paper",
            "investor_fit": ["Fit 1", "Fit 2"],
            "warnings": ["Warning 1", "Warning 2"]
        }}
        """

        if settings.gemini_api_key:
            return await self._evaluate_with_gemini(prompt)

        if not self.api_key:
            logger.error("No Gemini (GEMINI_API_KEY) or Zhipu/GLM (ZAI_API_KEY) key configured for evaluation.")
            return {}

        async with httpx.AsyncClient(timeout=90.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "glm-4",
                "messages": [
                    {"role": "system", "content": "You are a highly critical scientific analyst."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            
            try:
                resp = await client.post(self.api_url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                logger.error(f"LLM Evaluation failed: {e}")
                return {"error": str(e)}
