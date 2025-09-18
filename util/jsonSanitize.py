import re, json
from typing import Optional

def _extract_first_top_level_json_object(s: str) -> Optional[str]:
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
    return None

def _strip_code_fences_and_duplicates(content: str) -> str:
    s = content.strip()
    s = re.sub(r"```[a-zA-Z]*", "", s)
    s = s.replace("```", "")
    s = re.sub(r'\bjson_str\s*:\s*\{[\s\S]*?\}\s*$', '', s, flags=re.IGNORECASE)
    first_obj = _extract_first_top_level_json_object(s)
    return first_obj if first_obj is not None else s

def safe_parse_json(content: str) -> dict:
    cleaned = _strip_code_fences_and_duplicates(content)
    json_candidate = _extract_first_top_level_json_object(cleaned)
    if json_candidate is None:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model output")
        json_candidate = cleaned[start:end+1]
    j = json_candidate
    j = j.replace("’", "'").replace("‘", "'")
    j = j.replace("“", '"').replace("”", '"')
    j = re.sub(r",\s*([}\]])", r"\1", j)
    j = j.replace("\t", "    ")
    j = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", j)
    return json.loads(j)

def is_retriable_error_msg(msg: str) -> bool:
    msg = (msg or "").upper()
    return any(tok in msg for tok in ("500", "503", "504", "INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "TIMEOUT"))