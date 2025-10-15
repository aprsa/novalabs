from nicegui import ui
from fastapi import Request
from client.sdk import HubClientError
from base import PageBase


class UserDashboard(PageBase):
    """Student dashboard page implementations"""

    def student_dashboard(self, request: Request):
        """Main student dashboard"""
        user = self.require_auth(request)
        if not user:
            return

        # Admin redirect
        if user['role'] == 'admin':
            ui.navigate.to('/admin')
            return

        # Header
        with ui.header().classes('items-center justify-between'):
            with ui.row().classes('items-center'):
                ui.label('🔭 NovaLabs').classes('text-xl font-bold')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm')
                ui.button('Logout', on_click=lambda: self.logout()).props('flat dense')

        # Main content
        with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
            ui.label(f"Hello, {user['first_name']}!").classes('text-3xl font-bold mb-2')
            ui.label(f"{user['institution'] or 'Cadet'}").classes('text-gray-600 mb-8')

            # Get user's courses and labs
            try:
                self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)
                courses = self.hub_client.get_user_courses(user['id'])
                labs = self.hub_client.get_labs()

                # Courses Section
                with ui.card().classes('w-full mb-6'):
                    ui.label('My Courses').classes('text-2xl font-bold mb-4')

                    if not courses:
                        ui.label('You are not enrolled in any courses yet.').classes('text-gray-600')
                        ui.label('Contact your instructor to get enrolled.').classes('text-sm text-gray-500')
                    else:
                        for course in courses:
                            with ui.card().classes('w-full mb-4 hover:shadow-lg transition-shadow'):
                                with ui.row().classes('items-center justify-between w-full'):
                                    with ui.column():
                                        ui.label(course['name']).classes('text-xl font-bold')
                                        ui.label(f"{course['code']} • {course['semester']}").classes('text-gray-600')

                                    ui.button('View Course', on_click=lambda c=course: ui.navigate.to(f'/course/{c["id"]}')).props('flat')

                # Available Labs Section
                with ui.card().classes('w-full'):
                    ui.label('Available Labs').classes('text-2xl font-bold mb-4')

                    if not labs:
                        ui.label('No labs available at this time.').classes('text-gray-600')
                    else:
                        with ui.grid(columns=2).classes('w-full gap-4'):
                            for lab in labs:
                                with ui.card().classes('hover:shadow-lg transition-shadow cursor-pointer'):
                                    ui.label(lab['name']).classes('text-xl font-bold mb-2')
                                    ui.label(lab['description']).classes('text-gray-600 text-sm mb-4')

                                    # Check access
                                    access = self.hub_client.check_lab_access(user['id'], lab['slug'])

                                    if access['has_access']:
                                        ui.button(
                                            'Launch Lab',
                                            on_click=lambda l=lab: self.launch_lab(l, user['id'])
                                        ).props('color=primary')

                                        if access.get('due_date'):
                                            from datetime import datetime
                                            due = datetime.fromisoformat(access['due_date'])
                                            ui.label(f"Due: {due.strftime('%b %d, %Y')}").classes('text-xs text-orange-600 mt-2')
                                    else:
                                        ui.label('Not assigned to your courses').classes('text-sm text-gray-500')
                                        ui.button('Request Access', on_click=lambda: ui.notify('Contact your instructor')).props('flat disabled')

            except HubClientError as e:
                ui.label(f'Error loading dashboard: {str(e)}').classes('text-red-500')

    def launch_lab(self, lab, user_id):
        """Launch a lab in new tab"""
        # Create or resume lab session
        try:
            session = self.hub_client.get_or_create_lab_session(user_id, lab['slug'])
            ui.run_javascript(f"window.open('{lab['ui_url']}', '_blank')")
            ui.notify(f'Launching {lab["name"]}...', type='positive')
        except HubClientError as e:
            ui.notify(f'Error launching lab: {str(e)}', type='negative')

    def course_page(self, request: Request, course_id: int):
        """Individual course page"""
        user = self.require_auth(request)
        if not user:
            return

        with ui.header().classes('items-center justify-between'):
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
                ui.label('🔭 NovaLabs').classes('text-xl font-bold ml-2')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm')
                ui.button('Logout', on_click=lambda: self.logout()).props('flat dense')

        with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
            try:
                self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)
                course = self.hub_client.get_course(course_id)

                ui.label(course['name']).classes('text-3xl font-bold mb-2')
                ui.label(f"{course['code']} • {course['semester']}").classes('text-gray-600 mb-8')

                # Lab assignments for this course
                with ui.card().classes('w-full'):
                    ui.label('Lab Assignments').classes('text-2xl font-bold mb-4')

                    # Get assignments (you'll need to add this to client)
                    # For now, placeholder
                    ui.label('Lab assignments will appear here').classes('text-gray-600')

                # Grades
                with ui.card().classes('w-full mt-6'):
                    ui.label('Grades').classes('text-2xl font-bold mb-4')

                    grades = self.hub_client.get_user_grades(user['id'], course_id=course_id)

                    if not grades:
                        ui.label('No grades yet').classes('text-gray-600')
                    else:
                        columns = [
                            {'name': 'assignment', 'label': 'Assignment', 'field': 'assignment'},
                            {'name': 'score', 'label': 'Score', 'field': 'score'},
                            {'name': 'graded', 'label': 'Graded', 'field': 'graded'},
                        ]

                        rows = [
                            {
                                'assignment': g.get('assignment_title', 'Lab Assignment'),
                                'score': f"{g['score']}/{g['max_score']}" if g['score'] is not None else 'Not graded',
                                'graded': g['graded_at'][:10] if g.get('graded_at') else '-'
                            }
                            for g in grades
                        ]

                        ui.table(columns=columns, rows=rows)

            except HubClientError as e:
                ui.label(f'Error loading course: {str(e)}').classes('text-red-500')
