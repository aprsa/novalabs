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
    ui.run(
        title='NovaLabs Hub',
        port=8101,
        reload=True,
        show=True
    )
