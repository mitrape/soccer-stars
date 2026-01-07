# shared/netcodec.py
import json
from typing import Any, Dict, Optional

def dumps_line(msg: Dict[str, Any]) -> bytes:
    """dict -> JSON bytes ending with newline"""
    return (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")

def loads_line(line: bytes) -> Optional[Dict[str, Any]]:
    """JSON line bytes -> dict, or None if invalid"""
    try:
        s = line.decode("utf-8").strip()
        if not s:
            return None
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None