"""
Nerve‑style configuration loader.

This module provides a helper for loading agent configuration from a YAML
file, inspired by the Nerve Agent Development Kit. The configuration
allows non‑developers to influence the behavior of the organic virtual pet
without modifying Python code. It currently supports a top‑level ``agent``
section with a ``system_prompt`` key and an optional ``tasks`` section.

The file ``agent_config.yaml`` must reside in the same directory as this
module. If it is missing or malformed, an empty configuration is returned.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def load_agent_config() -> Dict[str, Any]:
    """Load the agent configuration from ``agent_config.yaml``.

    Returns a dictionary parsed from YAML. If the file cannot be read or
    parsed, an empty dictionary is returned instead. The caller should
    handle missing keys gracefully.

    Returns:
        dict: The parsed YAML configuration, or an empty dict on error.
    """
    config_path = os.path.join(os.path.dirname(__file__), "agent_config.yaml")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}