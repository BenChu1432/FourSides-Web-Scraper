from together import Together
import os
import asyncio
from app.models.newsEntity import NewsEntity


TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")

client = Together(api_key=TOGETHER_AI_API_KEY)

semaphore = asyncio.Semaphore(1.1)  # Only one request at a time

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
                    "content": "You're a professional translator to translate traditional Chinese into English. (For names, simply translate them into pinyin)"
                },
                {"role": "user", "content": f"""The following is a news article in traditional Chinese. Help me translate it into English:
                 {article.content}
                 """}
            ],
        )
        print("content_en:",response.choices[0].message.content.strip())
        article.content_en = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Translation failed for article {article}: {e}")