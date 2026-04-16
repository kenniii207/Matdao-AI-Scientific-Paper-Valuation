"""Evaluation service for scientific paper analysis using LLMs."""

import logging
import json
import time
from collections import deque
import httpx
from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.core.json_utils import coerce_jsonable
from backend.models.scoring import DIMENSION_NAMES

logger = logging.getLogger(__name__)
_RECENT_INSIGHTS: deque[str] = deque(maxlen=50)
_GENERIC_PHRASES = {
    "strong scientific rigor",
    "limited commercialization signals",
    "early-stage deep tech investors",
    "corporate r&d collaboration",
    "no go-to-market strategy",
    "no industry validation",
}


def _normalize_generic_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _detect_generic_output(result: Dict[str, Any]) -> Dict[str, Any]:
    insight = str(result.get("insight") or result.get("executive_summary") or "").strip()
    warnings = result.get("warnings") or []
    warning_text = " ".join(str(item) for item in warnings) if isinstance(warnings, list) else str(warnings)
    combined = f"{insight} {warning_text}".strip()
    normalized = _normalize_generic_text(combined)
    reasons: list[str] = []

    if not normalized:
        reasons.append("missing_insight")
    elif len(normalized) < 40:
        reasons.append("insight_too_short")

    if any(phrase in normalized for phrase in _GENERIC_PHRASES):
        reasons.append("contains_generic_phrase")

    repeat_count = 0
    if normalized:
        repeat_count = sum(1 for previous in _RECENT_INSIGHTS if previous == normalized)
        _RECENT_INSIGHTS.append(normalized)
    if repeat_count >= 2:
        reasons.append("recent_repeat_pattern")

    return {
        "generic_output_detected": bool(reasons),
        "generic_output_reasons": reasons,
        "recent_repeat_count": repeat_count,
    }

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
        document_profile = metadata.get("document_profile", {}) if isinstance(metadata, dict) else {}
        abstract = str(document_profile.get("abstract") or "").strip()
        keywords = document_profile.get("keywords") or []
        if isinstance(keywords, list):
            keyword_text = ", ".join(str(k) for k in keywords[:8])
        else:
            keyword_text = ""
        llm_text = (text_content or "")[: max(2000, settings.evaluation_text_max_chars)]
        
        prompt = f"""
        You are the Head of Scientific Due Diligence at MatDAO.
        Your task is to evaluate a scientific paper for investment and research support.
        
        ### DATA SOURCES
        1. Parsed Paper Profile:
        - Abstract: {abstract}
        - Keywords: {keyword_text}

        2. Extracted Paper Text (truncated for speed):
        {llm_text}
        
        3. API Metadata (OpenAlex, Semantic Scholar, Google Scholar theme matches):
        {metadata_str}

        ### ANALYSIS RULES
        - Use document_profile + similar_papers_curated (if present) to infer closest research theme before scoring.
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
        llm_start = time.perf_counter()
        llm_provider = "gemini" if settings.gemini_api_key else "glm"

        if settings.gemini_api_key:
            eval_result = await self._evaluate_with_gemini(prompt)
            llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
            return self._attach_quality_signals(eval_result, llm_provider, llm_ms)

        if not self.api_key:
            logger.error("No Gemini (GEMINI_API_KEY) or Zhipu/GLM (ZAI_API_KEY) key configured for evaluation.")
            llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
            return self._attach_quality_signals({}, llm_provider, llm_ms)

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
                eval_result = json.loads(content)
                llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
                return self._attach_quality_signals(eval_result, llm_provider, llm_ms)
            except Exception as e:
                logger.error(f"LLM Evaluation failed: {e}")
                llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
                return self._attach_quality_signals({"error": str(e)}, llm_provider, llm_ms)

    def _attach_quality_signals(
        self,
        eval_result: Dict[str, Any],
        provider: str,
        llm_stage_ms: float,
    ) -> Dict[str, Any]:
        result = eval_result if isinstance(eval_result, dict) else {}
        stage_timings = result.get("stage_timings_ms")
        if not isinstance(stage_timings, dict):
            stage_timings = {}
        stage_timings["llm_stage_ms"] = llm_stage_ms
        result["stage_timings_ms"] = stage_timings

        quality_signals = result.get("_quality_signals")
        if not isinstance(quality_signals, dict):
            quality_signals = {}
        quality_signals["llm_provider"] = provider
        quality_signals.update(_detect_generic_output(result))
        result["_quality_signals"] = quality_signals
        return result
