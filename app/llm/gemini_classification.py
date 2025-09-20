import os
import asyncio
from typing import Any, Dict, List, Optional, Tuple
import google.generativeai as genai

from util.jsonSanitize import safe_parse_json, is_retriable_error_msg
from scrapers.news import AssessmentItem

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

def _build_clean_allowed_set(raw_tags):
    clean = set()
    for t in raw_tags:
        core = t.split("**")[1].strip() if (isinstance(t, str) and t.startswith("**") and t.count("**") >= 2) else t
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
    return k.replace("（", " ").replace("）", " ").strip()

def _normalize_degree(val: str) -> str:
    if not isinstance(val, str):
        return "low"
    v = val.strip().lower()
    return v if v in {"low", "moderate", "high"} else "low"

def _coerce_float_0_1(x) -> Optional[float]:
    try:
        f = float(x)
        f = 0.0 if f < 0 else (1.0 if f > 1 else f)
        return round(f, 2)
    except Exception:
        return None

system_prompt_template = """
你是一位新聞分析助理，專門負責判斷新聞文章中多大程度上存在以下特定的新聞優點和誤導性報導技術，並針對每一項提供清楚、有根據的說明。

---

1.請依據以下兩組標籤進行分析：

1a.### 📌 誤導手法（journalistic_demerits）
這些是可能誤導讀者的報導技術，只標示有關或出現過的：

{misguiding_tools_list}

1b.### 📌 新聞優點（journalistic_merits）
這些是能提升新聞品質的特徵，請判斷是否有具體體現：

{journalistic_merits_list}

2.### 📌 新聞報道風格（reporting_style）
{reporting_style_list}

3.### 📌 新聞報道目的（reporting_intention）
自由發揮，請用最多10字指出1-3個報道目的。

---

### ⚠️ 請注意：
- **僅列出實際在文章中出現的標籤**（無論是誤導工具或新聞價值特徵）。
- 每一項標註請提供具體描述與評估程度，並引用文章中的字詞、句子或段落作為依據。
- 請輸出以下格式的標準 JSON，不要包含 Markdown 或其他說明文字。
- 請依據出現頻率、語氣強度、篇幅比重與對讀者影響，判斷每個標籤的程度（degree），並使用以下分級：
  - low：僅出現一次或語氣輕微，對整體影響極低。
  - moderate：中等頻率或篇幅，對報導理解造成明顯影響。
  - high：反覆出現或為主導敘事，顯著影響報導客觀性與判斷。

---
{{
  "journalistic_demerits": {{
    "decontextualisation": {{
      "description": "請用繁體中文具體詳細描述該誤導技術在文章中是否出現，以及用文章中的具體用詞解釋出現的方式、程度與語境，並需要準確引用人、物和事說明。",
      "degree": "low / moderate / high"
    }},
    ...
  }},
  "journalistic_merits": {{
    "multiple_perspectives": {{
      "description": "請用繁體中文具體詳細描述該新聞優點在文章中是否出現，以及用文章中的具體用詞解釋出現的方式、程度與語境，並需要準確引用人、物和事明。",
      "degree": "low / moderate / high"
    }},
    ...
  }},
  "reporting_style": ["選用適用的報道風格", ...],
  "reporting_intention": ["用最多10字指出報道目的", ...]
}}
"""

def _lists_for_prompt():
    jm = "\n".join([f"- {t}" for t in ALLOWED_TAGS["journalistic_merits"]])
    jd = "\n".join([f"- {t}" for t in ALLOWED_TAGS["journalistic_demerits"]])
    rs = "\n".join([f"- {t}" for t in ALLOWED_TAGS["reporting_style"]])
    return jm, jd, rs

class GeminiArticleClassifier:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite"))
        jm, jd, rs = _lists_for_prompt()
        self.system_prompt = system_prompt_template.format(
            misguiding_tools_list=jd,
            journalistic_merits_list=jm,
            reporting_style_list=rs
        )

    async def analyze(self, article_text: str, max_retries: int = 3) -> Dict[str, Any]:
        delay = 0.8
        user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON 分析結果：

--- ARTICLE START ---
{article_text.strip()}
--- ARTICLE END ---
"""
        for attempt in range(max_retries):
            try:
                chat = self.model.start_chat(history=[{"role": "user", "parts": [self.system_prompt.strip()]}])
                response = chat.send_message(user_prompt.strip())
                data = safe_parse_json(response.text)
                return data
            except Exception as e:
                msg = str(e)
                if is_retriable_error_msg(msg) and attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 6.0)
                    continue
                raise

    # Extraction helpers exposed so the service layer can reuse consistent logic
    def extract_clickbait(self, data: dict) -> Optional[dict]:
        cb = data.get("clickbait")
        if not isinstance(cb, dict):
            rt = data.get("refined_title")
            if isinstance(rt, str) and rt.strip():
                return {"confidence": None, "explanation": None, "refined_title": rt.strip()}
            return None
        conf = self._coerce_float_0_1(cb.get("confidence"))
        exp = cb.get("explanation") if isinstance(cb.get("explanation"), str) and cb.get("explanation").strip() else None
        rt = cb.get("refined_title") if isinstance(cb.get("refined_title"), str) and cb.get("refined_title").strip() else None
        if conf is None and not exp and not rt:
            return None
        return {"confidence": conf, "explanation": exp.strip() if exp else None, "refined_title": rt.strip() if rt else None}

    def extract_reporting_style(self, data: dict) -> List[str]:
        rs = data.get("reporting_style", [])
        if not isinstance(rs, list):
            return []
        allowed = set(ALLOWED_TAGS["reporting_style"])
        return [t for t in rs if isinstance(t, str) and t in allowed]

    def extract_reporting_intention(self, data: dict) -> List[str]:
        ri = data.get("reporting_intention", [])
        if not isinstance(ri, list):
            return []
        out = []
        for x in ri:
            if isinstance(x, (str, int, float)):
                sx = str(x).strip().strip("「」\"'")
                if sx:
                    out.append(sx[:10])
            if len(out) >= 3:
                break
        return out

    def extract_tagged_section(self, data: dict, key: str) -> Dict[str, AssessmentItem]:
        raw = data.get(key, {})
        out: Dict[str, AssessmentItem] = {}
        if not isinstance(raw, dict):
            return out
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            clean_key = _clean_key(k)
            if key == "journalistic_demerits" and clean_key.lower() == "clickbait":
                # Allow service layer to decide; default keeps it. Service may strip.
                pass
            if clean_key not in _CLEAN_ALLOWED_DEMERITS.union(_CLEAN_ALLOWED_MERITS):
                # Only accept allowed tags
                if key == "journalistic_demerits" and clean_key not in _CLEAN_ALLOWED_DEMERITS:
                    continue
                if key == "journalistic_merits" and clean_key not in _CLEAN_ALLOWED_MERITS:
                    continue
            desc = v.get("description", "")
            deg = v.get("degree", "")
            if isinstance(desc, str) and desc.strip():
                if isinstance(deg, str) and deg.strip().lower() == "not applicable":
                    continue
                out[clean_key] = {"description": desc.strip(), "degree": _normalize_degree(deg)}
        return out

    def validate_schema(self, d: dict) -> Optional[str]:
        if "reporting_style" in d and not isinstance(d["reporting_style"], list):
            return "'reporting_style' must be a list"
        if "reporting_intention" in d and not isinstance(d["reporting_intention"], list):
            return "'reporting_intention' must be a list"
        for k in ("journalistic_demerits", "journalistic_merits"):
            if k in d and not isinstance(d[k], dict):
                return f"'{k}' must be an object"
        return None

    @staticmethod
    def _coerce_float_0_1(x) -> Optional[float]:
        try:
            f = float(x)
            f = 0.0 if f < 0 else (1.0 if f > 1 else f)
            return round(f, 2)
        except Exception:
            return None