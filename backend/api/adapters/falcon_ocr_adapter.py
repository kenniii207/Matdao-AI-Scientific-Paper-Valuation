"""Falcon-OCR (300M) adapter — Local vision-language extraction on GPU.

Loads the TII Falcon-OCR 300M model for secondary extraction of tables, 
formulas, and complex layouts.
"""

import logging
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor
from backend.core.exceptions import AdapterError

logger = logging.getLogger(__name__)

class FalconOCRAdapter:
    """Singleton adapter for loading and running Falcon-OCR 300M."""
    
    _model = None
    _processor = None
    
    def __init__(self, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._ensure_loaded()

    def _ensure_loaded(self):
        """Lazy load model and processor to shared class variables."""
        if FalconOCRAdapter._model is None:
            logger.info(f"Loading Falcon-OCR (300M) onto {self.device}...")
            try:
                # Use float16 on GPU to save memory (fits in ~0.5 GB)
                torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
                
                FalconOCRAdapter._processor = AutoProcessor.from_pretrained(
                    "tiiuae/Falcon-OCR", 
                    trust_remote_code=True
                )
                FalconOCRAdapter._model = AutoModel.from_pretrained(
                    "tiiuae/Falcon-OCR",
                    trust_remote_code=True,
                    torch_dtype=torch_dtype
                ).to(self.device).eval()
                
                logger.info("Falcon-OCR loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Falcon-OCR model: {str(e)}")
                FalconOCRAdapter._model = None # Reset for retry
                raise AdapterError(f"Falcon-OCR model load failed: {str(e)}")

    async def ocr(self, image: Image.Image, prompt: str = "Extract the text from this document image.") -> str:
        """Run inference on the provided image."""
        if not FalconOCRAdapter._model:
            raise AdapterError("Falcon-OCR model not loaded.")
            
        try:
            # Prepare inputs
            inputs = self._processor(images=image, text=prompt, return_tensors="pt").to(self.device)
            if self.device == "cuda":
                inputs = {k: v.to(torch.float16) if v.dtype == torch.float32 else v for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = FalconOCRAdapter._model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=False,
                    num_beams=1
                )
            
            result = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return result.strip()
        except Exception as e:
            logger.error(f"Falcon-OCR inference failed: {str(e)}")
            raise AdapterError(f"Falcon-OCR processing error: {str(e)}")
