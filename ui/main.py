# ui/main.py
"""
NiceGUI-based portal for NovaLabs Hub
"""
from nicegui import ui
from fastapi import Request

# Import page modules
import auth_pages
import user_dash
import admin_dash
import cosmic_dash


# Authentication routes
@ui.page('/login')
def route_login(request: Request):
    return auth_pages.login_page(request)


@ui.page('/register')
def route_register(request: Request):
    return auth_pages.register_page(request)


# Student routes
@ui.page('/')
def route_dashboard(request: Request):
    return user_dash.student_dashboard(request)


@ui.page('/cosmic')
def route_cosmic_dashboard(request: Request):
    return cosmic_dash.cosmic_dashboard(request)


# Admin routes
@ui.page('/admin')
def route_admin_dashboard(request: Request):
    return admin_dash.admin_dashboard(request)


@ui.page('/admin/users')
def route_admin_users(request: Request):
    return admin_dash.admin_users(request)


@ui.page('/admin/labs')
def route_admin_labs(request: Request):
    return admin_dash.admin_labs(request)


if __name__ in {'__main__', '__mp_main__'}:
    # Mount static files directory
    from pathlib import Path
    from nicegui import app
    app.add_static_files('/assets', Path(__file__).parent / 'assets')

    ui.run(
        title='NovaLabs Hub',
        port=8101,
        reload=True,
        show=True
    )
