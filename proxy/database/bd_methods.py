from sqlalchemy import select
from sqlalchemy.orm import Session

from proxy.app.network.proxyManager import add_proxy_to_windows_credentials, remove_proxy_from_windows_credentials
from proxy.database.schemas import Proxy


def validate_repeat_proxys(session: Session, proxy_str: str) -> bool:
    print("DEBUG: validate_repeat_proxys called for", proxy_str)
    try:
        result = session.execute(select(Proxy).where(Proxy.proxy_to_str == proxy_str))
        all_proxys = result.scalars().all()
        print("DEBUG: validate_repeat_proxys result =", all_proxys)
        if all_proxys:
            print("Данная прокси уже существует")
            return False
        return True
    except Exception as exc:
        print("Ошибка в validate_repeat_proxys:", exc)
        return False


def add_proxy(session: Session,
              type_proxy: str,
              host: str, port: int,
              user: str = None, password: str = None,
              public: bool = False) -> bool:
    auth = f"{user}:{password}@" if user else ""
    proxy_to_str = f"{type_proxy}://{auth}{host}:{port}"

    if not validate_repeat_proxys(session, proxy_to_str):
        print("Не пройдена валидация (дубликат)")
        return False

    try:
        proxy = Proxy(
            type=type_proxy,
            host=host,
            port=port,
            user=user,
            password=password,
            proxy_to_str=proxy_to_str,
            public=public
        )
        session.add(proxy)
        session.commit()
        session.refresh(proxy)

        if user and password:
            try:
                add_proxy_to_windows_credentials(host, port, user, password)
            except Exception as e:
                print("Ошибка при добавлении в Windows credentials:", e)

        print(f"Успешно добавлена прокси - {proxy_to_str}")
        return True
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        print(f"Ошибка при добавлении прокси - {proxy_to_str} = {e}")
        return False


def delete_proxy(session: Session, proxy_id: int) -> bool:
    try:
        proxy = session.get(Proxy, proxy_id)
        if not proxy:
            print(f"⚠️ Прокси с id={proxy_id} не найден")
            return False

        if proxy.user and proxy.password:
            try:
                remove_proxy_from_windows_credentials(proxy.host, proxy.port)
            except Exception as e:
                print("Ошибка при удалении из Windows credentials:", e)

        session.delete(proxy)
        session.commit()
        print(f"✅ Прокси id={proxy_id} успешно удалена")
        return True
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        print(f"Ошибка при попытке найти и удалить прокси = {e}")
        return False


def edit_proxy(session: Session, proxy_id: int, **kwargs) -> bool:
    try:
        proxy = session.get(Proxy, proxy_id)
        if not proxy:
            print(f"⚠️ Прокси с id={proxy_id} не найден")
            return False

        old_host = proxy.host
        old_port = proxy.port
        old_user = proxy.user
        old_password = proxy.password

        for key, value in kwargs.items():
            if hasattr(proxy, key):
                setattr(proxy, key, value)
            else:
                print(f"⚠️ Поле '{key}' отсутствует в модели Proxy — пропускаем")

        type_ = kwargs.get("type", proxy.type)
        host = kwargs.get("host", proxy.host)
        port = kwargs.get("port", proxy.port)
        user = kwargs.get("user", proxy.user or "")
        password = kwargs.get("password", proxy.password or "")
        auth = f"{user}:{password}@" if user else ""
        new_proxy_to_str = f"{type_}://{auth}{host}:{port}"

        result = session.execute(
            select(Proxy).where(Proxy.proxy_to_str == new_proxy_to_str, Proxy.id != proxy_id)
        )
        duplicate = result.scalars().first()
        if duplicate:
            print(f"⚠️ Прокси с такими параметрами уже существует ({new_proxy_to_str})")
            session.rollback()
            return False

        proxy.proxy_to_str = new_proxy_to_str

        session.commit()
        session.refresh(proxy)

        try:
            if old_user and old_password:
                remove_proxy_from_windows_credentials(old_host, old_port)
        except Exception as e:
            print("Ошибка при удалении старых Windows credentials:", e)

        try:
            if proxy.user and proxy.password:
                add_proxy_to_windows_credentials(proxy.host, proxy.port, proxy.user, proxy.password)
        except Exception as e:
            print("Ошибка при добавлении новых Windows credentials:", e)

        print(f"✅ Прокси id={proxy_id} успешно обновлён: {proxy.proxy_to_str}")
        return True

    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        print(f"❌ Ошибка при редактировании прокси id={proxy_id}: {e}")
        return False


def get_proxy(session: Session, proxy_id: int):
    try:
        proxy = session.get(Proxy, proxy_id)
        if proxy:
            return proxy
        return False
    except Exception as e:
        print("Ошибка get_proxy:", e)
        return False
