"""
NiceGUI-based portal for NovaLabs Hub
Central route registration - all @ui.page decorators are here
Implementation functions are in respective modules:
- auth_pages.py: login and registration
- user_dash.py: student dashboard and course pages
- admin_dash.py: admin dashboard and management pages
"""

import sys
import os

# Add parent directory to path so we can import hub modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from fastapi import Request

# Import page implementations
import auth_pages
import user_dash
import admin_dash


# ============================================================================
# Create Handler Instances
# ============================================================================
auth_handler = auth_pages.AuthPages()
user_handler = user_dash.UserDashboard()
admin_handler = admin_dash.AdminDashboard()


@ui.page('/login')
def route_login(request: Request):
    """Login page route"""
    return auth_handler.login_page(request)


@ui.page('/register')
def route_register(request: Request):
    """Registration page route"""
    return auth_handler.register_page(request)


# ============================================================================
# Route Registration - Student Dashboard
# ============================================================================

@ui.page('/')
def route_student_dashboard(request: Request):
    """Main student dashboard route"""
    return user_handler.student_dashboard(request)


@ui.page('/course/{course_id}')
def route_course_page(request: Request, course_id: int):
    """Individual course page route"""
    return user_handler.course_page(request, course_id)


# ============================================================================
# Route Registration - Admin Dashboard
# ============================================================================

@ui.page('/admin')
def route_admin_dashboard(request: Request):
    """Admin dashboard route"""
    return admin_handler.admin_dashboard(request)


@ui.page('/admin/users')
def route_admin_users(request: Request):
    """Admin users management route"""
    return admin_handler.admin_users(request)


@ui.page('/admin/courses')
def route_admin_courses(request: Request):
    """Admin courses management route"""
    return admin_handler.admin_courses(request)


@ui.page('/admin/labs')
def route_admin_labs(request: Request):
    """Admin labs management route"""
    return admin_handler.admin_labs(request)


@ui.page('/admin/analytics')
def route_admin_analytics(request: Request):
    """Admin analytics route"""
    return admin_handler.admin_analytics(request)


# ============================================================================
# Run Portal
# ============================================================================

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(
        title='NovaLabs Hub',
        port=8101,
        reload=True,
        show=True
    )
