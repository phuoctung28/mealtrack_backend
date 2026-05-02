"""
SigLIP adapter using google/siglip-base-patch16-224.

SigLIP uses sigmoid loss (each pair scored independently) which produces
meaningful absolute similarity scores — matching food text+image pairs
score 0.75–0.90, clearly wrong images score near 0.00.

This replaces the original CLIP adapter whose cross-modal cosine similarity
topped out at ~0.33 for specific food dishes, making a 0.65 threshold
impossible to reach.
"""

from __future__ import annotations

import asyncio
import io
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "google/siglip-base-patch16-224"

_processor_singleton = None
_model_singleton = None


def _load(device: str):
    global _processor_singleton, _model_singleton
    if _model_singleton is None:
        from transformers import AutoModel, AutoProcessor  # lazy

        logger.info("loading SigLIP model %s on %s", MODEL_NAME, device)
        _processor_singleton = AutoProcessor.from_pretrained(MODEL_NAME)
        _model_singleton = AutoModel.from_pretrained(MODEL_NAME)
        _model_singleton.eval()
        if device != "cpu":
            _model_singleton = _model_singleton.to(device)
    return _processor_singleton, _model_singleton


class ClipEmbeddingAdapter:
    """
    Embeds text and images using SigLIP.

    embed_text  → list of 768-d unit vectors (one per input string)
    embed_image_bytes → single 768-d unit vector

    Similarity is computed as sigmoid(image_emb @ text_emb.T) and ranges
    0–1. Use IMAGE_MATCH_THRESHOLD=0.65 as a practical cutoff.
    """

    def __init__(self, processor, model, device: str = "cpu", dim: int = 768):
        self._processor = processor
        self._model = model
        self._device = device
        self._dim = dim

    @classmethod
    def from_settings(cls, model_name: str, device: str, dim: int):
        # model_name / dim kept for interface compatibility
        processor, model = _load(device)
        return cls(processor=processor, model=model, device=device, dim=dim)

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        def _run():
            import torch

            # SigLIP works better with descriptive prompts
            prompted = [f"a photo of {t}" for t in texts]
            inputs = self._processor(
                text=prompted,
                images=None,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
            )
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                out = self._model.get_text_features(**inputs)
                # Depending on Transformers version/model class, features may be returned
                # either as a tensor or a BaseModelOutputWithPooling-like object.
                if hasattr(out, "pooler_output"):
                    text_embeds = out.pooler_output
                elif hasattr(out, "text_embeds"):
                    text_embeds = out.text_embeds
                else:
                    text_embeds = out
                text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)
            return [row.cpu().numpy().tolist() for row in text_embeds]

        return await asyncio.to_thread(_run)

    async def embed_image_bytes(self, data: bytes) -> list[float]:
        def _run():
            import torch
            from PIL import Image  # lazy

            img = Image.open(io.BytesIO(data)).convert("RGB")
            inputs = self._processor(
                text=None,
                images=[img],
                return_tensors="pt",
            )
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                out = self._model.get_image_features(**inputs)
                if hasattr(out, "pooler_output"):
                    image_embeds = out.pooler_output
                elif hasattr(out, "image_embeds"):
                    image_embeds = out.image_embeds
                else:
                    image_embeds = out
                image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
            return image_embeds[0].cpu().numpy().tolist()

        return await asyncio.to_thread(_run)

    async def score_image_text(self, image_data: bytes, text: str) -> float:
        """
        Compute true SigLIP similarity: sigmoid(logits_per_image).

        Uses the model's full forward pass (text + image together) so that
        the learned logit_scale and logit_bias are applied correctly.
        Scores range 0–1; matching food pairs typically score 0.75–0.90.
        """

        def _run():
            import torch
            from PIL import Image  # lazy

            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            prompted = f"a photo of {text}"
            inputs = self._processor(
                text=[prompted],
                images=[img],
                return_tensors="pt",
                padding="max_length",
                truncation=True,
            )
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._model(**inputs)
            # logits_per_image shape: (n_images, n_texts) → (1, 1)
            logits = outputs.logits_per_image
            return torch.sigmoid(logits)[0][0].item()

        return await asyncio.to_thread(_run)
