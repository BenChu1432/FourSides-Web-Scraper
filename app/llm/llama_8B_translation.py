from together import Together
import os
import asyncio
from app.modals.newsEntity import NewsEntity


TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")

client = Together(api_key=TOGETHER_AI_API_KEY)

async def translate_article(article: NewsEntity):
    if article.content=="" or not article.content:
        return
    print("Translating:",article.url)
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            temperature=0.2,
            top_p=0.9,
            messages=[
                {
                    "role": "system",
                    "content": "You are a translation engine. Translate traditional Chinese into natural, fluent English. Do not explain, do not comment, do not say anything else. Just return the translated text only. Translate names to pinyin. Output only the translation."
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate the following traditional Chinese article into English. Output only the translation:\n\n{article.content}"
                    )
                }
            ],
        )
        print("content_en:",response.choices[0].message.content.strip())
        article.content_en = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Translation failed for article {article}: {e}")