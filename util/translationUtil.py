import requests

def translate_text(text, source_lang="en", target_lang="es", api_url="https://libretranslate.com/translate"):
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text"
    }

    response = requests.post(api_url, data=payload)
    
    if response.status_code == 200:
        translated_text = response.json()["translatedText"]
        return translated_text
    else:
        print("Error:", response.status_code, response.text)
        return None

# Example usage
original_text = "Hello, how are you?"
translated = translate_text(original_text, source_lang="en", target_lang="fr")

print("Original:", original_text)
print("Translated:", translated)