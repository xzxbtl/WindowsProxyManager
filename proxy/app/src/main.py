import flet as ft
from sqlalchemy import select
from proxy.app.network.proxyManager import (
    set_system_proxy,
    reset_system_proxy
)
from proxy.database.bd_methods import add_proxy, edit_proxy, delete_proxy, get_proxy
from proxy.database.config import get_session, create_base
from proxy.database.schemas import Proxy


running_proxy = {"id": None}
edit_state = {"editing_id": None}


def load_proxies_from_db():
    try:
        with get_session() as db_session:
            result = db_session.execute(select(Proxy))
            return result.scalars().all()
    except Exception as exc:
        print("Ошибка load_proxies_from_db:", exc)
        return []


def remove_overlay(overlay: ft.Control, page: ft.Page):
    try:
        if overlay in page.controls:
            page.controls.remove(overlay)
            page.update()
            print("DEBUG: overlay removed")
    except Exception as exc:
        print("DEBUG: error removing overlay:", exc)


def show_fullscreen_overlay(page: ft.Page, title: str, content_control: ft.Control, width: int = 720):
    try:
        overlay = ft.Container(expand=True, bgcolor="rgba(0,0,0,0.72)", alignment=ft.alignment.center)
        modal_box = ft.Container(
            width=width,
            padding=ft.padding.all(18),
            border_radius=10,
            bgcolor="#2b2c2e",
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title, weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.WHITE),
                            ft.IconButton(icon=ft.Icons.CLOSE, on_click=lambda e, o=overlay: remove_overlay(o, page))
                        ]
                    ),
                    ft.Divider(height=8, color="#3a3b3d"),
                    content_control,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.ElevatedButton("Закрыть", on_click=lambda e, o=overlay: remove_overlay(o, page))
                        ],
                    ),
                ]
            )
        )
        overlay.content = modal_box
        page.add(overlay)
        page.update()
        print("DEBUG: centered fullscreen overlay added")
    except Exception as exc:
        print("FATAL show_fullscreen_overlay error:", exc)


def show_fullscreen_alert(page: ft.Page, title: str, message: str):
    content = ft.Text(message, color=ft.Colors.WHITE)
    show_fullscreen_overlay(page, title, content, width=520)


def on_info_action(page: ft.Page, proxy_id: int):
    try:
        with get_session() as session:
            proxy = get_proxy(session, proxy_id)
    except Exception as exc:
        show_fullscreen_alert(page, "Ошибка", f"Ошибка чтения прокси: {exc}")
        return

    if not proxy:
        show_fullscreen_alert(page, "Ошибка", "Прокси не найдена")
        return

    info_column = ft.Column(
        spacing=10,
        controls=[
            ft.Row([ft.Text("Тип:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(proxy.type or "-", color=ft.Colors.WHITE)]),
            ft.Row([ft.Text("Хост:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(proxy.host or "-", color=ft.Colors.WHITE)]),
            ft.Row([ft.Text("Порт:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(str(proxy.port) if proxy.port else "-", color=ft.Colors.WHITE)]),
            ft.Row([ft.Text("Юзер:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(proxy.user or "-", color=ft.Colors.WHITE)]),
            ft.Row([ft.Text("Пароль:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(proxy.password or "-", color=ft.Colors.WHITE)]),
            ft.Row([ft.Text("Прокси:", weight=ft.FontWeight.BOLD, width=120, color=ft.Colors.WHITE),
                    ft.Text(proxy.proxy_to_str or "-", color=ft.Colors.WHITE)]),
        ]
    )

    content = ft.Container(content=info_column, padding=ft.padding.all(8), bgcolor="#2b2c2e", border_radius=6)
    show_fullscreen_overlay(page, "Информация о прокси", content, width=700)


def main(page: ft.Page):
    page.title = "ProxyManager"
    page.window_resizable = True
    page.window.center()
    page.window.height = 800
    page.window.width = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1b1c1e"

    main_content = ft.Container(expand=True, padding=16)
    proxies_column = ft.Column(spacing=10)
    proxies_scroll_container = ft.Container(content=ft.ListView(controls=[proxies_column]), expand=True, padding=10)

    https_value = {"val": True}

    def start_proxy(proxy_id: int, content_column: ft.Column):
        running_proxy["id"] = proxy_id
        with get_session() as session:
            proxy = get_proxy(session, proxy_id)
        set_system_proxy(proxy.host, proxy.port, proxy.type)
        show_proxies_list(content_column)

    def stop_proxy(proxy_id: int, content_column: ft.Column):
        if running_proxy.get("id") == proxy_id:
            running_proxy["id"] = None
        reset_system_proxy()
        show_proxies_list(content_column)

    def on_delete_action(proxy_id: int, proxies_column: ft.Column):
        try:
            with get_session() as session:
                success = delete_proxy(session, int(proxy_id))
            if success:
                show_fullscreen_alert(page, "Уведомление", "Прокси успешно удалена")
            else:
                show_fullscreen_alert(page, "Ошибка", "Ошибка при удалении прокси")
            show_proxies_list(content_column=proxies_column)
        except Exception as e:
            print("Ошибка при удалении прокси:", e)
            show_fullscreen_alert(page, "Ошибка", str(e))


    def show_proxies_list(content_column: ft.Column):
        proxys = load_proxies_from_db()
        content_column.controls.clear()

        for proxy in proxys:
            proxy_id = proxy.id
            proxy_str = proxy.proxy_to_str
            is_running = (proxy_id == running_proxy["id"])

            start_icon = ft.Icons.POWER_SETTINGS_NEW if not is_running else ft.Icons.CANCEL
            start_color = ft.Colors.GREEN if not is_running else ft.Colors.RED
            start_tooltip = "Запустить" if not is_running else "Остановить"

            def make_click(action: str, pid=proxy_id):
                def _on_click(e: ft.ControlEvent):
                    on_proxy_action(pid, action, content_column)

                return _on_click

            proxy_row = ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            proxy_str,
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                            width=300,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.IconButton(
                                    icon=start_icon,
                                    icon_color=start_color,
                                    tooltip=start_tooltip,
                                    on_click=make_click("start" if not is_running else "stop"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Редактировать",
                                    on_click=make_click("edit"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    tooltip="Удалить",
                                    on_click=make_click("delete"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.INFO,
                                    tooltip="Информация",
                                    on_click=make_click("info"),
                                ),
                            ],
                        ),
                    ],
                ),
                padding=10,
                bgcolor="#2b2c2e",
                border_radius=10,
            )
            content_column.controls.append(proxy_row)
        page.update()

    def toggle_https(e: ft.ControlEvent):
        https_value["val"] = not https_value["val"]
        https_btn.icon = ft.Icons.LOCK if https_value["val"] else ft.Icons.LOCK_OPEN
        https_btn.text = "HTTPS" if https_value["val"] else "HTTP"
        https_btn.bgcolor = "#1f5f3b" if https_value["val"] else "#3a3b3d"
        page.update()

    https_btn = ft.ElevatedButton(
        text="HTTPS",
        icon=ft.Icons.LOCK,
        icon_color=ft.Colors.WHITE,
        bgcolor="#1f5f3b",
        color=ft.Colors.WHITE,
        on_click=toggle_https,
        style=ft.ButtonStyle(padding=ft.padding.symmetric(vertical=12, horizontal=18)),
    )

    input_host = ft.TextField(label="Хост", hint_text="example.com или 1.2.3.4", border_radius=10, expand=True,
                              content_padding=ft.padding.symmetric(vertical=12, horizontal=12))
    input_port = ft.TextField(label="Порт", hint_text="8080", border_radius=10, expand=True,
                              content_padding=ft.padding.symmetric(vertical=12, horizontal=12),
                              keyboard_type=ft.KeyboardType.NUMBER)
    input_user = ft.TextField(label="Юзер", hint_text="username", border_radius=10, expand=True,
                              content_padding=ft.padding.symmetric(vertical=12, horizontal=12))
    input_password = ft.TextField(label="Пароль", hint_text="пароль", border_radius=10, expand=True,
                                  content_padding=ft.padding.symmetric(vertical=12, horizontal=12),
                                  password=True, can_reveal_password=True)

    def on_cancel(e: ft.ControlEvent):
        nav.selected_index = 0
        show_proxies_list(proxies_column)
        main_content.content = proxies_scroll_container
        page.update()

    def _on_add_or_save(e: ft.ControlEvent):
        host = (input_host.value or "").strip()
        port = (input_port.value or "").strip()
        user = (input_user.value or "").strip()
        password = (input_password.value or "").strip()
        proto = "https" if https_value["val"] else "http"
        proxy_str = f"{proto}://{f'{user}:{password}@' if user else ''}{host}:{port}"

        if not host:
            show_fullscreen_alert(page, "Ошибка", "Поле Хост обязательно")
            return
        if not port.isdigit():
            show_fullscreen_alert(page, "Ошибка", "Поле Порт обязательно и должно быть числом")
            return
        pnum = int(port)
        if not (1 <= pnum <= 65535):
            show_fullscreen_alert(page, "Ошибка", "Порт должен быть 1–65535")
            return

        try:
            with get_session() as session:
                if edit_state["editing_id"]:
                    edit_proxy(session, edit_state["editing_id"],
                               type=proto, host=host, port=pnum, user=user, password=password, public=True)
                    edit_state["editing_id"] = None
                else:
                    add_proxy(session, proto, host, pnum, user, password, True)
        except Exception as exc:
            show_fullscreen_alert(page, "Ошибка", str(exc))
            return

        show_proxies_list(proxies_column)

        input_host.value = ""
        input_port.value = ""
        input_user.value = ""
        input_password.value = ""
        https_value["val"] = True
        https_btn.icon = ft.Icons.LOCK
        https_btn.text = "HTTPS"
        https_btn.bgcolor = "#1f5f3b"

        btn_add.text = "Добавить"
        btn_add.icon = ft.Icons.ADD
        btn_add.icon_color = ft.Colors.GREEN

        nav.selected_index = 0
        main_content.content = proxies_scroll_container
        page.update()

    btn_cancel = ft.TextButton("Отмена", icon=ft.Icons.CANCEL, icon_color=ft.Colors.RED, on_click=on_cancel)
    btn_add = ft.TextButton("Добавить", icon=ft.Icons.ADD, icon_color=ft.Colors.GREEN, on_click=_on_add_or_save)

    add_proxy_view = ft.Container(
        expand=True,
        bgcolor="#222425",
        border_radius=12,
        border=ft.border.all(1, "#2f3133"),
        padding=30,
        content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Container(width=400, content=ft.Column(spacing=14, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.START, controls=[https_btn]),
                ft.Divider(height=8, color="#2e2f30"),
                input_host, input_port, input_user, input_password,
                ft.Row(alignment=ft.MainAxisAlignment.END, spacing=12, controls=[btn_cancel, btn_add])
            ]))
        ])
    )

    settings_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Настройки", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Switch(label="Включить что-то"),
                ft.Switch(label="Автообновление"),
            ],
            spacing=10,
        ),
        padding=16,
        expand=True,
    )

    about_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("О программе", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("ProxyManager v1.0\nКраткое описание программы..."),
            ],
            spacing=10,
        ),
        padding=16,
        expand=True,
    )

    def on_proxy_action(proxy_id: int, action: str, content_column: ft.Column):
        try:
            if action == "start":
                if running_proxy["id"] and running_proxy["id"] != proxy_id:
                    stop_proxy(running_proxy["id"], content_column)
                start_proxy(proxy_id, content_column)


            elif action == "stop":
                stop_proxy(proxy_id, content_column)

            elif action == "edit":
                open_edit_view(proxy_id)

            elif action == "delete":
                on_delete_action(proxy_id, content_column)

            elif action == "info":
                on_info_action(page, proxy_id)

        except Exception as exc:
            show_fullscreen_alert(page, "Ошибка", str(exc))


    def open_edit_view(proxy_id: int):
        try:
            with get_session() as session:
                proxy = get_proxy(session, proxy_id)
        except Exception as exc:
            show_fullscreen_alert(page, "Ошибка", f"Не удалось загрузить прокси: {exc}")
            return

        if not proxy:
            show_fullscreen_alert(page, "Ошибка", "Прокси не найдена")
            return

        input_host.value = proxy.host or ""
        input_port.value = str(proxy.port) if proxy.port else ""
        input_user.value = proxy.user or ""
        input_password.value = proxy.password or ""
        https_value["val"] = proxy.type.lower() == "https"
        https_btn.icon = ft.Icons.LOCK if https_value["val"] else ft.Icons.LOCK_OPEN
        https_btn.text = "HTTPS" if https_value["val"] else "HTTP"
        https_btn.bgcolor = "#1f5f3b" if https_value["val"] else "#3a3b3d"

        edit_state["editing_id"] = proxy_id
        btn_add.text = "Сохранить"
        btn_add.icon = ft.Icons.SAVE
        btn_add.icon_color = ft.Colors.WHITE

        nav.selected_index = 1
        main_content.content = add_proxy_view
        page.update()



    def change_menu(e: ft.ControlEvent):
        idx = e.control.selected_index
        if idx == 0:
            show_proxies_list(proxies_column)
            main_content.content = proxies_scroll_container
        elif idx == 1:
            main_content.content = add_proxy_view
        elif idx == 2:
            main_content.content = settings_view
        elif idx == 3:
            main_content.content = about_view
        page.update()

    nav = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=110,
        bgcolor="#242527",
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.POWER_SETTINGS_NEW, label="Главная"),
            ft.NavigationRailDestination(icon=ft.Icons.DENSITY_MEDIUM, label="Добавить прокси"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Настройки"),
            ft.NavigationRailDestination(icon=ft.Icons.INFO_OUTLINE, label="О программе"),
        ],
        on_change=change_menu,
    )

    show_proxies_list(proxies_column)
    main_content.content = proxies_scroll_container

    page.add(ft.Row(
        controls=[nav, ft.VerticalDivider(width=1, color="#3a3b3d"), main_content],
        expand=True,
    ))


if __name__ == "__main__":
    create_base()
    ft.app(target=main, view=ft.FLET_APP)
