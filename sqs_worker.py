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
        await news_controller.scrape_classify_and_store_news_for_one_news_outlet(media_name)
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
            MaxNumberOfMessages=5,
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

# import os
# import json
# import boto3
# from botocore.exceptions import NoCredentialsError
# import asyncio
# import sys
# from app.controller import news_controller
# from app.db.database import AsyncSessionLocal  # ✅ Use your existing session
# from dotenv import load_dotenv

# import boto3

# from util import awsUtil
# load_dotenv()
# SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
# LIFECYCLE_HOOK_NAME = os.getenv("LIFECYCLE_HOOK_NAME")  # e.g., "MyTerminateHook"
# ASG_NAME = os.getenv("ASG_NAME")  # e.g., "my-auto-scaling-group"
# print("🌈 Successfully loaded environment variables")


# lock = asyncio.Lock()
# shutdown_event = asyncio.Event()
# active_jobs=0



# # try:
# #     # Set up a session without specifying a profile
# #     session = boto3.Session()
# #     current_profile = session.profile_name or "default"
# #     print("✅ Currently using AWS profile:", current_profile)

# #     # Optional: verify identity
# #     sts = session.client('sts')
# #     identity = sts.get_caller_identity()
# #     print("🧾 ARN:", identity['Arn'])
# # except NoCredentialsError:
# #     print("❌ No credentials found.")
# # except Exception as e:
# #     print("❌ Error:", e)
# session = boto3.Session()
# print("✅ Boto3 session object successfully created to talk to the AWS service to get more info about this instance from:", boto3.Session().__class__)

# sqs = session.client('sqs', region_name='ap-northeast-1')
# print("👥 Succesfully connected to the SQS instance")
# autoscaling = session.client('autoscaling', region_name='ap-northeast-1')
# print("🎯 Succesfully connected to the autoscaling function")



# def graceful_shutdown(signum, frame):
#     print("\n🛑 SIGTERM received. Waiting for jobs to finish...")
#     shutdown_event.set()

#     async def wait_and_exit():
#         global active_jobs
#         while True:
#             async with lock:
#                 if active_jobs == 0:
#                     break
#             print(f"⏳ Waiting for {active_jobs} active jobs to finish...")
#             await asyncio.sleep(5)
#         print("🤙🏻 Calling the Instance Metadata Service (IMDS) for the instance_id... ")
#         instance_id=await awsUtil.get_instance_id()
#         print("🎉 Successfully fetched the instance_id:",instance_id)
#         print("✅ All jobs finished. Completing lifecycle hook...")
#         try:
#             autoscaling.complete_lifecycle_action(
#                 LifecycleHookName=LIFECYCLE_HOOK_NAME,
#                 AutoScalingGroupName=ASG_NAME,
#                 LifecycleActionResult='CONTINUE',
#                 InstanceId=instance_id
#             )
#             print("✅ Lifecycle hook completed.")
#         except Exception as e:
#             print("❌ Failed to complete lifecycle hook:", e)

#         sys.exit(0)

#     # Run the wait logic in the asyncio loop
#     asyncio.get_event_loop().create_task(wait_and_exit())

# async def process_message(message_body):
#     print("⚡️ Processing message...")
#     global active_jobs
#     async with lock:
#         active_jobs += 1
#     try:
#         data = json.loads(message_body)
#         media_name = data.get("media_name")
#         task_type = data.get("task_type")

#         if task_type == "scrape_specific_news_outlet" and media_name:
#             await news_controller.scrape_translate_and_store_news_for_one_news_outlet(media_name)
#             print(f"✅ Scraped: {media_name}")
#         elif task_type == "scrape-all-taiwanese-news":
#             await news_controller.scrape_and_store_all_taiwanese_news()
#             print("✅ Scraped all Taiwanese news")
#         else:
#             print("⚠️ Unknown or incomplete task")
#     finally:
#         async with lock:
#             active_jobs -= 1

# async def poll_sqs():
#     print("🔁 Polling SQS...")
#     while True:
#         response = sqs.receive_message(
#             QueueUrl=SQS_QUEUE_URL,
#             MaxNumberOfMessages=5,
#             WaitTimeSeconds=10
#         )
#         messages = response.get("Messages", [])
#         tasks = []

#         for message in messages:
#             body = message["Body"]
#             tasks.append(process_message(body))

#             # Delete from SQS
#             sqs.delete_message(
#                 QueueUrl=SQS_QUEUE_URL,
#                 ReceiptHandle=message["ReceiptHandle"]
#             )

#         if tasks:
#             await asyncio.gather(*tasks)

#         await asyncio.sleep(1)

# if __name__ == "__main__":
#     asyncio.run(poll_sqs())
