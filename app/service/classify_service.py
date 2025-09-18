import asyncio
import re
from typing import Any, Dict, List, Optional
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# External deps in your project
from app.modals.newsEntity import NewsEntity
from scrapers.news import AssessmentItem
from util import traditionalChineseUtil

# --- Optional: Together integration stub (kept for completeness, unchanged behavior) ---
try:
    from together import Together
    _together_available = True
except Exception:
    _together_available = False

load_dotenv()

# Configure providers
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

# Together client (lazy init)
_TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "Qwen/Qwen3-235B-A22B-fp8-tput")
_TOGETHER_ENABLED = os.getenv("TOGETHER_API_KEY") is not None and _together_available

_together_client = None
def _get_together_client():
    global _together_client
    if _together_client is None and _TOGETHER_ENABLED:
        _together_client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
    return _together_client

def get_clickbait_data_from_together(headline: str) -> Optional[dict]:
    if not _TOGETHER_ENABLED:
        return None
    client = _get_together_client()
    if client is None:
        return None

    system_prompt = """
你是一位新聞分析助理，專門負責判斷新聞文章標題是否屬於標題黨，並提供信心分數、具體說明與中性標題建議。

嚴格輸出規則（務必遵守）：
- 僅輸出「一個」JSON 物件，不要輸出任何其他文字、說明或程式碼區塊。
- 不要使用 Markdown 圍欄（例如 ```json）。
- 僅能使用頂層鍵：clickbait。
- 任何字串中的英文雙引號 " 需以 \\" 轉義；可以使用全形引號「」不需轉義。
- 不要使用單一收尾引號 ’ 造成 JSON 字串不合法。
- 字串中的換行請使用 \\n。
- 不要包含多餘逗號（trailing commas）。
- clickbait.confidence 必須為 0 到 1 的數字（兩位小數），explanation 和 refined_title 為非空字串。
""".strip()

    try:
        resp = client.chat.completions.create(
            model=_TOGETHER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": headline.strip()}
            ]
        )
        raw = resp.choices[0].message.content
        data = safe_parse_json(raw)
        cb = data.get("clickbait")
        if isinstance(cb, dict):
            conf = _coerce_float_0_1(cb.get("confidence"))
            exp = cb.get("explanation") if isinstance(cb.get("explanation"), str) and cb.get("explanation").strip() else None
            rt = cb.get("refined_title") if isinstance(cb.get("refined_title"), str) and cb.get("refined_title").strip() else None
            if conf is not None and exp and rt:
                return {"confidence": conf, "explanation": exp.strip(), "refined_title": rt.strip()}
    except Exception:
        return None
    return None

# ----------------------------------------------

ALLOWED_TAGS = {
    "journalistic_merits": [
        "**multiple_perspectives**（多元觀點）",
        "**logical_flow**（邏輯清晰）",
        "**use_of_real_world_examples**（實例具體）",
        "**constructive_criticism**（具建設性批評）",
        "**avoidance_of_nationalism_or_populism**（避免民族主義或民粹主義）",
        "**source_transparency**（消息來源透明）",
        "**clarification_of_uncertainty**（澄清不確定性）",
        "**background_context**（背景脈絡充分）",
        "**transparency_of_process(報導過程透明)",
        "**depth_of_analysis** (分析深入)",
        "**engagement_with_complexity** (有處理議題的複雜性)",
        "**local_relevance_and_contextualization** (在地脈絡化與關聯性)",
        "**independence_from_power** (報導獨立性強)",
        "**clarity_of_purpose** (報導目的明確)",
        "**accountability_framing**（持份者責任歸屬明確）",
        "**ethical_reporting**（具倫理意識的報導）",
        "**use_of_data**（善用數據）",
        "**cultural_humility**（展現文化謙遜）",
        "**centering_affected_voices**（凸顯當事者觀點）",
        "**readability**（表達易懂）",
        "**headline_reflects_content**（標題與內文一致）",
        "**public_interest_orientation**（以公共利益為導向）",
        "**critical_thinking_encouraged**（促進批判思考）",
        "**timely_relevance_and_timeless_insight**（報道具時效性和長遠啟發性）"
    ],
    "journalistic_demerits": [
        "**decontextualisation**（脫離語境/缺乏細緻脈絡）",
        "**clickbait**（標題黨）",
        "**fear_mongering**（惡意引起社會恐慌）",
        "**cherry_picking**（選擇性舉例）",
        "**loaded_language**（情緒性用語）",
        "**conflation**（不當混淆）",
        "**lack_of_balance**（缺乏平衡觀點）",
        "**overemphasis_on_profanity_and_insults**（過度放大粗俗語言或人身攻擊）",
        "**social_media_amplification_trap**（社群放大陷阱）",
        "**nationalistic framing**（民族主義框架）",
        "**corporate_glorification**（企業美化）",
        "**overemphasis_on_glory**（過度強調成就）",
        "**propagandistic_tone**（大外宣語調）",
        "**overuse_of_statistics_without_verification**（數據濫用或未驗證）",
        "**no_critical_inquiry_or_accountability**（缺乏批判與責任追究）",
        "**strategic_omission**（策略性忽略）",
        "**anonymous_authority**（不具名權威）",
        "**minor_incident_magnification**（小事件誇大）",
        "**victimhood_framing**（受害者框架）",
        "**heroic_framing**（英雄敘事）",
        "**binary_framing**（非黑即白敘事）",
        "**moral_judgment_framing**（道德判斷包裝）",
        "**cultural_essentialism**（文化本質論）",
        "**traditional_values_shield**（主張傳統價值作擋牌）",
        "**pre_criminal_framing**（預設有罪）"
    ],
    "reporting_style": [
        "he_said_she_said_reporting",
        "propagandistic_reporting",
        "investigative_reporting",
        "solutions_journalism",
        "feature_reporting",
        "advocacy_journalism",
        "opinion_reporting",
        "sensationalist_reporting",
        "stenographic_reporting",
        "data_journalism",
        "explanatory_reporting",
        "entertainment_reporting",
        "infotainment_reporting",
        "patriotic_reporting"
    ]
}

journalistic_merits_list = "\n".join([f"- {tag}" for tag in ALLOWED_TAGS["journalistic_merits"]])
misguiding_tools_list = "\n".join([f"- {tag}" for tag in ALLOWED_TAGS["journalistic_demerits"]])
reporting_style_list = "\n".join([f"- {tag}" for tag in ALLOWED_TAGS["reporting_style"]])

# ---- System prompt (hardened) ----
system_prompt = f"""
你是一位新聞分析助理，專門負責判斷新聞文章中多大程度上存在以下特定的新聞優點和誤導性報導技術，並針對每一項提供清楚、有根據的說明。

嚴格輸出規則（務必遵守）：
- 僅輸出「一個」JSON 物件，不要輸出任何其他文字、說明或程式碼區塊。
- 不要使用 Markdown 圍欄（例如 ```json）。
- 僅能使用頂層鍵：clickbait、journalistic_demerits、journalistic_merits、reporting_style、reporting_intention。
- 任何字串中的英文雙引號 " 需以 \\" 轉義；可以使用全形引號「」不需轉義。
- 不要使用單一收尾引號 ’ 造成 JSON 字串不合法。
- 字串中的換行請使用 \\n。
- 不要包含多餘逗號（trailing commas）。
- clickbait.confidence 必須為 0 到 1 的數字（兩位小數），explanation/refined_title 為非空字串。
- 僅包含實際出現且適用的標籤（merits/demerits），沒有出現就省略該子鍵。

---
1) 新聞報道標題黨程度（clickbait）
- 評估標題是否有誇張形容、恐嚇語、賣關子、絕對化等特徵。
- 信心分數：
  - 0.00--0.30：無明顯標題黨元素
  - 0.31--0.60：輕微吸睛
  - 0.61--0.85：多種特徵且誇張
  - 0.86--1.00：嚴重誇張或與內文落差大
- refined_title：中性克制、直接反映內文，不留懸念。

2a) 誤導手法（journalistic_demerits）
只標示有關或出現過的：
{misguiding_tools_list}

2b) 新聞優點（journalistic_merits）
只標示有具體體現的：
{journalistic_merits_list}

3) 新聞報道風格（reporting_style）
{reporting_style_list}

4) 新聞報道目的（reporting_intention）
自擬 1-3 項，每項最多 10 字。

輸出 JSON 範例（鍵名固定；僅示意型態，實際只輸出有出現的子鍵）：
{{
  "clickbait": {{
    "confidence": 0.00,
    "explanation": "……",
    "refined_title": "……"
  }},
  "journalistic_demerits": {{
    "anonymous_authority": {{
      "description": "……",
      "degree": "low"
    }}
  }},
  "journalistic_merits": {{
    "headline_reflects_content": {{
      "description": "……",
      "degree": "high"
    }}
  }},
  "reporting_style": ["feature_reporting", "explanatory_reporting"],
  "reporting_intention": ["事實報導", "事件釐清"]
}}
"""

# ---------- Helpers ----------
def _is_retriable_error_msg(msg: str) -> bool:
    msg = (msg or "").upper()
    retriable_tokens = ("500", "503", "504", "INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "TIMEOUT")
    return any(tok in msg for tok in retriable_tokens)

def _normalize_degree(val: str) -> str:
    if not isinstance(val, str):
        return "low"
    v = val.strip().lower()
    return v if v in {"low", "moderate", "high"} else "low"

def _build_clean_allowed_set(raw_tags: List[str]) -> set:
    clean = set()
    for t in raw_tags:
        if t.startswith("**") and t.count("**") >= 2:
            core = t.split("**")[1].strip()
        else:
            core = t
        core = core.replace("（", " ").replace("）", " ").strip()
        clean.add(core)
    return clean

_CLEAN_ALLOWED_DEMERITS = _build_clean_allowed_set(ALLOWED_TAGS["journalistic_demerits"])
_CLEAN_ALLOWED_MERITS = _build_clean_allowed_set(ALLOWED_TAGS["journalistic_merits"])

def _clean_key(key: str) -> str:
    if not isinstance(key, str):
        return ""
    k = key.strip()
    if k.startswith("**") and k.count("**") >= 2:
        k = k.split("**")[1].strip()
    k = k.replace("（", " ").replace("）", " ").strip()
    return k

def _coerce_float_0_1(x: Any) -> Optional[float]:
    try:
        f = float(x)
        if f < 0:
            f = 0.0
        if f > 1:
            f = 1.0
        return round(f + 1e-8, 2)
    except Exception:
        return None

def _strip_code_fences_and_duplicates(content: str) -> str:
    s = content.strip()
    s = re.sub(r"```[a-zA-Z]*", "", s)
    s = s.replace("```", "")
    s = re.sub(r'\bjson_str\s*:\s*\{[\s\S]*?\}\s*$', '', s, flags=re.IGNORECASE)
    first_obj = _extract_first_top_level_json_object(s)
    if first_obj is not None:
        return first_obj
    return s

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
    def _strip_ctrl(m: re.Match) -> str:
        return " "
    j = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", _strip_ctrl, j)
    return json.loads(j)

def _set_empty_fields(a: NewsEntity):
    a.refined_title = None
    a.reporting_style = []
    a.reporting_intention = []
    a.journalistic_demerits = {}
    a.journalistic_merits = {}
    a.clickbait = None

def _extract_clickbait(data: dict) -> Optional[dict]:
    cb = data.get("clickbait")
    if not isinstance(cb, dict):
        rt = data.get("refined_title")
        if isinstance(rt, str) and rt.strip():
            return {
                "confidence": None,
                "explanation": None,
                "refined_title": rt.strip()
            }
        return None
    conf = _coerce_float_0_1(cb.get("confidence"))
    exp = cb.get("explanation") if isinstance(cb.get("explanation"), str) and cb.get("explanation").strip() else None
    rt = cb.get("refined_title") if isinstance(cb.get("refined_title"), str) and cb.get("refined_title").strip() else None
    if conf is None and not exp and not rt:
        return None
    return {
        "confidence": conf,
        "explanation": exp.strip() if isinstance(exp, str) else None,
        "refined_title": rt.strip() if isinstance(rt, str) else None
    }

# C. 強化：容忍字串形式的 reporting_style，先包裝成 list 再過濾
def _extract_reporting_style(data: dict) -> List[str]:
    rs = data.get("reporting_style", [])
    if isinstance(rs, str) and rs.strip():
        rs = [rs.strip()]
    if not isinstance(rs, list):
        return []
    allowed = set(ALLOWED_TAGS["reporting_style"])
    return [t for t in rs if isinstance(t, str) and t in allowed]

def _extract_reporting_intention(data: dict) -> List[str]:
    ri = data.get("reporting_intention", [])
    if not isinstance(ri, list):
        return []
    out = []
    for x in ri:
        if isinstance(x, (str, int, float)):
            sx = str(x).strip()
            sx = sx.strip().strip("「」\"'")
            if sx:
                out.append(sx[:10])
        if len(out) >= 3:
            break
    return out

def _extract_tagged_section(
    data: dict,
    key: str,
    allowed_set: set
) -> Dict[str, AssessmentItem]:
    raw = data.get(key, {})
    out: Dict[str, AssessmentItem] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        clean_key = _clean_key(k)
        if clean_key not in allowed_set:
            continue
        # 不允許「clickbait」作為劣勢標籤透過
        if clean_key.lower() == "clickbait":
            continue
        desc = v.get("description", "")
        deg = v.get("degree", "")
        if isinstance(desc, str) and desc.strip():
            if isinstance(deg, str) and deg.strip().lower() == "not applicable":
                continue
            out[clean_key] = {
                "description": desc.strip(),
                "degree": _normalize_degree(deg)
            }
    return out

def validate_schema(d: dict) -> Optional[str]:
    if "clickbait" not in d or not isinstance(d["clickbait"], dict):
        return "missing 'clickbait' object"
    cb = d["clickbait"]
    if not isinstance(cb.get("refined_title"), str) or not cb["refined_title"].strip():
        return "missing 'clickbait.refined_title'"
    conf = _coerce_float_0_1(cb.get("confidence"))
    if conf is None:
        return "invalid 'clickbait.confidence' (must be 0..1 number)"
    if "reporting_style" in d and not isinstance(d["reporting_style"], list):
        return "'reporting_style' must be a list"
    if "reporting_intention" in d and not isinstance(d["reporting_intention"], list):
        return "'reporting_intention' must be a list"
    for k in ("journalistic_demerits", "journalistic_merits"):
        if k in d and not isinstance(d[k], dict):
            return f"'{k}' must be an object"
    return None

# --- Disable clickbait detection switch (kept) ---
DISABLE_CLICKBAIT_DETECTION = os.getenv("DISABLE_CLICKBAIT_DETECTION", "true").lower() in ("1", "true", "yes")

def _force_no_clickbait(article: NewsEntity):
    refined = getattr(article, "refined_title", None) or getattr(article, "title", None) or ""
    article.clickbait = {
        "confidence": 0.00,
        "explanation": "未檢出標題黨元素。",
        "refined_title": refined.strip() or "（無標題）"
    }

# ---------- Main ----------
async def classify_article(article: NewsEntity, max_retries: int = 3):
    print("🌈 classifying the news:", getattr(article, "url", None))
    _set_empty_fields(article)

    content = article.content or ""
    user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON 分析結果：

--- ARTICLE START ---
{traditionalChineseUtil.safeTranslateIntoTraditionalChinese(content)}
--- ARTICLE END ---
"""

    delay = 0.8
    for attempt in range(max_retries):
        try:
            chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt.strip()]}])
            response = chat.send_message(user_prompt.strip())
            print("✅ Got an LLM response")

            # Parse and sanitize JSON
            try:
                data = safe_parse_json(response.text)
            except Exception as parse_err:
                msg = str(parse_err)
                if _is_retriable_error_msg(msg) and attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 6.0)
                    continue
                print("⚠️ Failed to parse JSON:", parse_err)
                return {"ok": False, "error": f"parse_error: {msg}"}

            if not isinstance(data, dict):
                return {"ok": False, "error": "parse_error: model output is not a JSON object"}

            # A. 在 validate_schema 前先寬鬆正規化 reporting_style
            rs_pre = data.get("reporting_style")
            if isinstance(rs_pre, str) and rs_pre.strip():
                data["reporting_style"] = [rs_pre.strip()]
            elif rs_pre is None:
                data["reporting_style"] = []

            # Strict schema validation before extraction
            schema_err = validate_schema(data)
            if schema_err:
                # Allow one retry if schema invalid and attempts remain
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 6.0)
                    continue
                return {"ok": False, "error": f"parse_error: {schema_err}"}

            # Extract sections
            clickbait_obj = _extract_clickbait(data)
            reporting_style_out = _extract_reporting_style(data)  # C. 增強後的 extractor
            reporting_intention_out = _extract_reporting_intention(data)
            journalistic_demerits_out = _extract_tagged_section(
                data, "journalistic_demerits", _CLEAN_ALLOWED_DEMERITS
            )
            journalistic_merits_out = _extract_tagged_section(
                data, "journalistic_merits", _CLEAN_ALLOWED_MERITS
            )

            # Strict validation for clickbait JSON (since schema requires a JSONB)
            if not clickbait_obj or not isinstance(clickbait_obj, dict):
                return {"ok": False, "error": "parse_error: missing or invalid 'clickbait' object"}
            if not clickbait_obj.get("refined_title"):
                return {"ok": False, "error": "parse_error: missing clickbait.refined_title"}

            # Normalize confidence to float or None
            if "confidence" in clickbait_obj:
                clickbait_obj["confidence"] = _coerce_float_0_1(clickbait_obj["confidence"])

            # Truncate explanation if extremely long (defensive)
            if isinstance(clickbait_obj.get("explanation"), str):
                clickbait_obj["explanation"] = clickbait_obj["explanation"].strip()

            # Attach to the article
            article.clickbait = clickbait_obj
            article.refined_title = clickbait_obj.get("refined_title")
            article.reporting_style = reporting_style_out
            article.reporting_intention = reporting_intention_out
            article.journalistic_demerits = journalistic_demerits_out
            article.journalistic_merits = journalistic_merits_out

            # Optional: Together headline augmentation (kept but disabled by default)
            """
            if getattr(article, "title", None):
                together_cb = get_clickbait_data_from_together(article.title)
                if together_cb:
                    article.clickbait.update({k: v for k, v in together_cb.items() if v is not None})
                    if together_cb.get("refined_title"):
                        article.refined_title = together_cb["refined_title"]
            """

            # Enforce: Do not detect clickbait (per request)
            if DISABLE_CLICKBAIT_DETECTION:
                _force_no_clickbait(article)

            print("🥳 Successfully attached data to the article")
            return {"ok": True}

        except Exception as e:
            msg = str(e)
            if _is_retriable_error_msg(msg) and attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 6.0)
                continue
            print("⚠️ Classification error (final):", e)
            return {"ok": False, "error": msg}

async def classify_articles(articles: List[NewsEntity]):
    tasks = [classify_article(article) for article in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results