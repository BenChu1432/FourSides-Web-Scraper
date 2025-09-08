import os
import json
import boto3
from botocore.exceptions import NoCredentialsError
import asyncio

from app.controller import news_controller
from app.db.database import AsyncSessionLocal  # ✅ Use your existing session
from dotenv import load_dotenv

import boto3
print("✅ Boto3 is using session from:", boto3.Session().__class__)


load_dotenv()
try:
    # Set up a session without specifying a profile
    session = boto3.Session()
    current_profile = session.profile_name or "default"
    print("✅ Currently using AWS profile:", current_profile)

    # Optional: verify identity
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print("🧾 ARN:", identity['Arn'])
except NoCredentialsError:
    print("❌ No credentials found.")
except Exception as e:
    print("❌ Error:", e)
session = boto3.Session()
sqs = session.client('sqs', region_name='ap-northeast-1')
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

async def process_message(message_body):
    data = json.loads(message_body)
    media_name = data.get("media_name")
    task_type = data.get("task_type")
    print("task_type:",task_type)

    if task_type == "scrape_specific_news_outlet" and media_name:
        await news_controller.scrape_generate_question_and_classify_and_store_news_for_one_news_outlet(media_name)
        print(f"✅ Scraped: {media_name}")
    elif task_type == "scrape-all-taiwanese-news":
        await news_controller.scrape_and_store_all_taiwanese_news()
        print(f"✅ Scraped: {media_name}")
    else:
        print("⚠️ Unknown or incomplete task")

async def poll_sqs():
    print("🔁 Polling SQS...")
    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )
        messages = response.get("Messages", [])
        tasks = []

        for message in messages:
            body = message["Body"]
            tasks.append(process_message(body))

            # Delete from SQS
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

        if tasks:
            await asyncio.gather(*tasks)

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(poll_sqs())
