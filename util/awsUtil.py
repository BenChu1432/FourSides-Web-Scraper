import requests


async def get_instance_id():
    path="instance-id"
    base_url = "http://169.254.169.254/latest/meta-data/"
    try:
        print("Trying to get machine_id!")
        response = requests.get(base_url + path, timeout=2)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"🤖 Failed to get machine_id using path ({path}): {e}")
        return None
