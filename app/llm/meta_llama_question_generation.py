import json
import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv
from together import Together

# External domain imports you mentioned
from app.modals.newsEntity import NewsEntity
from scrapers.news import AssessmentItem
from util import traditionalChineseUtil

load_dotenv()
TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
MODEL_TO_GENERATE_QUESTIONS = os.getenv("MODEL_TO_GENERATE_QUESTIONS") or "openai/gpt-oss-20b"


def _strip_control_chars(s: str) -> str:
    # Remove control characters except common whitespace
    return re.sub(r"[\x00-\x09\x0B-\x1F\x7F]", "", s)


def _find_json_codeblock(content: str) -> Optional[str]:
    """
    Try to extract JSON from common patterns:
    1) ```json ... ```
    2) ``` ... ```
    3) First top-level { ... } block in the content
    4) Fallback: if content itself looks like JSON
    """
    if not content:
        return None

    # Normalize line endings
    s = content.strip()

    # 1) ```json ... ```
    m = re.search(r"```json\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if candidate:
            return candidate

    # 2) ``` ... ```
    m = re.search(r"```\s*([\s\S]*?)```", s)
    if m:
        candidate = m.group(1).strip()
        # Heuristically prefer if it starts with { or [
        if candidate.startswith("{") or candidate.startswith("["):
            return candidate

    # 3) Try to locate the first top-level JSON object by brace matching
    # This is more robust against prose around the JSON.
    start_idx = s.find("{")
    if start_idx != -1:
        depth = 0
        for i in range(start_idx, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start_idx : i + 1]
                    return candidate

    # 4) Fallback: if entire content appears to be JSON-ish
    if s.startswith("{") and s.endswith("}"):
        return s

    return None


def _tolerant_quote_fix(s: str) -> str:
    # Fix patterns like: "explanation": ""金牌特務"林..."
    # Convert to: "explanation": "\"金牌特務\"林..."
    def repl(m):
        inner = m.group(1)
        # Escape any unescaped quotes inside
        inner_fixed = inner.replace(r'\"', '"')  # normalize any prior escaping
        inner_fixed = inner_fixed.replace('"', r'\"')
        return f'"explanation": "{inner_fixed}"'

    s = re.sub(
        r'"explanation"\s*:\s*"([^"]*?"[^"]*?[^\\])"',  # greedy enough to catch first pair of quotes
        repl,
        s,
        flags=re.DOTALL,
    )
    return s

def extract_json_from_content(content: str) -> Optional[dict]:
    try:
        if not content or not content.strip():
            print("❌ content 為空，無法解析 JSON")
            return None

        s = content.strip()

        # 1) Try ```json fenced block
        m = re.search(r"```json\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
        if m:
            json_str = m.group(1).strip()
        else:
            # 2) Try generic ``` fenced block that looks like JSON
            m = re.search(r"```\s*([\s\S]*?)```", s)
            if m and m.group(1).strip().startswith("{"):
                json_str = m.group(1).strip()
            else:
                # 3) Try to find the first complete top-level JSON object by brace depth
                start = s.find("{")
                json_str = None
                if start != -1:
                    depth = 0
                    for i in range(start, len(s)):
                        if s[i] == "{":
                            depth += 1
                        elif s[i] == "}":
                            depth -= 1
                            if depth == 0:
                                json_str = s[start:i+1]
                                break

                # 4) If still not found, and the whole content looks like JSON, use it
                if json_str is None and s.startswith("{") and s.endswith("}"):
                    json_str = s

                if json_str is None:
                    print("❌ 找不到 JSON 區塊")
                    print("🔎 Content preview:", s[:500])
                    return None

        # Cleanup control chars
        json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)
        # Remove common trailing commas
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        return json.loads(json_str)

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        # Guard against json_str maybe undefined in some paths
        try:
            print("🔎 JSON String that failed:", json_str[:1000])
        except Exception:
            pass
        return None


def validate_question_schema(obj: dict) -> Optional[str]:
    """
    Validate that the object has the required shape:
    {
      "question": str,
      "options": {"A": str, "B": str, "C": str, "D": str},
      "answer": "A"|"B"|"C"|"D",
      "explanation": str
    }
    Returns None if valid, else an error message.
    """
    if not isinstance(obj, dict):
        return "根節點不是物件"

    required_keys = ["question", "options", "answer", "explanation"]
    for k in required_keys:
        if k not in obj:
            return f"缺少必要欄位: {k}"

    if not isinstance(obj["question"], str) or not obj["question"].strip():
        return "question 應為非空字串"

    if not isinstance(obj["options"], dict):
        return "options 應為物件"
    for k in ["A", "B", "C", "D"]:
        if k not in obj["options"] or not isinstance(obj["options"][k], str) or not obj["options"][k].strip():
            return f"options.{k} 應為非空字串"

    if obj["answer"] not in ["A", "B", "C", "D"]:
        return "answer 必須為 A/B/C/D 之一"

    if not isinstance(obj["explanation"], str) or not obj["explanation"].strip():
        return "explanation 應為非空字串"

    return None


async def generate_question_for_article(article: NewsEntity) -> List[Dict]:
    article_text = article.content or ""
    client = Together(api_key=TOGETHER_AI_API_KEY)

    system_prompt = """
你是一位出題專家。請根據以下文章內容，設計一題選擇題，題目為「以下哪一項敘述是正確的？」，
需測驗讀者的細節理解與批判思考能力，並遵守以下規則：

1. 題目與選項避免過於直接或明顯，需細讀文章才能判斷。
2. 四個選項中，僅一個為根據文章內容可明確判定的「正確」敘述，其餘三項為「合理但錯誤」或「似是而非」。
3. 避免明確關鍵字（如精確人名、地名、數字）讓答案過於直觀。
4. 可使用模糊或間接語言（如「鄰近地區」、「數十人」、「可能」、「有傳言」等）。
5. 所有選項需與文章內容相關，避免離題或荒謬。
6. 僅輸出 JSON，格式如下：
{
  "question": "題目文字",
  "options": { "A": "選項A", "B": "選項B", "C": "選項C", "D": "選項D" },
  "answer": "四選項之一",
  "explanation": "僅用一段文字簡要說明為何每個答案正確、其他選項錯誤（必為單一字串，禁止為物件、陣列或多欄位）"
}

請使用繁體中文回答，不要輸出任何多餘文字或附加說明。
    """.strip()

    user_prompt = f"""請分析以下新聞文章，並依 system prompt 的格式與規則輸出結構化 JSON：

--- ARTICLE START ---
{traditionalChineseUtil.safeTranslateIntoTraditionalChinese(article_text)}
--- ARTICLE END ---
"""

    response = client.chat.completions.create(
        model=MODEL_TO_GENERATE_QUESTIONS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
    )

    content = response.choices[0].message.content
    print("LLM raw content:", content[:1000])

    parsed = extract_json_from_content(content)
    if not parsed:
        return []

    # Validate schema
    err = validate_question_schema(parsed)
    if err:
        print("❌ Schema validation failed:", err)
        print("🔎 Parsed object preview:", json.dumps(parsed, ensure_ascii=False)[:1000])
        return []

    # Optionally ensure answer key exists in options
    if parsed["answer"] not in parsed["options"]:
        print("❌ answer 不在 options 中")
        return []

    # Return as list to support future multi-question extension
    return [parsed]