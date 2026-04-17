"""Evaluation service for scientific paper analysis using LLMs."""

import asyncio
import logging
import json
import time
from collections import deque
import httpx
from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.core.json_utils import coerce_jsonable

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
_DEFAULT_SCORE = 3.0
_MISSING_RATIONALE = (
    "Structured rationale was missing from model output; neutral score retained for audit consistency."
)
_MISSING_SNIPPET = (
    "No attributable origin snippet extracted from the parsed paper text; manual validation recommended."
)
_DEFAULT_INVESTOR_FIT = [
    "Early-stage deep tech investors",
    "Corporate R&D collaboration",
]
_DEFAULT_WARNINGS = [
    "Insufficient risk detail from current extraction",
    "Validate external market signals with manual Layer 3 review",
]
_INSUFFICIENT_EVIDENCE_SUMMARY = (
    "Evidence quality is insufficient for high-confidence investment inference; "
    "scores are preserved as provisional pending manual diligence."
)
_INSUFFICIENT_EVIDENCE_INSIGHT = (
    "The current extraction/enrichment evidence is too thin or inconsistent to support a decisive thesis."
)
_INSUFFICIENT_EVIDENCE_RECOMMENDATION = "Hold - Insufficient Evidence (Manual Review Required)"
_INSUFFICIENT_EVIDENCE_WARNINGS = [
    "Automated output was downgraded due to limited or inconsistent evidence coverage.",
    "Route this paper to manual analyst review before acting on recommendation.",
]


def _normalize_generic_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def _detect_generic_output(
    result: Dict[str, Any],
    record_history: bool = True,
) -> Dict[str, Any]:
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
    if normalized and record_history:
        repeat_count = sum(1 for previous in _RECENT_INSIGHTS if previous == normalized)
        _RECENT_INSIGHTS.append(normalized)
    if repeat_count >= 2:
        reasons.append("recent_repeat_pattern")

    return {
        "generic_output_detected": bool(reasons),
        "generic_output_reasons": reasons,
        "recent_repeat_count": repeat_count,
    }


def _safe_float(value: Any, default: float = _DEFAULT_SCORE) -> tuple[float, bool]:
    try:
        return float(value), False
    except Exception:
        return default, True


def _coerce_string_list(value: Any, fallback: list[str], max_items: int = 3) -> list[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if cleaned:
            return cleaned[:max_items]
    return fallback[:max_items]


def _average_dimension_score(scores: dict[str, dict[str, Any]]) -> float:
    values = [float((item or {}).get("score") or _DEFAULT_SCORE) for item in scores.values()]
    if not values:
        return _DEFAULT_SCORE
    return sum(values) / len(values)


def _derive_recommendation_from_scores(avg_score: float) -> str:
    if avg_score >= 4.2:
        return "Tier A - High Priority Diligence"
    if avg_score >= 3.6:
        return "Tier B - Targeted Validation"
    if avg_score >= 3.0:
        return "Tier C - Conditional Monitoring"
    return "Tier D - Defer"


def _build_summary_from_scores(scores: dict[str, dict[str, Any]]) -> str:
    avg_score = _average_dimension_score(scores)
    strong_dims = [dim_id for dim_id, item in scores.items() if float(item.get("score") or 0.0) >= 4.0]
    weak_dims = [dim_id for dim_id, item in scores.items() if float(item.get("score") or 5.0) <= 2.5]
    headline = f"Average dimension score is {avg_score:.2f}/5 from automated extraction."
    if strong_dims:
        headline += f" Strongest dimensions: {', '.join(str(dim_id) for dim_id in strong_dims[:3])}."
    if weak_dims:
        headline += f" Watch dimensions: {', '.join(str(dim_id) for dim_id in weak_dims[:3])}."
    return headline


def _build_insight_from_scores(scores: dict[str, dict[str, Any]]) -> str:
    dim2 = float(scores.get("2", {}).get("score", _DEFAULT_SCORE))
    dim3 = float(scores.get("3", {}).get("score", _DEFAULT_SCORE))
    dim9 = float(scores.get("9", {}).get("score", _DEFAULT_SCORE))
    if dim9 <= 1.0:
        return "Governance risk signal is severe enough to trigger integrity gate override."
    if dim2 >= 4.0 and dim3 < 3.0:
        return "Scientific quality is promising, but commercialization signals remain early."
    if dim2 < 3.0:
        return "Core scientific rigor appears uncertain and needs deeper manual validation."
    return "Signals are mixed; additional evidence is required for stronger conviction."


def _build_warnings_from_scores(scores: dict[str, dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if float(scores.get("3", {}).get("score", _DEFAULT_SCORE)) < 3.0:
        warnings.append("No clear go-to-market strategy evidence in extracted material")
    if float(scores.get("8", {}).get("score", _DEFAULT_SCORE)) < 3.0:
        warnings.append("Technical or execution uncertainty remains elevated")
    if float(scores.get("9", {}).get("score", _DEFAULT_SCORE)) <= 1.0:
        warnings.append("Governance integrity gate risk detected")
    return warnings or _DEFAULT_WARNINGS[:]


def _has_structured_scores(payload: Dict[str, Any] | Any) -> bool:
    if not isinstance(payload, dict):
        return False
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return False
    valid_count = 0
    for dim_id in range(1, 10):
        item = scores.get(str(dim_id), scores.get(dim_id))
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        try:
            float(score)
            valid_count += 1
        except Exception:
            continue
    return valid_count >= 5

class ScientificEvaluator:
    """Orchestrates scientific due diligence using LLM synthesis."""

    def __init__(self):
        self.api_key = settings.zai_api_key
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.provider_timeout = max(30, int(settings.llm_provider_timeout_seconds))

    @staticmethod
    def _parse_csv(value: str) -> list[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]

    def _provider_sequence(self) -> list[str]:
        configured = [item.lower() for item in self._parse_csv(settings.llm_fallback_order)]
        if not configured:
            configured = ["gemini", "glm", "openrouter"]
        deduped: list[str] = []
        seen: set[str] = set()
        for item in configured:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    @staticmethod
    def _metadata_complexity_markers(metadata: Dict[str, Any]) -> int:
        markers = 0
        source_errors = metadata.get("source_errors", {}) if isinstance(metadata, dict) else {}
        curated = metadata.get("similar_papers_curated", []) if isinstance(metadata, dict) else []
        if isinstance(source_errors, dict) and len(source_errors) == 0:
            markers += 1
        if isinstance(curated, list) and len(curated) >= 5:
            markers += 1
        document_profile = metadata.get("document_profile", {}) if isinstance(metadata, dict) else {}
        if isinstance(document_profile, dict):
            keywords = document_profile.get("keywords")
            if isinstance(keywords, list) and len(keywords) >= 6:
                markers += 1
        return markers

    def _infer_complexity_band(self, text_content: str, metadata: Dict[str, Any]) -> str:
        text = str(text_content or "")
        text_len = len(text)
        text_lower = text.lower()
        method_terms = (
            "method", "methods", "ablation", "dataset", "evaluation", "experiment",
            "randomized", "trial", "statistical", "p-value", "supplementary"
        )
        method_hits = sum(1 for term in method_terms if term in text_lower)
        metadata_markers = self._metadata_complexity_markers(metadata)

        if text_len >= int(settings.llm_complexity_high_chars) or method_hits >= 4 or metadata_markers >= 2:
            return "high"
        if text_len <= int(settings.llm_complexity_low_chars) and method_hits <= 1 and metadata_markers == 0:
            return "low"
        return "medium"

    def _apply_adaptive_routing(
        self,
        providers: list[str],
        text_content: str,
        metadata: Dict[str, Any],
    ) -> tuple[list[str], str]:
        if not settings.llm_adaptive_routing_enabled:
            return providers, "disabled"

        band = self._infer_complexity_band(text_content, metadata)
        if band == "high":
            preferred = ["gemini", "qwen", "glm", "openrouter", "kimi", "minimax", "liquid"]
        elif band == "low":
            preferred = ["qwen", "openrouter", "gemini", "glm", "kimi", "minimax", "liquid"]
        else:
            preferred = ["gemini", "qwen", "openrouter", "glm", "kimi", "minimax", "liquid"]

        rank = {provider: index for index, provider in enumerate(preferred)}
        ordered = sorted(
            providers,
            key=lambda provider: (rank.get(provider, 999), providers.index(provider)),
        )
        return ordered, band

    async def _evaluate_with_openai_compatible(
        self,
        *,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str,
    ) -> Dict[str, Any]:
        clean_key = (api_key or "").strip()
        clean_base = (base_url or "").strip().rstrip("/")
        clean_model = (model or "").strip()
        if not clean_key or not clean_base or not clean_model:
            return {"error": f"{provider_name}_not_configured", "provider": provider_name}

        url = clean_base if clean_base.endswith("/chat/completions") else f"{clean_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": clean_model,
            "messages": [
                {"role": "system", "content": "You are a highly critical scientific analyst."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=float(self.provider_timeout)) as client:
            for attempt in range(1, 3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if not content:
                        raise ValueError(f"{provider_name} returned empty content")
                    parsed = json.loads(content) if isinstance(content, str) else content
                    if isinstance(parsed, dict):
                        parsed["_provider"] = provider_name
                    return parsed if isinstance(parsed, dict) else {"error": "invalid_payload", "provider": provider_name}
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response else None
                    retryable = status in {429, 500, 502, 503, 504}
                    if retryable and attempt < 2:
                        await asyncio.sleep(0.8 * attempt)
                        continue
                    logger.error("%s evaluation failed with status %s: %s", provider_name.upper(), status, exc)
                    return {
                        "error": f"{provider_name}_http_{status}",
                        "provider": provider_name,
                        "status_code": status,
                    }
                except Exception as exc:
                    if attempt < 2:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    logger.error("%s evaluation failed: %s", provider_name.upper(), exc)
                    return {"error": str(exc), "provider": provider_name}

    async def _evaluate_with_gemini(self, prompt: str) -> Dict[str, Any]:
        api_key = settings.gemini_api_key
        if not api_key:
            return {"error": "gemini_not_configured", "provider": "gemini"}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=float(self.provider_timeout)) as client:
            for attempt in range(1, 3):
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
                        raise ValueError("Gemini returned empty content")
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        parsed["_provider"] = "gemini"
                    return parsed
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response else None
                    retryable = status in {429, 500, 502, 503, 504}
                    if retryable and attempt < 2:
                        await asyncio.sleep(1.0 * attempt)
                        continue
                    logger.error("Gemini evaluation failed with status %s: %s", status, exc)
                    return {
                        "error": f"gemini_http_{status}",
                        "provider": "gemini",
                        "status_code": status,
                    }
                except Exception as exc:
                    if attempt < 2:
                        await asyncio.sleep(0.6 * attempt)
                        continue
                    logger.error("Gemini evaluation failed: %s", exc)
                    return {"error": str(exc), "provider": "gemini"}

    async def _evaluate_with_glm(self, prompt: str) -> Dict[str, Any]:
        return await self._evaluate_with_openai_compatible(
            provider_name="glm",
            api_key=self.api_key,
            base_url=self.api_url,
            model="glm-4",
            prompt=prompt,
        )

    async def _evaluate_with_openrouter(self, prompt: str) -> Dict[str, Any]:
        api_key = (settings.openrouter_api_key or "").strip()
        if not api_key:
            return {"error": "openrouter_not_configured", "provider": "openrouter"}

        url = (settings.openrouter_api_url or "https://openrouter.ai/api/v1/chat/completions").strip()
        models = self._parse_csv(settings.openrouter_models)
        if not models:
            return {"error": "openrouter_models_missing", "provider": "openrouter"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url.strip():
            headers["HTTP-Referer"] = settings.openrouter_site_url.strip()
        if settings.openrouter_site_name.strip():
            headers["X-OpenRouter-Title"] = settings.openrouter_site_name.strip()

        async with httpx.AsyncClient(timeout=float(self.provider_timeout)) as client:
            model_errors: dict[str, str] = {}
            for model in models:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a highly critical scientific analyst."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }
                if settings.openrouter_reasoning_enabled:
                    payload["reasoning"] = {"enabled": True}
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if not content:
                        raise ValueError("openrouter_empty_content")
                    parsed = json.loads(content) if isinstance(content, str) else content
                    if isinstance(parsed, dict):
                        parsed["_provider"] = "openrouter"
                        parsed["_model"] = model
                        return parsed
                    model_errors[model] = "invalid_json_payload"
                except Exception as exc:
                    model_errors[model] = str(exc)
                    continue
            return {
                "error": "openrouter_all_models_failed",
                "provider": "openrouter",
                "model_errors": model_errors,
            }

    async def _evaluate_with_kimi(self, prompt: str) -> Dict[str, Any]:
        return await self._evaluate_with_openai_compatible(
            provider_name="kimi",
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            model=settings.kimi_model,
            prompt=prompt,
        )

    async def _evaluate_with_minimax(self, prompt: str) -> Dict[str, Any]:
        return await self._evaluate_with_openai_compatible(
            provider_name="minimax",
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model,
            prompt=prompt,
        )

    async def _evaluate_with_liquid(self, prompt: str) -> Dict[str, Any]:
        return await self._evaluate_with_openai_compatible(
            provider_name="liquid",
            api_key=settings.liquid_ai_api_key,
            base_url=settings.liquid_ai_base_url,
            model=settings.liquid_ai_model,
            prompt=prompt,
        )

    async def _evaluate_with_qwen(self, prompt: str) -> Dict[str, Any]:
        return await self._evaluate_with_openai_compatible(
            provider_name="qwen",
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
            prompt=prompt,
        )

    def _validate_and_repair_schema(
        self,
        eval_result: Dict[str, Any] | Any,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        source_payload = eval_result if isinstance(eval_result, dict) else {}
        repaired_scores: dict[str, dict[str, Any]] = {}
        repair_count = 0
        missing_dimensions: list[int] = []
        defaulted_dimensions: list[int] = []
        clamped_dimensions: list[int] = []
        missing_snippet_dimensions: list[int] = []

        raw_scores = source_payload.get("scores")
        if not isinstance(raw_scores, dict):
            raw_scores = {}
            repair_count += 1

        for dim_id in range(1, 10):
            raw_item = raw_scores.get(str(dim_id), raw_scores.get(dim_id))
            if not isinstance(raw_item, dict):
                raw_item = {}
                missing_dimensions.append(dim_id)
                repair_count += 1

            raw_score = raw_item.get("score")
            score, was_defaulted = _safe_float(raw_score)
            if was_defaulted:
                defaulted_dimensions.append(dim_id)
                repair_count += 1
            clamped_score = max(1.0, min(5.0, score))
            if clamped_score != score:
                clamped_dimensions.append(dim_id)
                repair_count += 1

            rationale = str(raw_item.get("rationale") or "").strip()
            if not rationale:
                rationale = _MISSING_RATIONALE
                repair_count += 1

            origin_snippet = str(raw_item.get("origin_snippet") or raw_item.get("snippet") or "").strip()
            if not origin_snippet:
                origin_snippet = _MISSING_SNIPPET
                missing_snippet_dimensions.append(dim_id)
                repair_count += 1

            repaired_scores[str(dim_id)] = {
                "score": round(clamped_score, 4),
                "rationale": rationale,
                "origin_snippet": origin_snippet,
            }

        executive_summary = str(source_payload.get("executive_summary") or "").strip()
        insight = str(source_payload.get("insight") or "").strip()
        avg_score = _average_dimension_score(repaired_scores)
        if not executive_summary:
            executive_summary = _build_summary_from_scores(repaired_scores)
            repair_count += 1
        if not insight:
            insight = _build_insight_from_scores(repaired_scores)
            repair_count += 1

        investment_recommendation = str(source_payload.get("investment_recommendation") or "").strip()
        if not investment_recommendation:
            investment_recommendation = _derive_recommendation_from_scores(avg_score)
            repair_count += 1

        investor_fit = _coerce_string_list(
            source_payload.get("investor_fit"),
            fallback=_DEFAULT_INVESTOR_FIT,
        )
        if investor_fit == _DEFAULT_INVESTOR_FIT:
            repair_count += 1

        warnings = _coerce_string_list(
            source_payload.get("warnings"),
            fallback=_build_warnings_from_scores(repaired_scores),
        )
        if not source_payload.get("warnings"):
            repair_count += 1

        metadata_payload = metadata if isinstance(metadata, dict) else {}
        source_errors = metadata_payload.get("source_errors")
        source_error_count = len(source_errors) if isinstance(source_errors, dict) else 0
        snippet_present_count = sum(
            1
            for score_item in repaired_scores.values()
            if str(score_item.get("origin_snippet") or "").strip()
            and str(score_item.get("origin_snippet")).strip() != _MISSING_SNIPPET
        )
        snippet_coverage_ratio = round(snippet_present_count / 9.0, 4)

        result = {
            "scores": repaired_scores,
            "executive_summary": executive_summary,
            "investment_recommendation": investment_recommendation,
            "insight": insight,
            "investor_fit": investor_fit,
            "warnings": warnings,
            "_quality_signals": {
                **(source_payload.get("_quality_signals") if isinstance(source_payload.get("_quality_signals"), dict) else {}),
                "schema_repair_applied": repair_count > 0,
                "schema_repair_count": repair_count,
                "missing_dimensions": missing_dimensions,
                "defaulted_dimensions": defaulted_dimensions,
                "clamped_dimensions": clamped_dimensions,
                "missing_snippet_dimensions": missing_snippet_dimensions,
                "source_error_count": source_error_count,
                "snippet_coverage_ratio": snippet_coverage_ratio,
            },
        }
        if source_payload.get("error"):
            result["error"] = str(source_payload.get("error"))

        insufficient_reasons: list[str] = []
        if snippet_coverage_ratio < 0.45:
            insufficient_reasons.append("low_snippet_coverage")
        if source_error_count >= 2:
            insufficient_reasons.append("multiple_source_errors")
        if len(defaulted_dimensions) >= 4:
            insufficient_reasons.append("many_defaulted_dimensions")
        if result.get("error"):
            insufficient_reasons.append("llm_error")
        generic_probe = _detect_generic_output(
            {
                "insight": result.get("insight"),
                "warnings": result.get("warnings"),
                "executive_summary": result.get("executive_summary"),
            },
            record_history=False,
        )
        if generic_probe.get("generic_output_detected"):
            insufficient_reasons.append("generic_output_pattern")

        if insufficient_reasons:
            result["executive_summary"] = _INSUFFICIENT_EVIDENCE_SUMMARY
            result["insight"] = _INSUFFICIENT_EVIDENCE_INSIGHT
            result["investment_recommendation"] = _INSUFFICIENT_EVIDENCE_RECOMMENDATION
            result["investor_fit"] = [
                "Internal diligence team review",
                "Domain expert panel review",
            ]
            merged_warnings = _INSUFFICIENT_EVIDENCE_WARNINGS + list(result.get("warnings") or [])
            result["warnings"] = list(dict.fromkeys(merged_warnings))[:4]
        result["_quality_signals"]["insufficient_evidence"] = bool(insufficient_reasons)
        result["_quality_signals"]["insufficient_evidence_reasons"] = insufficient_reasons
        return result

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
        provider_errors: dict[str, str] = {}
        selected_result: Dict[str, Any] = {}
        selected_provider = "none"
        base_sequence = self._provider_sequence()
        sequence, complexity_band = self._apply_adaptive_routing(base_sequence, llm_text, metadata)
        provider_runners = {
            "gemini": self._evaluate_with_gemini,
            "glm": self._evaluate_with_glm,
            "openrouter": self._evaluate_with_openrouter,
            "qwen": self._evaluate_with_qwen,
            "kimi": self._evaluate_with_kimi,
            "minimax": self._evaluate_with_minimax,
            "liquid": self._evaluate_with_liquid,
        }

        attempted = 0
        for provider_name in sequence:
            runner = provider_runners.get(provider_name)
            if runner is None:
                provider_errors[provider_name] = "unknown_provider"
                continue
            attempted += 1
            provider_result = await runner(prompt)
            if _has_structured_scores(provider_result):
                selected_result = provider_result
                selected_provider = provider_name if attempted == 1 else f"{provider_name}_fallback"
                break
            provider_errors[provider_name] = str(provider_result.get("error") or "no_structured_scores")

        if not selected_result:
            if not provider_errors:
                provider_errors["config"] = "llm_keys_missing_or_invalid_provider_order"
            selected_result = {
                "error": "all_llm_providers_failed",
                "_quality_signals": {
                    "llm_hard_failure": True,
                    "provider_errors": provider_errors,
                },
            }
            selected_provider = "none"

        repaired_result = self._validate_and_repair_schema(selected_result, metadata)
        quality_signals = repaired_result.get("_quality_signals")
        if not isinstance(quality_signals, dict):
            quality_signals = {}
        quality_signals["provider_errors"] = provider_errors
        quality_signals["provider_routing"] = {
            "adaptive_enabled": bool(settings.llm_adaptive_routing_enabled),
            "complexity_band": complexity_band,
            "base_order": base_sequence,
            "effective_order": sequence,
        }
        repaired_result["_quality_signals"] = quality_signals

        llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
        return self._attach_quality_signals(repaired_result, selected_provider, llm_ms)

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
