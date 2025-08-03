import requests


async def get_instance_id():
    path="instance-id"
    base_url = "http://169.254.169.254/latest/meta-data/"
    try:
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2,
        )
        token_response.raise_for_status()
        token = token_response.text

        print("Trying to get machine_id!")
        response = requests.get(base_url + path, headers={"X-aws-ec2-metadata-token": token},timeout=2)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"🤖 Failed to get machine_id using path ({path}): {e}")
        return None
