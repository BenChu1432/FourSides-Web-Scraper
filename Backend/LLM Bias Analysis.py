import requests
import json

# Replace with your actual article content
article_text = """
[INSERT YOUR NEWS ARTICLE HERE]
"""

# Prompt to analyze the article for political bias
analysis_prompt = f"""
Analyze the following news article for political bias. Specifically, identify whether the article leans pro-democracy, pro-communism, or is neutral. Provide evidence from the text to support your conclusion.

Article:
\"\"\"
{article_text}
\"\"\"
"""


url = "https://api.fireworks.ai/inference/v1/chat/completions"
payload = {
  "model": "accounts/fireworks/models/mixtral-8x22b-instruct",
  "max_tokens": 2048,
  "top_p": 1,
  "top_k": 40,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "temperature": 0.6,
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ]
}
headers = {
  "Accept": "application/json",
  "Content-Type": "application/json",
  "Authorization": "Bearer fw_3ZkqKkuQG6dKrQETJaJFjGDV"
}
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Check for errors
if response.status_code != 200:
    print("Error:", response.status_code, response.text)
else:
    # Parse response JSON
    result = response.json()
    
    # Extract and print the model's reply
    reply = result['choices'][0]['message']['content']
    print("reply:",reply)