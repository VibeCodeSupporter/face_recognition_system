"""Shared ONNX Runtime session creation with GPU-first CPU fallback."""

from __future__ import annotations

import logging
from pathlib import Path

import onnxruntime as ort


logger = logging.getLogger(__name__)


def create_inference_session(model_path: str | Path) -> ort.InferenceSession:
    """Prefer NVIDIA CUDA when the installed ONNX Runtime can initialize it."""
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        preload_dlls = getattr(ort, "preload_dlls", None)
        if preload_dlls is not None:
            try:
                preload_dlls()
            except Exception as error:
                logger.warning("Could not preload CUDA/cuDNN libraries: %s", error)
        try:
            session = ort.InferenceSession(
                str(model_path),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            logger.info("ONNX model %s uses providers %s", model_path, session.get_providers())
            return session
        except Exception as error:
            logger.warning(
                "CUDA provider unavailable for %s; falling back to CPU: %s",
                model_path,
                error,
            )

    session = ort.InferenceSession(
        str(model_path), providers=["CPUExecutionProvider"]
    )
    logger.info("ONNX model %s uses CPUExecutionProvider", model_path)
    return session
