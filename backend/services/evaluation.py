"""Evaluation service for scientific paper analysis using LLMs."""

import logging
import json
import httpx
from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.models.scoring import DIMENSION_NAMES

logger = logging.getLogger(__name__)

class ScientificEvaluator:
    """Orchestrates scientific due diligence using LLM synthesis."""

    def __init__(self):
        self.api_key = settings.zhipu_api_key or settings.zai_api_key
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

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
        if not self.api_key:
            logger.error("No Zhipu/GLM API key found for evaluation.")
            return {}

        metadata_str = json.dumps(enriched_data or {}, indent=2)
        
        prompt = f"""
        You are the Head of Scientific Due Diligence at MatDAO.
        Your task is to evaluate a scientific paper for investment and research support.
        
        ### DATA SOURCES
        1. Extracted Paper Text:
        {text_content[:20000]}
        
        2. API Metadata (Citations, Retractions, Peer Review):
        {metadata_str}

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
            "investment_recommendation": "Tier A/B/C/Reject"
        }}
        """

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
