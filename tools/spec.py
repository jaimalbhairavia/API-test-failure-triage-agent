"""get_api_spec tool: return the OpenAPI definition for a given endpoint.

No-op (returns an informational message) if no spec file was configured
for this run. Supports JSON and YAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

_SPEC_DATA: Optional[dict] = None


def set_spec_path(path: Optional[str]) -> None:
    """Load the OpenAPI file once at startup. Pass None to disable."""
    global _SPEC_DATA
    if not path:
        _SPEC_DATA = None
        return

    spec_path = Path(path)
    if not spec_path.exists():
        _SPEC_DATA = None
        return

    text = spec_path.read_text()
    if spec_path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "PyYAML is required to read YAML OpenAPI specs. Install with `pip install pyyaml`."
            ) from e
        _SPEC_DATA = yaml.safe_load(text)
    else:
        _SPEC_DATA = json.loads(text)


@tool
def get_api_spec(endpoint_path: str, method: str = "") -> str:
    """Return the OpenAPI path-object for an endpoint.

    Args:
        endpoint_path: URL path template, e.g. "/users/{id}".
        method: Optional HTTP verb ("get", "post", ...); if omitted,
            returns the full path object including all methods.

    Returns:
        JSON-encoded spec excerpt or a not-found message.
    """
    if _SPEC_DATA is None:
        return "No OpenAPI spec configured for this run."

    paths = _SPEC_DATA.get("paths", {}) or {}
    path_obj = paths.get(endpoint_path)

    # Fuzzy: try common variants
    if path_obj is None:
        variants = {
            endpoint_path.rstrip("/"),
            endpoint_path.lstrip("/"),
            "/" + endpoint_path.lstrip("/"),
        }
        for v in variants:
            if v in paths:
                endpoint_path = v
                path_obj = paths[v]
                break

    if path_obj is None:
        available = list(paths.keys())
        sample = available[:20]
        return (
            f"Path '{endpoint_path}' not found in spec. "
            f"Spec has {len(available)} paths. First 20: {sample}"
        )

    if method:
        op = path_obj.get(method.lower())
        if not op:
            return (
                f"Method '{method}' not documented for '{endpoint_path}'. "
                f"Available methods: {[m for m in path_obj.keys() if m != 'parameters']}"
            )
        return json.dumps({endpoint_path: {method.lower(): op}}, indent=2, default=str)

    return json.dumps({endpoint_path: path_obj}, indent=2, default=str)
