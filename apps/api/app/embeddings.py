"""EmbeddingProvider interface (RESEARCH.md R2).

SigLIP2Provider runs the real `google/siglip2-base-patch16-256` encoder via 🤗 transformers
(Apache-2.0; Tschannen et al., arXiv:2502.14786). Images and text share one space, so a
role's text query can retrieve photos directly.

FallbackProvider is used when torch/transformers or the weights are unavailable. It is
image-only (colour histogram + edge layout); `cross_modal=False` tells the weaver to use
lexical matching over Memory Atoms for text→moment retrieval. Results always record
which provider ran — the demo must never claim SigLIP 2 unless it actually did.
"""
import os
from functools import lru_cache
from typing import Protocol

import numpy as np
from PIL import Image

SIGLIP2_ID = os.getenv('MEMORY_ATLAS_SIGLIP_MODEL', 'google/siglip2-base-patch16-256')


class EmbeddingProvider(Protocol):
    name: str
    model_id: str | None
    cross_modal: bool

    def embed_images(self, images: list[Image.Image]) -> np.ndarray: ...
    def embed_texts(self, texts: list[str]) -> np.ndarray | None: ...


def _features(out) -> np.ndarray:
    # transformers ≤4.x returns a tensor; 5.x returns a ModelOutput whose pooler_output is the projected embedding.
    tensor = getattr(out, 'pooler_output', None) if not hasattr(out, 'float') else out
    return tensor.float().numpy()


def _normalize(x: np.ndarray) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-9)


class SigLIP2Provider:
    name, cross_modal = 'siglip2', True

    def __init__(self, model_id: str = SIGLIP2_ID):
        import torch
        from transformers import AutoModel, AutoProcessor
        self.model_id, self._torch = model_id, torch
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).eval()

    def embed_images(self, images):
        with self._torch.no_grad():
            inputs = self.processor(images=images, return_tensors='pt')
            return _normalize(_features(self.model.get_image_features(**inputs)))

    def embed_texts(self, texts):
        with self._torch.no_grad():
            # SigLIP was trained with max_length padding of 64 tokens; lowercase prompts match its training text.
            inputs = self.processor(text=[t.lower() for t in texts], padding='max_length', max_length=64, truncation=True, return_tensors='pt')
            return _normalize(_features(self.model.get_text_features(**inputs)))


class FallbackProvider:
    name, model_id, cross_modal = 'fallback', None, False

    def embed_images(self, images):
        feats = []
        for img in images:
            small = np.asarray(img.convert('HSV').resize((64, 64)), dtype=float)
            h, s, v = small[..., 0] / 256, small[..., 1] / 256, small[..., 2] / 256
            hist, _ = np.histogramdd(np.stack([h, s, v], -1).reshape(-1, 3), bins=(8, 4, 4), range=((0, 1),) * 3)
            gray = np.asarray(img.convert('L').resize((16, 16)), dtype=float) / 255
            gx, gy = np.diff(gray, axis=1)[:-1], np.diff(gray, axis=0)[:, :-1]
            layout = np.concatenate([gray.flatten() - gray.mean(), np.hypot(gx, gy).flatten()])
            feats.append(np.concatenate([np.sqrt(hist.flatten() / hist.sum()), layout * 0.35]))
        return _normalize(np.array(feats))

    def embed_texts(self, texts):
        return None


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    choice = os.getenv('MEMORY_ATLAS_EMBEDDINGS', 'auto')
    if choice in ('auto', 'siglip2'):
        try:
            return SigLIP2Provider()
        except Exception:  # missing torch/transformers/weights → honest fallback
            if choice == 'siglip2':
                raise
    return FallbackProvider()
