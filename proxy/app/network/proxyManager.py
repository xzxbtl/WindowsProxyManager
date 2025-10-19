import ctypes
import subprocess
import sys
import winreg


def add_proxy_to_windows_credentials(host: str, port: int,
                                     username: str, password: str) -> bool:
    try:
        subprocess.run([
            "cmdkey",
            f"/add:{host}:{port}",
            f"/user:{username}",
            f"/pass:{password}",
        ], check=True, capture_output=True)

        print(f"✅ Добавлены учётные данные для {str(f"{host}:{port}")}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при добавлении учётных данных: {e.stderr.decode(errors='ignore')}")
        return False


def remove_proxy_from_windows_credentials(host: str, port: int) -> bool:
    try:
        subprocess.run(["cmdkey", f"/delete:{str(f"{host}:{port}")}"], check=True, capture_output=True)
        print(f"🗑️ Удалены учётные данные для {str(f"{host}:{port}")}")
        return True

    except subprocess.CalledProcessError as e:
        if b"not found" in e.stderr:
            print(f"ℹ️ Учётные данные для {str(f"{host}:{port}")} не найдены")
        else:
            print(f"❌ Ошибка при удалении учётных данных: {e.stderr.decode(errors='ignore')}")
        return False


def set_system_proxy(host: str, port: int, proxy_type: str = "all"):
    proxy_type = proxy_type.lower()

    if proxy_type not in ["http", "https", "all"]:
        print(f"❌ Неподдерживаемый тип прокси: {proxy_type}")
        return

    if proxy_type == "all":
        winhttp_proxy = f"http={host}:{port};https={host}:{port}"
    elif proxy_type == "http":
        winhttp_proxy = f"http={host}:{port}"
    else:
        winhttp_proxy = f"https={host}:{port}"

    if proxy_type == "all":
        wininet_proxy = f"{host}:{port}"
    elif proxy_type == "http":
        wininet_proxy = f"{host}:{port}"
    else:
        wininet_proxy = f"{host}:{port}"

    # --- WinHTTP ---
    try:
        subprocess.run(["netsh", "winhttp", "reset", "proxy"], check=True)
        subprocess.run(["netsh", "winhttp", "set", "proxy", winhttp_proxy], check=True)
        print(f"✅ WinHTTP прокси установлен: {winhttp_proxy}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки WinHTTP прокси: {e}")

    # --- WinINET / браузеры ---
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, wininet_proxy)
        winreg.CloseKey(key)
        print(f"✅ Системный прокси для браузеров установлен: {wininet_proxy}")
    except Exception as e:
        print(f"❌ Ошибка установки прокси для браузеров: {e}")



def reset_system_proxy():
    # --- 1️⃣ WinHTTP ---
    try:
        subprocess.run(["netsh", "winhttp", "reset", "proxy"], check=True)
        print("✅ WinHTTP прокси сброшен")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сброса WinHTTP прокси: {e}")

    # --- 2️⃣ WinINET / браузеры ---
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)  # отключаем прокси
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")     # очищаем сервер
        winreg.CloseKey(key)
        print("✅ Системный прокси для браузеров сброшен")
    except PermissionError:
        print("❌ Ошибка: недостаточно прав для изменения реестра. Запустите скрипт от администратора.")
    except Exception as e:
        print(f"❌ Ошибка сброса прокси для браузеров: {e}")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def run_as_admin():
    script = sys.argv[0]
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    sys.exit(0)
