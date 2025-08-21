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

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-flash-lite")  # or replace with latest model name
# LLAMA:meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
# Alibaba: Qwen/Qwen2.5-7B-Instruct-Turbo

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
        "**pre-criminal_framing**（預設有罪）"
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
        "explanatory_reporting"
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
  "reporting_intention": [簡短準確指出1-3個報道目的和用意, ...],
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
        print("⛔ 問題附近內容：", json_str[e.pos - 30:e.pos + 30])
        raise

async def classify_article(article: NewsEntity):
    print("🌈 classifying the news:",article.url)
    user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON 分析結果:

--- ARTICLE START ---
{article.content}
--- ARTICLE END ---
"""

    chat = model.start_chat(history=[
        {"role": "user", "parts": [system_prompt.strip()]},
        ])
    response = chat.send_message(user_prompt.strip())
    print("✅ Gotten an LLM response")
    try:
        content = safe_parse_json(response.text)
        print("content:",content)
        print("✅ Safely parsed the text")
    except Exception as e:
        print("⚠️ Failed to parse the json:", e)
        return None

    # Initialize safe defaults
    refined_title: Optional[str] = None
    reporting_style_out: List[str] = []
    reporting_intention_out: List[str] = []
    journalistic_demerits_out: Dict[str, AssessmentItem] = {}
    journalistic_merits_out: Dict[str, AssessmentItem] = {}

    def _normalize_degree(val: str) -> str:
        # Accept only your Degree literal, fallback to "low" if invalid
        allowed = {"low", "moderate", "high"}
        if isinstance(val, str) and val.lower() in allowed:
            return val.lower()
        # If model outputs "not applicable", just skip the item later (we only keep appeared tags)
        return "low"

    data = content
    if not isinstance(data, dict):
        print("⚠️ Parsed content is not a dict. Raw output:")
        print(content)
        return None
    # refined_title
    rt = data.get("refined_title", None)
    print("rt:",rt)
    if isinstance(rt, str) and rt.strip():
        refined_title = rt.strip()
        print("✅ Successfully parsed the refined_title")
    else:
        refined_title = None

    # reporting_style (only keep allowed tags and ensure list[str])
    rs = data.get("reporting_style", [])
    print("rs:",rs)
    if isinstance(rs, list):
        reporting_style_out = [
            t for t in rs
            if isinstance(t, str) and t in ALLOWED_TAGS["reporting_style"]
        ]
        print("✅ Successfully parsed the reporting_style")

    # reporting_intention (ensure list[str], keep short)
    ri = data.get("reporting_intention", [])
    print("ri:",ri)
    if isinstance(ri, list):
        reporting_intention_out = [str(x).strip() for x in ri if isinstance(x, (str, int, float))]
        # Optionally limit to 3
        reporting_intention_out = reporting_intention_out[:3]
        print("✅ Successfully parsed the reporting_intention")

    # journalistic_demerits: keep only tags that appear and have valid structure
    jd = data.get("journalistic_demerits", {})
    print("jd:",jd)
    if isinstance(jd, dict):
        for key, item in jd.items():
            # Map keys that may come with **bold** or localized text to canonical key
            # We accept the canonical english snake_case keys from ALLOWED_TAGS
            canonical_keys = [t.split("**")[1] if t.startswith("**") else t for t in ALLOWED_TAGS["journalistic_demerits"]]
            # Build a map of clean_key -> allowed
            clean_allowed = set()
            for t in ALLOWED_TAGS["journalistic_demerits"]:
                # t is like "**decontextualisation**（…）"
                # extract between ** if present
                if t.startswith("**") and "**" in t[2:]:
                    clean = t.split("**")[1].strip()
                else:
                    clean = t
                # ensure final clean is like decontextualisation
                clean = clean.replace("（", " ").replace("）", " ").strip()
                # take first token till space or parenthesis
                clean = clean.split()[0]
                clean_allowed.add(clean)

            clean_key = key.strip("* ").split("**")[-1] if "**" in key else key.strip()
            clean_key = clean_key.replace("（", " ").replace("）", " ").strip().split()[0]

            if clean_key in clean_allowed and isinstance(item, dict):
                desc = item.get("description", "")
                deg = item.get("degree", "").lower() if isinstance(item.get("degree"), str) else ""
                # Skip "not applicable" or empty descriptions
                if isinstance(desc, str) and desc.strip():
                    if deg == "not applicable":
                        continue
                    journalistic_demerits_out[clean_key] = {
                        "description": desc.strip(),
                        "degree": _normalize_degree(deg)
                    }
        print("✅ Successfully parsed the journalistic_demerits")

    # journalistic_merits: same normalization
    jm = data.get("journalistic_merits", {})
    print("jm:",jm)
    if isinstance(jm, dict):
        clean_allowed = set()
        for t in ALLOWED_TAGS["journalistic_merits"]:
            # similar extraction
            if t.startswith("**") and "**" in t[2:]:
                clean = t.split("**")[1].strip()
            else:
                clean = t
            clean = clean.replace("（", " ").replace("）", " ").strip()
            clean = clean.split()[0]
            clean_allowed.add(clean)

        for key, item in jm.items():
            clean_key = key.strip("* ").split("**")[-1] if "**" in key else key.strip()
            clean_key = clean_key.replace("（", " ").replace("）", " ").strip().split()[0]
            if clean_key in clean_allowed and isinstance(item, dict):
                desc = item.get("description", "")
                deg = item.get("degree", "").lower() if isinstance(item.get("degree"), str) else ""
                if isinstance(desc, str) and desc.strip():
                    if deg == "not applicable":
                        continue
                    journalistic_merits_out[clean_key] = {
                        "description": desc.strip(),
                        "degree": _normalize_degree(deg)
                    }
        print("✅ Successfully parsed the journalistic_merits")

    # Attach to article (NewsEntity should have these attributes)
    # If your NewsEntity uses different field names, adjust here
    try:
        article.refined_title = refined_title
        article.reporting_style = reporting_style_out
        article.reporting_intention = reporting_intention_out
        article.journalistic_demerits = journalistic_demerits_out
        article.journalistic_merits = journalistic_merits_out
        print("✅ Successfully attached data to the article")
    except Exception as e:
        print("⚠️ Failed to assign fields to article:", e)
    print("🥳 Successfully parsed everything!")
    return {
        "refined_title": refined_title,
        "reporting_style": reporting_style_out,
        "reporting_intention": reporting_intention_out,
        "journalistic_demerits": journalistic_demerits_out,
        "journalistic_merits": journalistic_merits_out
    }

async def classify_articles(articles: List[NewsEntity]):
    tasks = [classify_article(article) for article in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results