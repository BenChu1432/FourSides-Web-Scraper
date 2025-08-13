from typing import Optional
from opencc import OpenCC

# Create a converter: Simplified to Traditional
cc = OpenCC('s2tw')  # Other options: t2s, s2tw, s2hk, s2twp


def translateIntoTraditionalChinese(text:str):
    return cc.convert(text)

def safeTranslateIntoTraditionalChinese(txt: Optional[str]) -> Optional[str]:
    # If your DB column is NOT NULL, return "" instead of None here.
    if txt is None:
        return None
    stripped = txt.strip()
    if not stripped:
        return stripped  # keep empty string as-is
    try:
        return translateIntoTraditionalChinese(stripped)
    except Exception:
        # Fallback to original on translator errors
        return stripped
