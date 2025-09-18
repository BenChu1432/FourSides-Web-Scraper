import os
from typing import Optional
from util.jsonSanitize import safe_parse_json

try:
    from together import Together
    _available = True
except Exception:
    _available = False

DEFAULT_MODEL = os.getenv("TOGETHER_MODEL", "Qwen/Qwen3-235B-A22B-fp8-tput")

class TogetherClickbaitClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if not _available:
            raise RuntimeError("together package is not available")
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise RuntimeError("TOGETHER_API_KEY not set")
        self.client = Together(api_key=self.api_key)
        self.model = model or DEFAULT_MODEL

        self.system_prompt = """你是一位新聞分析助理，專門負責判斷新聞文章標題是否屬於標題黨，並提供信心分數、具體說明與中性標題建議。

嚴格輸出規則（務必遵守）：
- 僅輸出「一個」JSON 物件，不要輸出任何其他文字、說明或程式碼區塊。
- 不要使用 Markdown 圍欄（例如 ```json）。
- 僅能使用頂層鍵：clickbait。
- 任何字串中的英文雙引號 " 需以 \\" 轉義；可以使用全形引號「」不需轉義。
- 不要使用單一收尾引號 ’ 造成 JSON 字串不合法。
- 字串中的換行請使用 \\n。
- 不要包含多餘逗號（trailing commas）。
- clickbait.confidence 必須為 0 到 1 的數字（兩位小數），explanation 和 refined_title 為非空字串。

1) 新聞報道標題黨程度（clickbait）
- 評估標題是否有誇張形容、恐嚇語、賣關子、絕對化、或標題與內文落差大
- 信心分數建議：0.00-0.30/0.31-0.60/0.61-0.85/0.86-1.00
- refined_title：中性克制，不留懸念。""".strip()

    def get_clickbait(self, headline: str) -> Optional[dict]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": headline.strip()}
                ]
            )
            raw = resp.choices[0].message.content
            data = safe_parse_json(raw)
            cb = data.get("clickbait")
            if isinstance(cb, dict):
                conf = self._coerce_float_0_1(cb.get("confidence"))
                exp = cb.get("explanation") if isinstance(cb.get("explanation"), str) and cb.get("explanation").strip() else None
                rt = cb.get("refined_title") if isinstance(cb.get("refined_title"), str) and cb.get("refined_title").strip() else None
                if conf is not None and exp and rt:
                    return {"confidence": conf, "explanation": exp.strip(), "refined_title": rt.strip()}
        except Exception:
            return None
        return None

    @staticmethod
    def _coerce_float_0_1(x):
        try:
            f = float(x)
            f = 0.0 if f < 0 else (1.0 if f > 1 else f)
            return round(f, 2)
        except Exception:
            return None