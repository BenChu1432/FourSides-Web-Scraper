import asyncio
import re
from typing import Dict, List, Optional
from together import Together
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from app.modals.newsEntity import NewsEntity
from scrapers.news import AssessmentItem
import random
from util import traditionalChineseUtil

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-flash-lite") 

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
    "journalistic_demerits":[
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
        "**traditional_values_shield**（主張傳統價值作擋箭牌）",
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
reporting_style = "\n".join([f"- {tag}" for tag in ALLOWED_TAGS["reporting_style"]])

# political standing
system_prompt = f"""
你是一位新聞分析助理，專門負責判斷新聞文章中多大程度上存在以下特定的新聞優點和誤導性報導技術，並針對每一項提供清楚、有根據的說明。

---

1.若文章標題包含「標題黨／聳動」特徵（如誇張形容、恐嚇性措辭、過度絕對化、賣關子語句），請在輸出 JSON 的最上層加入 "refined_title" 欄位，提供一個更準確、克制且與內文一致的標題；若無此問題，"refined_title" 請填 null。請以繁體中文撰寫 refined_title。

2.請依據以下兩組標籤進行分析：

2a.### 📌 誤導手法（journalistic demerits）
這些是可能誤導讀者的報導技術，只標示有關或出現過的：

{misguiding_tools_list}

2b.### 📌 新聞優點（journalistic merits）
這些是能提升新聞品質的特徵，請判斷是否有具體體現：

{journalistic_merits_list}

3.### 📌 新聞報道風格（reporting styles）
{reporting_style}

4.### 📌 新聞報道目的（reporting intention）
自由發揮
---

### ⚠️ 請注意：
- **僅列出實際在文章中出現的標籤**（無論是誤導工具或新聞價值特徵）。
- 每一項標註請提供具體描述與評估程度，並引用文章中的字詞、句子或段落作為依據。
- 只顯示適用的誤導手法（journalistic demerits）和新聞優點（journalistic merits）, 但必須顯示"refined_title", 新聞報道風格（reporting styles）和新聞報道目的（reporting intention）
- 輸出範例格式必須為標準 JSON，直接輸出純 JSON 結構，不需要額外包裝在 content 欄位下。

---
{{
  "refined_title": "若需要修訂則填入修訂後標題；否則為 null",
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
  "reporting_style": [選用適用的報道風格, ...],
  "reporting_intention": [用最多10字準確指出1-3個報道目的和用意, ...],
}}
"""

print("system_prompt:",system_prompt)


def safe_parse_json(content: str):
    # 嘗試從 markdown 格式中提取純 JSON 區塊
    match = re.search(r"```json\s*([\s\S]+?)\s*```", content)
    if not match:
        # 若無 markdown 標記，直接從第一個 { 開始
        match = re.search(r"\{[\s\S]+", content)
        if not match:
            raise ValueError("⚠️ 無法找到 JSON 區塊")
    try:
        json_str = match.group(1) if "```" in match.group(0) else match.group(0)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("❌ JSON decode error at character:", e.pos)
        print("content:",content)
        print("json_str:",json_str)
        print("⛔ 問題附近內容：", json_str[e.pos - 30:e.pos + 30])
        raise

def _set_empty_fields(a):
    a.refined_title = None
    a.reporting_style = []
    a.reporting_intention = []
    a.journalistic_demerits = {}
    a.journalistic_merits = {}

def _is_retriable_error_msg(msg: str) -> bool:
    # Based on Gemini troubleshooting guide: 500 INTERNAL, 503 UNAVAILABLE, 504 DEADLINE_EXCEEDED
    # Also handle common wording
    msg = (msg or "").upper()
    retriable_tokens = ("500", "503", "504", "INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "TIMEOUT")
    return any(tok in msg for tok in retriable_tokens)

async def classify_article(article: NewsEntity, max_retries: int = 3):
    print("🌈 classifying the news:", article.url)

    # Prefill defaults so downstream never breaks
    _set_empty_fields(article)

    # Optional: truncate to mitigate deadline/exceeded and 500 due to very long context
    content = article.content or ""

    user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON 分析結果:

--- ARTICLE START ---
{traditionalChineseUtil.safeTranslateIntoTraditionalChinese(content)}
--- ARTICLE END ---
"""

    delay = 0.8  # backoff starting delay
    for attempt in range(max_retries):
        try:
            chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt.strip()]}])
            # Set a timeout so calls don't hang forever (504 guidance: increase timeout if needed)
            response = chat.send_message(user_prompt.strip())
            print("✅ Gotten an LLM response")

            try:
                data = safe_parse_json(response.text)
            except Exception as parse_err:
                # Parsing error isn't a backend 500/503/504; treat as non-retriable unless model hinted at a service issue
                msg = str(parse_err)
                if _is_retriable_error_msg(msg) and attempt < max_retries - 1:
                    await asyncio.sleep(delay + random.random() * 0.5)
                    delay *= 2
                    continue
                print("⚠️ Failed to parse JSON:", parse_err)
                return {"ok": False, "error": f"parse_error: {msg}"}

            if not isinstance(data, dict):
                return {"ok": False, "error": "parse_error: model output is not a JSON object"}

            # Initialize locals
            refined_title: Optional[str] = None
            reporting_style_out: List[str] = []
            reporting_intention_out: List[str] = []
            journalistic_demerits_out: Dict[str, AssessmentItem] = {}
            journalistic_merits_out: Dict[str, AssessmentItem] = {}

            def _normalize_degree(val: str) -> str:
                allowed = {"low", "moderate", "high"}
                return val.lower() if isinstance(val, str) and val.lower() in allowed else "low"

            # refined_title
            rt = data.get("refined_title")
            refined_title = rt.strip() if isinstance(rt, str) and rt.strip() else None

            # reporting_style
            rs = data.get("reporting_style", [])
            if isinstance(rs, list):
                reporting_style_out = [t for t in rs if isinstance(t, str) and t in ALLOWED_TAGS["reporting_style"]]

            # reporting_intention
            ri = data.get("reporting_intention", [])
            if isinstance(ri, list):
                reporting_intention_out = [str(x).strip() for x in ri if isinstance(x, (str, int, float))][:3]

            # journalistic_demerits
            jd = data.get("journalistic_demerits", {})
            if isinstance(jd, dict):
                clean_allowed = set()
                for t in ALLOWED_TAGS["journalistic_demerits"]:
                    clean = t.split("**")[1].strip() if t.startswith("**") and "**" in t[2:] else t
                    clean = clean.replace("（", " ").replace("）", " ").strip().split()[0]
                    clean_allowed.add(clean)
                for key, item in jd.items():
                    clean_key = key.strip("* ").split("**")[-1] if "**" in key else key.strip()
                    clean_key = clean_key.replace("（", " ").replace("）", " ").strip().split()[0]
                    if clean_key in clean_allowed and isinstance(item, dict):
                        desc = item.get("description", "")
                        deg = item.get("degree", "")
                        if isinstance(desc, str) and desc.strip():
                            if isinstance(deg, str) and deg.lower() == "not applicable":
                                continue
                            journalistic_demerits_out[clean_key] = {
                                "description": desc.strip(),
                                "degree": _normalize_degree(deg)
                            }

            # journalistic_merits
            jm = data.get("journalistic_merits", {})
            if isinstance(jm, dict):
                clean_allowed = set()
                for t in ALLOWED_TAGS["journalistic_merits"]:
                    clean = t.split("**")[1].strip() if t.startswith("**") and "**" in t[2:] else t
                    clean = clean.replace("（", " ").replace("）", " ").strip().split()[0]
                    clean_allowed.add(clean)
                for key, item in jm.items():
                    clean_key = key.strip("* ").split("**")[-1] if "**" in key else key.strip()
                    clean_key = clean_key.replace("（", " ").replace("）", " ").strip().split()[0]
                    if clean_key in clean_allowed and isinstance(item, dict):
                        desc = item.get("description", "")
                        deg = item.get("degree", "")
                        if isinstance(desc, str) and desc.strip():
                            if isinstance(deg, str) and deg.lower() == "not applicable":
                                continue
                            journalistic_merits_out[clean_key] = {
                                "description": desc.strip(),
                                "degree": _normalize_degree(deg)
                            }

            # Attach to the article
            article.refined_title = refined_title
            article.reporting_style = reporting_style_out
            article.reporting_intention = reporting_intention_out
            article.journalistic_demerits = journalistic_demerits_out
            article.journalistic_merits = journalistic_merits_out

            print("🥳 Successfully attached data to the article")
            return {"ok": True}

        except Exception as e:
            msg = str(e)
            if _is_retriable_error_msg(msg) and attempt < max_retries - 1:
                await asyncio.sleep(delay + random.random() * 0.5)
                delay *= 2
                continue
            # Per Gemini troubleshooting guide:
            # - 500 INTERNAL: unexpected error -> reduce input or switch model; retry already attempted
            # - 503 UNAVAILABLE: service overloaded -> retry already attempted
            # - 504 DEADLINE_EXCEEDED: increase timeout -> we used 60s; consider higher if needed
            print("⚠️ Classification error (final):", e)
            return {"ok": False, "error": msg}

async def classify_articles(articles: List[NewsEntity]):
    tasks = [classify_article(article) for article in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results