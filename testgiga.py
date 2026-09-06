import os
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

credentials = os.getenv("GIGACHAT_CREDENTIALS")
scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
api_url = os.getenv("GIGACHAT_API_URL")

print("⏳ Пытаемся получить токен напрямую через requests...")

try:
    # 1. Получаем токен
    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '12345678-1234-1234-1234-123456789012',
        'Authorization': f'Basic {credentials}'
    }
    payload = {'scope': scope}

    r1 = requests.post(auth_url, headers=headers, data=payload, verify=False, timeout=15)
    r1.raise_for_status()
    token = r1.json().get('access_token')
    print(f"✅ Токен получен! (начинается с {token[:15]}...)")

    # 2. Задаем вопрос
    print("⏳ Отправляем вопрос нейросети...")
    headers2 = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload2 = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": "Напиши одно слово: УрФУ"}]
    }
    r2 = requests.post(api_url, headers=headers2, json=payload2, verify=False, timeout=30)
    r2.raise_for_status()

    answer = r2.json()['choices'][0]['message']['content']
    print(f"🎉 УСПЕХ! Нейросеть ответила: {answer}")

except requests.exceptions.SSLError as e:
    print(f"❌ ОШИБКА SSL: {e}")
    print(
        "💡 Совет: Попробуй отключить антивирус на 5 минут или раздать интернет с телефона (возможно, сеть МИРЭА блокирует).")
except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Текст ошибки от Сбера: {e.response.text}")