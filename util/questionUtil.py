import random
from typing import List, Dict, Any

from app.modals.newsEntity import NewsEntity

# Assuming this mapping is defined somewhere, e.g., in a constants file or directly in the function
DEMERIT_TAG_DESCRIPTIONS = {
    "decontextualisation": "脫離上下文地引用",
    "clickbait": "使用聳動標題吸引點擊",
    "fear_mongering": "渲染恐懼情緒",
    "cherry_picking": "挑選有利資訊忽略其他觀點",
    "loaded_language": "使用情緒化語言",
    "conflation": "混淆不同概念",
    "lack_of_balance": "未呈現多方觀點",
    "overemphasis_on_profanity_and_insults": "過度強調辱罵與粗口",
    "social_media_amplification_trap": "過度依賴社群媒體熱度",
    "nationalistic_framing": "民族主義框架",
    "corporate_glorification": "過度讚揚企業",
    "overemphasis_on_glory": "過度強調榮耀",
    "propagandistic_tone": "宣傳性語氣",
    "overuse_of_statistics_without_verification": "過度使用未經驗證的數據",
    "no_critical_inquiry_or_accountability": "缺乏批判性提問或追責",
    "strategic_omission": "策略性遺漏重要資訊",
    "anonymous_authority": "引用不具名權威",
    "minor_incident_magnification": "放大微不足道事件",
    "victimhood_framing": "受害者敘事框架",
    "heroic_framing": "英雄敘事框架",
    "binary_framing": "非黑即白的敘事框架",
    "moral_judgment_framing": "帶有道德評判的框架",
    "cultural_essentialism": "文化本質主義",
    "traditional_values_shield": "以傳統價值作為護盾",
    "pre-criminal_framing": "預設犯罪傾向的敘事",
}

def generate_misleading_technique_question(article: NewsEntity) -> List[Dict[str, Any]]:
    """
    Generates a single multiple-choice question about a journalistic demerit
    based on the article's tagging data.
    """
    demerits = getattr(article, "journalistic_demerits", None) or {}
    print("demerits:",demerits)
    
    # Filter for demerits with a non-empty description
    tagged_demerits = {
        tag: detail for tag, detail in demerits.items()
        if detail and detail.get("description", "").strip()
    }

    if not tagged_demerits:
        return []

    # Choose one tagged demerit as the correct answer
    correct_tag = random.choice(list(tagged_demerits.keys()))
    correct_detail = tagged_demerits[correct_tag]
    correct_option_text = DEMERIT_TAG_DESCRIPTIONS.get(correct_tag, correct_tag)
    correct_explanation_text = correct_detail.get("description", "").strip()

    # Get distractor tags that are not present in the article
    all_tags = list(DEMERIT_TAG_DESCRIPTIONS.keys())
    distractor_tags = [tag for tag in all_tags if tag not in tagged_demerits and tag != correct_tag]
    
    # Select 3 random distractors
    distractor_texts = random.sample(distractor_tags, min(3, len(distractor_tags)))
    distractor_texts = [DEMERIT_TAG_DESCRIPTIONS.get(tag, tag) for tag in distractor_texts]
    
    # Combine and shuffle all options
    all_option_texts = [correct_option_text] + distractor_texts
    random.shuffle(all_option_texts)

    options = {chr(65 + i): text for i, text in enumerate(all_option_texts)}
    correct_key = [k for k, v in options.items() if v == correct_option_text][0]

    return [{
        "question": "以下哪一個是誤導性新聞的常見技巧？",
        "options": options,
        "answer": correct_key,
        "explanation": correct_explanation_text,
    }]