"""
Принудительная остановка всех экземпляров бота
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def stop_all_processes():
    """Остановить все процессы Python"""
    print("🛑 Остановка всех Python процессов...")
    
    if sys.platform == "win32":
        # Windows
        try:
            # Получаем список процессов
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], 
                                  capture_output=True, text=True)
            print("Найденные процессы:")
            print(result.stdout)
            
            # Останавливаем
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                         capture_output=True, text=True)
            subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"], 
                         capture_output=True, text=True)
            print("✅ Все Python процессы остановлены")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    else:
        # Linux/Mac
        try:
            subprocess.run(["pkill", "-f", "python"], capture_output=True)
            subprocess.run(["pkill", "-f", "python3"], capture_output=True)
            print("✅ Все Python процессы остановлены")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def delete_webhook():
    """Удалить webhook через API"""
    print("🔄 Удаление webhook...")
    
    # Читаем токен
    token = None
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('TELEGRAM_TOKEN='):
                    token = line.split('=')[1].strip()
                    break
    
    if not token:
        print("❌ Токен не найден")
        return
    
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        response = requests.get(url)
        data = response.json()
        
        if data['ok']:
            print("✅ Webhook удален успешно")
        else:
            print(f"❌ Ошибка: {data}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def clear_pending_updates():
    """Очистить ожидающие обновления"""
    print("🔄 Очистка ожидающих обновлений...")
    
    token = None
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('TELEGRAM_TOKEN='):
                    token = line.split('=')[1].strip()
                    break
    
    if not token:
        print("❌ Токен не найден")
        return
    
    try:
        # Получаем последнее обновление
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1"
        response = requests.get(url)
        data = response.json()
        
        if data['ok'] and data['result']:
            # Получаем последний update_id
            last_update_id = data['result'][-1]['update_id']
            
            # Очищаем все обновления
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url)
            if response.json()['ok']:
                print("✅ Ожидающие обновления очищены")
        else:
            print("✅ Нет ожидающих обновлений")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🛑  Принудительная остановка бота")
    print("=" * 50)
    print()
    
    stop_all_processes()
    time.sleep(2)
    delete_webhook()
    time.sleep(1)
    clear_pending_updates()
    
    print()
    print("=" * 50)
    print("✅ Все экземпляры бота остановлены")
    print("🚀 Теперь можно запустить бота заново: python main.py")
    print("=" * 50)