from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def compute_content_hash(normalized: Mapping[str, Any]) -> str:
    stable = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
