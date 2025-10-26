"""
Image recognition utilities for the organic virtual pet.

This module provides helper functions to extract simple visual features from
user-provided images and to classify images using the Google Cloud Vision
API when available. These functions allow the virtual pet to build a
"photographic" memory by storing compact representations of images and
associating them with semantic labels. If the Vision API is not configured,
the module falls back to computing basic features without classification.

The primary functions are:

* ``extract_features`` – Convert raw image bytes into a normalized feature
  vector by resizing and flattening the image. This provides a compact
  representation suitable for similarity search.
* ``classify_image`` – Use the Vision API to detect labels for an image.
  When the API client is unavailable or credentials are missing, it returns
  an empty list. You can extend this function to use other classification
  services or on-device models.

Example usage::

    from .image_recognition import extract_features, classify_image
    with open("photo.jpg", "rb") as f:
        data = f.read()
    features = extract_features(data)
    labels = classify_image(data)

The returned ``features`` is a list of floats (length 768) and ``labels``
is a list of strings describing the content of the image.

Note: To enable label detection with the Vision API, you must set the
``GOOGLE_APPLICATION_CREDENTIALS`` environment variable to point to a
service account JSON key and install the ``google-cloud-vision`` package.

"""

from __future__ import annotations

import os
import io
import logging
from typing import List, Optional

import numpy as np  # type: ignore
import cv2  # type: ignore

# Configure logging
logger = logging.getLogger(__name__)

# Attempt to import the Google Cloud Vision client. If unavailable or
# credentials are not configured, Vision API calls will be skipped.
try:
    from google.cloud import vision  # type: ignore
    _vision_client: Optional[vision.ImageAnnotatorClient] = None
except Exception:
    vision = None  # type: ignore
    _vision_client = None


def _get_vision_client() -> Optional["vision.ImageAnnotatorClient"]:
    """Lazily initialize the Vision API client if possible.

    Returns ``None`` when the vision library is not available or the
    ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable is not set. This
    prevents import and initialization errors when running locally without
    credentials.
    """
    global _vision_client
    if vision is None:
        logger.warning("🔴 Google Cloud Vision library not available")
        return None
        
    if _vision_client is not None:
        return _vision_client
        
    # Only initialize if credentials exist and file is present
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    logger.info("🔍 Checking Vision API credentials: %s", cred_path or "not set")
    
    if not cred_path or not os.path.exists(cred_path):
        logger.warning("🔴 Vision API credentials not found or invalid")
        return None
        
    try:
        _vision_client = vision.ImageAnnotatorClient()  # type: ignore
        logger.info("✅ Vision API client initialized successfully")
        return _vision_client
    except Exception as e:
        logger.error("🔴 Failed to initialize Vision API client: %s", str(e))
        return None


def extract_features(image_bytes: bytes, size: int = 16) -> List[float]:
    """Extract a normalized feature vector from raw image bytes.

    The image is decoded with OpenCV, resized to ``size x size`` pixels,
    converted to the RGB color space, and flattened into a 1D array. The
    resulting values are normalized to [0, 1] by dividing by 255. If the
    image cannot be decoded, a zero vector is returned.

    Args:
        image_bytes: Raw bytes of the image (e.g., from a file or base64).
        size: The target width and height for downsampling. Defaults to 16.

    Returns:
        A list of floats representing the normalized pixel values.
    """
    # Convert bytes to a NumPy array for OpenCV decoding
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        # Cannot decode; return a zero vector
        return [0.0] * (size * size * 3)
    # Resize to a small fixed size for compact representation
    img_resized = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    # Convert BGR (OpenCV default) to RGB
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    # Flatten and normalize to [0, 1]
    feature_vec = img_rgb.flatten().astype(float) / 255.0
    return feature_vec.tolist()


def classify_image(image_bytes: bytes, max_results: int = 5) -> List[str]:
    """Detect labels for the given image using Google Cloud Vision.

    When the Vision API client is available and properly configured, this
    function calls ``annotate_image`` to retrieve label annotations. It
    returns the top labels (limited by ``max_results``) sorted by score.

    If the client is not available or the API call fails, the function
    returns an empty list. You can extend this function to integrate
    alternative classifiers (e.g., on-device models) or return fallback
    labels based on simple heuristics.

    Args:
        image_bytes: Raw bytes of the image.
        max_results: Maximum number of labels to return.

    Returns:
        A list of label descriptions or an empty list on failure.
    """
    logger.info("🔍 Attempting to classify image using Vision API...")
    
    client = _get_vision_client()
    if client is None:
        logger.warning("❌ Vision API client not available")
        return []
    
    try:
        image = vision.Image(content=image_bytes)  # type: ignore
        logger.info("📡 Calling Vision API for label detection...")
        
        response = client.label_detection(image=image, max_results=max_results)
        
        if response.error.message:
            logger.error("❌ Vision API error: %s", response.error.message)
            return []
            
        labels = sorted(response.label_annotations, key=lambda x: x.score, reverse=True)
        label_descriptions = [label.description for label in labels[:max_results]]
        
        logger.info("✅ Vision API returned %d labels: %s", len(label_descriptions), label_descriptions)
        return label_descriptions
        
    except Exception as e:
        logger.error("❌ Vision API call failed: %s", str(e))
        # Fail silently and return no labels
        return []