from __future__ import annotations

import importlib


def load_schema(indicator_path: str) -> dict:
    module_path = indicator_path.replace(
        "/indicator.py",
        ".schema"
    ).replace("/", ".")

    module = importlib.import_module(module_path)

    return getattr(
        module,
        "PARAMETERS",
        {}
    )
