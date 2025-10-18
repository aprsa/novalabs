from nicegui import ui
from fastapi import Request
from client.sdk import SDKClientError
from session_manager import session_manager


def admin_dashboard(request: Request):
    """Main admin dashboard"""
    user = session_manager.require_admin(request)
    if not user:
        return

    client = session_manager.get_authenticated_client(request)
    if not client:
        ui.label('Session expired. Please login again.').classes('text-red-500')
        return

    # Header
    with ui.header().classes('items-center justify-between bg-indigo-600'):
        with ui.row().classes('items-center'):
            ui.label('🔭 NovaLabs Admin').classes('text-xl font-bold text-white')

        with ui.row().classes('items-center gap-4'):
            ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')
            ui.button('Logout', on_click=lambda: logout(request)).props('flat text-color=white')

    # Sidebar + content...
    with ui.column().classes('w-full p-8'):
        ui.label('Dashboard Overview').classes('text-3xl font-bold mb-8')

        try:
            # Stats
            users = client.get_users()
            labs = client.get_labs()

            with ui.row().classes('w-full gap-4 mb-8'):
                with ui.card().classes('flex-1'):
                    ui.label('Total Users').classes('text-gray-600 text-sm')
                    ui.label(str(len(users))).classes('text-4xl font-bold')

                with ui.card().classes('flex-1'):
                    ui.label('Available Labs').classes('text-gray-600 text-sm')
                    ui.label(str(len(labs))).classes('text-4xl font-bold')

        except SDKClientError as e:
            ui.label(f'Error: {str(e)}').classes('text-red-500')


def admin_users(request: Request):
    """User management page"""
    user = session_manager.require_admin(request)
    if not user:
        return

    client = session_manager.get_authenticated_client(request)
    if not client:
        return

    # Implementation...


def admin_labs(request: Request):
    """Lab management page"""
    user = session_manager.require_admin(request)
    if not user:
        return

    client = session_manager.get_authenticated_client(request)
    if not client:
        return

    # Implementation...


def logout(request: Request):
    """Logout helper"""
    session_manager.logout(request)
    session_manager.clear_session_cookie()
