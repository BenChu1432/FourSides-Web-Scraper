from together import Together
import json
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import asyncio
from contextlib import asynccontextmanager
from openai import AsyncAzureOpenAI
from app.modals.newsEntity import NewsEntity

load_dotenv()

# ---------------- Azure OpenAI Config ----------------
TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")

if not TOGETHER_AI_API_KEY:
    raise ValueError("Please set TOGETHER_AI_API_KEY in your environment.")

# One-time client
client = Together(api_key=TOGETHER_AI_API_KEY)

# Concurrency limiter (tune this for your quota)
LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "8"))
_llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)

# Optional: strict JSON response (supported on 2024-06-01+ and newer models)
RESPONSE_FORMAT = {"type": "json_object"}


# LLAMA:meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
# Alibaba: Qwen/Qwen2.5-7B-Instruct-Turbo

def _normalize_key(k: str) -> str:
    # Map fancy tags like "**decontextualisation**（...）" to simple slug keys
    k = k.strip().lower()
    # strip markdown asterisks and Chinese annotations
    k = k.replace("**", "")
    k = k.split("（")[0].strip()
    k = k.replace(" ", "_").replace("-", "_")
    return k

def _empty_analysis():
    return {
    "refined_title": None,
    "journalistic_demerits": {},
    "journalistic_merits": {},
    "reporting_style": [],
    "reporting_intention": [],
    "error": "Failed to parse model output"
    }

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
        "**timely_relevance_and_timeless_insight**（報道具時效性和長遠啟發性）",
        "**inclusive_language** (包容性語言)",
        "**representation_of_marginalized_groups** (弱勢群體有呈現)",
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
        "**nationalistic_framing**（民族主義框架）",
        "**corporate_glorification**（企業美化）",
        "**overemphasis_on_glory**（過度強調成就）",
        "**propagandistic_tone**（大外宣語調）",
        "**overuse_of_statistics_without_verification**（數據濫用或未驗證）",
        "**no_critical_inquiry_or_accountability**（缺乏批判與責任追究）",
        "**strategic_omission**（策略性忽略）",
        "**anonymous_authority**（不具名權威）",
        "**disproportionate_amplification_of_minor_incidents**（次要事件的過度放大）",
        "**victimhood_framing**（受害者框架）",
        "**heroic_framing**（英雄敘事）",
        "**binary_framing**（非黑即白敘事）",
        "**moral_judgment_framing**（道德判斷包裝）",
        "**cultural_essentialism**（文化本質論）",
        "**traditional_values_shield**（主張傳統價值作擋箭牌）",
        "**pre_criminal_framing**（預設有罪）"
        "**whataboutism**（那又怎麼辦主義）"
        "**pseudo_expertise** (引用非專業人士作為權威)"
        "**overpersonalisation** (過度強調個人責任，忽視結構性問題)",
        "**false_balance**（虛假平衡）"
        "**false_equivalence**（錯誤類比）",
        "**echoing_government_or_corporate_press_releases**（僅重複官方說法）",
        "**narrative_over_facts**（敘事主導，事實退位）"
    ],
    "reporting_style": [
        "he_said_she_said_reporting", "propagandistic_reporting", "investigative_reporting",
        "solutions_journalism", "feature_reporting", "advocacy_journalism", 
        "opinion_reporting", "sensationalist_reporting", "stenographic_reporting",
        "data_journalism", "explanatory_reporting"
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

---

### 請針對每一項誤導工具，依下列格式輸出：
{{
  "refined_title": "若需要修訂則填入修訂後標題；否則為 null",
  "journalistic_demerits": {{
    "decontextualisation": {{
      "description": "請用繁體中文具體詳細描述該誤導技術在文章中是否出現，以及用文章中的具體用詞解釋出現的方式、程度與語境，並需要準確引用人、物和事說明。",
      "degree": "not applicable / low / moderate / high"
    }},
    ...
  }},
  "journalistic_merits": {{
    "multiple_perspectives": {{
      "description": "請用繁體中文具體詳細描述該新聞優點在文章中是否出現，以及用文章中的具體用詞解釋出現的方式、程度與語境，並需要準確引用人、物和事明。",
      "degree": "not applicable / low / moderate / high"
    }},
    ...
  }},
  "reporting_style": [選用適用的報道風格, ...],
  "reporting_intention": [簡短準確指出1-3個報道目的和用意, ...],
}}
"""

async def classifiy_article(article: NewsEntity):
    user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON 分析結果:

--- ARTICLE START ---
標題：{article.title}
內文: {article.content}
--- ARTICLE END ---
"""

    async with _llm_semaphore:
        print("⭐️ Trying to call the API!")
        try:
            response = client.chat.completions.create(
                model="Qwen/Qwen3-235B-A22B-Instruct-2507-tput",
                messages=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": user_prompt.strip()}
                ],
                temperature=0.6
            )
            print("response:",response)
            content = response.choices[0].message.content
            if not content or not isinstance(content, str) or not content.strip():
                raise ValueError("Empty content from LLM")
        except Exception as e:
            print("LLM call failed or empty content:", repr(e))
            data = _empty_analysis()
        else:
            try:
                data = json.loads(content)
                if not isinstance(data, dict):
                    # Some models may wrap in a list; salvage first object
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        data = data[0]
                    else:
                        raise ValueError("Parsed JSON is not an object")
            except Exception as parse_err:
                # Last-resort salvage
                try:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    candidate = content[start:end] if (start != -1 and end > start) else "{}"
                    data = json.loads(candidate)
                    if not isinstance(data, dict):
                        raise ValueError("Salvaged JSON is not an object")
                except Exception:
                    print("⚠️ Failed to parse JSON. Raw output:")
                    print(content)
                    print("Parse error:", repr(parse_err))
                    data = _empty_analysis()

    # Post-processing defaults
    if not isinstance(data, dict):
        data = _empty_analysis()

    print("data:",data)
    data.setdefault("refined_title", None)
    data.setdefault("journalistic_demerits", {})
    data.setdefault("journalistic_merits", {})
    data.setdefault("reporting_style", [])
    data.setdefault("reporting_intention", [])

    def _standardize_section(section_dict):
        out = {}
        if not isinstance(section_dict, dict):
            section_dict = {}
        for k, v in section_dict.items():
            key = _normalize_key(k if isinstance(k, str) else str(k))
            v = v or {}
            desc = (v.get("description") or "").strip()
            degree = (v.get("degree") or "").strip().lower()
            if degree not in {"not applicable", "low", "moderate", "high"}:
                degree = "not applicable" if not desc else "low"
            out[key] = {"description": desc, "degree": degree}
        return out

    data["journalistic_demerits"] = _standardize_section(data.get("journalistic_demerits"))
    data["journalistic_merits"] = _standardize_section(data.get("journalistic_merits"))

    def _as_str_list(x):
        if x is None:
            return []
        if isinstance(x, str):
            s = x.strip()
            return [s] if s else []
        if isinstance(x, list):
            out = []
            for i in x:
                s = str(i).strip()
                if s:
                    out.append(s)
            return out
        # Some models return dict with boolean flags; flatten truthy keys
        if isinstance(x, dict):
            return [str(k) for k, v in x.items() if v]
        return []

    data["reporting_style"] = _as_str_list(data.get("reporting_style"))
    data["reporting_intention"] = _as_str_list(data.get("reporting_intention"))

    # Update entity safely
    if isinstance(article, NewsEntity):
        refined_title = data.get("refined_title")
        article.refined_title = refined_title.strip() if isinstance(refined_title, str) and refined_title.strip() else None

        if hasattr(article, "journalistic_demerits"):
            article.journalistic_demerits = data["journalistic_demerits"]
        if hasattr(article, "journalistic_merits"):
            article.journalistic_merits = data["journalistic_merits"]
        if hasattr(article, "reporting_style"):
            article.reporting_style = list(data["reporting_style"])  # ensure list
        if hasattr(article, "reporting_intention"):
            article.reporting_intention = list(data["reporting_intention"])

    return dict(data)