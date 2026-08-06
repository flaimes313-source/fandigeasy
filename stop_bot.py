import os
import sys
import signal
import psutil

def find_and_kill_bots():
    """Найти и убить все процессы бота"""
    print("🔍 Поиск процессов бота...")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'main.py' in cmdline or 'bot.py' in cmdline:
                print(f"✅ Найден процесс: PID={proc.info['pid']}, CMD={cmdline[:50]}...")
                print(f"   Убиваем процесс {proc.info['pid']}...")
                proc.kill()
                print(f"   ✅ Процесс {proc.info['pid']} убит")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("❌ Установите psutil: pip install psutil")
        sys.exit(1)
    
    print("=" * 50)
    print("🛑 Остановка всех экземпляров бота")
    print("=" * 50)
    
    find_and_kill_bots()
    
    print("\n✅ Все процессы бота остановлены")
