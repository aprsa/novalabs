from nicegui import ui
from fastapi import Request
from client.sdk import HubClientError
from base import PageBase


# ============================================================================
# Admin Dashboard Class
# ============================================================================

class AdminDashboard(PageBase):
    """Admin dashboard page implementations"""

    def admin_dashboard(self, request: Request):
        """Main admin dashboard"""
        user = self.require_admin(request)
        if not user:
            return

        # Header
        with ui.header().classes('items-center justify-between bg-indigo-600'):
            with ui.row().classes('items-center'):
                ui.label('🔭 NovaLabs Admin').classes('text-xl font-bold text-white')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')
                ui.button('Logout', on_click=lambda: self.logout()).props('flat text-color=white')

        # Sidebar navigation
        with ui.splitter(value=20).classes('w-full h-screen') as splitter:
            with splitter.before:
                with ui.column().classes('w-full p-4 bg-gray-50 h-full'):
                    ui.button('Dashboard', on_click=lambda: ui.navigate.to('/admin')).props('flat align=left').classes('w-full')
                    ui.button('Users', on_click=lambda: ui.navigate.to('/admin/users')).props('flat align=left').classes('w-full')
                    ui.button('Courses', on_click=lambda: ui.navigate.to('/admin/courses')).props('flat align=left').classes('w-full')
                    ui.button('Labs', on_click=lambda: ui.navigate.to('/admin/labs')).props('flat align=left').classes('w-full')
                    ui.button('Analytics', on_click=lambda: ui.navigate.to('/admin/analytics')).props('flat align=left').classes('w-full')
                    ui.separator()
                    ui.button('Back to Portal', on_click=lambda: ui.navigate.to('/')).props('flat align=left').classes('w-full')

            with splitter.after:
                with ui.column().classes('w-full p-8'):
                    ui.label('Dashboard Overview').classes('text-3xl font-bold mb-8')

                    try:
                        self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)

                        # Stats cards
                        with ui.row().classes('w-full gap-4 mb-8'):
                            # Total users
                            with ui.card().classes('flex-1'):
                                ui.label('Total Users').classes('text-gray-600 text-sm')
                                users = self.hub_client.get_users()
                                ui.label(str(len(users))).classes('text-4xl font-bold')
                                ui.label(f"{sum(1 for u in users if u['is_active'])} active").classes('text-green-600 text-xs')

                            # Active sessions
                            with ui.card().classes('flex-1'):
                                ui.label('Active Sessions').classes('text-gray-600 text-sm')
                                sessions = self.hub_client.get_sessions()
                                ui.label(str(len(sessions))).classes('text-4xl font-bold')
                                ui.label(f"{sum(1 for s in sessions if s['is_active'])} active").classes('text-gray-500 text-xs')

                            # Courses
                            with ui.card().classes('flex-1'):
                                ui.label('Total Courses').classes('text-gray-600 text-sm')
                                courses = self.hub_client.get_courses()
                                ui.label(str(len(courses))).classes('text-4xl font-bold')
                                ui.label(f"{sum(1 for c in courses if c['is_active'])} active").classes('text-blue-600 text-xs')

                            # Labs
                            with ui.card().classes('flex-1'):
                                ui.label('Available Labs').classes('text-gray-600 text-sm')
                                labs = self.hub_client.get_labs()
                                ui.label(str(len(labs))).classes('text-4xl font-bold')
                                ui.label('all active').classes('text-green-600 text-xs')

                        # Recent activity
                        with ui.card().classes('w-full'):
                            ui.label('Recent Activity').classes('text-xl font-bold mb-4')

                            activities = [
                                {'user': 'Alice Johnson', 'action': 'completed PHOEBE Lab', 'time': '5 minutes ago'},
                                {'user': 'Bob Williams', 'action': 'started Exoplanet Lab', 'time': '12 minutes ago'},
                                {'user': 'Prof. Smith', 'action': 'created new course ASTR-202', 'time': '1 hour ago'},
                                {'user': 'Charlie Brown', 'action': 'registered', 'time': '2 hours ago'},
                            ]

                            for activity in activities:
                                with ui.row().classes('w-full items-center py-2 border-b'):
                                    ui.icon('account_circle').classes('text-gray-400')
                                    with ui.column().classes('flex-1 ml-3'):
                                        ui.label(f"{activity['user']} {activity['action']}").classes('text-sm')
                                        ui.label(activity['time']).classes('text-xs text-gray-500')

                    except Exception as e:
                        ui.label(f'Error loading dashboard: {str(e)}').classes('text-red-500')

    def admin_users(self, request: Request):
        """User management page"""
        user = self.require_admin(request)
        if not user:
            return

        with ui.header().classes('items-center justify-between bg-indigo-600'):
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin')).props('flat text-color=white')
                ui.label('User Management').classes('text-xl font-bold text-white ml-2')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')

        with ui.column().classes('w-full max-w-7xl mx-auto p-8'):
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label('Users').classes('text-3xl font-bold')
                ui.button('Add User', icon='add', on_click=lambda: self.show_add_user_dialog()).props('color=primary')

            # Filters
            # with ui.row().classes('w-full gap-4 mb-4'):
            #     role_filter = ui.select(
            #         ['All', 'Student', 'Instructor', 'Admin'],
            #         value='All',
            #         label='Role'
            #     ).classes('w-48')

            #     search_input = ui.input('Search users...').classes('flex-1').props('outlined dense')

            try:
                self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)

                users = self.hub_client.get_users()

                columns = [
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left', 'sortable': True},
                    {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left', 'sortable': True},
                    {'name': 'institution', 'label': 'Institution', 'field': 'institution', 'align': 'left'},
                    {'name': 'created', 'label': 'Created', 'field': 'created', 'align': 'left', 'sortable': True},
                    {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                ]

                rows = [
                    {
                        'id': user['id'],
                        'name': f"{user['first_name']} {user['last_name']}",
                        'email': user['email'],
                        'role': user['role'].capitalize(),
                        'institution': user['institution'] or '-',
                        'created': user['created_at'],
                        'actions': user['id']
                    }
                    for user in users
                ]

                table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn flat dense icon="edit" size="sm" @click="$parent.$emit('edit', props.row)" />
                        <q-btn flat dense icon="delete" color="negative" size="sm" @click="$parent.$emit('delete', props.row)" />
                    </q-td>
                ''')

                def handle_edit(e):
                    ui.notify(f'Edit user: {e.args["name"]}')

                def handle_delete(e):
                    ui.notify(f'Delete user: {e.args["name"]}', type='warning')

                table.on('edit', handle_edit)
                table.on('delete', handle_delete)

            except Exception as e:
                ui.label(f'Error loading users: {str(e)}').classes('text-red-500')

    def show_add_user_dialog(self):
        """Dialog to add a new user"""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Add New User').classes('text-xl font-bold mb-4')

            email = ui.input('Email').classes('w-full')
            first_name = ui.input('First Name').classes('w-full')
            last_name = ui.input('Last Name').classes('w-full')
            role = ui.select(['student', 'instructor', 'admin'], label='Role', value='student').classes('w-full')
            institution = ui.input('Institution').classes('w-full')
            password = ui.input('Temporary Password', password=True).classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Create User', on_click=lambda: self.create_user(
                    email.value, first_name.value, last_name.value,
                    role.value, institution.value, password.value, dialog
                )).props('color=primary')

        dialog.open()

    def create_user(self, email, first_name, last_name, role, institution, password, dialog):
        """Create a new user"""
        try:
            self.hub_client.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                institution=institution or None
            )
            ui.notify(f'User {email} created successfully', type='positive')
            dialog.close()
            ui.navigate.to('/admin/users')  # Refresh page
        except HubClientError as e:
            ui.notify(f'Error creating user: {str(e)}', type='negative')

    def admin_courses(self, request: Request):
        """Course management page"""
        user = self.require_admin(request)
        if not user:
            return

        with ui.header().classes('items-center justify-between bg-indigo-600'):
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin')).props('flat text-color=white')
                ui.label('Course Management').classes('text-xl font-bold text-white ml-2')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')

        with ui.column().classes('w-full max-w-7xl mx-auto p-8'):
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label('Courses').classes('text-3xl font-bold')
                ui.button('Create Course', icon='add', on_click=lambda: self.show_create_course_dialog()).props('color=primary')

            try:
                self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)

                # Course cards
                courses = self.hub_client.get_courses()

                with ui.grid(columns=2).classes('w-full gap-4'):
                    for course in courses:
                        with ui.card().classes('hover:shadow-lg transition-shadow'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                with ui.column():
                                    ui.label(course['name']).classes('text-xl font-bold')
                                    ui.label(f"{course['code']} • {course['semester']}").classes('text-gray-600')

                                ui.button(icon='more_vert').props('flat dense')

                            with ui.row().classes('w-full gap-4 mt-4'):
                                with ui.column().classes('flex-1'):
                                    ui.label('Students').classes('text-xs text-gray-600')
                                    ui.label(str(course['students'])).classes('text-2xl font-bold')

                                with ui.column().classes('flex-1'):
                                    ui.label('Labs').classes('text-xs text-gray-600')
                                    ui.label(str(course['labs'])).classes('text-2xl font-bold')

                            with ui.row().classes('w-full gap-2 mt-4'):
                                ui.button('Manage', on_click=lambda c=course: ui.navigate.to(f'/admin/course/{c["id"]}')).props('flat')
                                ui.button('Enrollments', on_click=lambda c=course: self.show_enrollments(c)).props('flat')

            except Exception as e:
                ui.label(f'Error loading courses: {str(e)}').classes('text-red-500')

    def show_create_course_dialog(self):
        """Dialog to create a new course"""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Create New Course').classes('text-xl font-bold mb-4')

            code = ui.input('Course Code', placeholder='ASTR-101').classes('w-full')
            name = ui.input('Course Name', placeholder='Introduction to Astronomy').classes('w-full')
            semester = ui.input('Semester', placeholder='Fall 2024').classes('w-full')
            institution = ui.input('Institution').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Create', on_click=lambda: self.create_course(
                    code.value, name.value, semester.value, institution.value, dialog
                )).props('color=primary')

        dialog.open()

    def create_course(self, code, name, semester, institution, dialog):
        """Create a new course"""
        try:
            # You'll need to add instructor_id logic
            self.hub_client.create_course(
                code=code,
                name=name,
                semester=semester,
                instructor_id=1,  # Would get from current user or selection
                institution=institution or None
            )
            ui.notify(f'Course {code} created successfully', type='positive')
            dialog.close()
            ui.navigate.to('/admin/courses')
        except HubClientError as e:
            ui.notify(f'Error creating course: {str(e)}', type='negative')

    def show_enrollments(self, course):
        """Show course enrollments dialog"""
        with ui.dialog() as dialog, ui.card().classes('w-[600px]'):
            ui.label(f'Enrollments: {course["name"]}').classes('text-xl font-bold mb-4')

            # Fetch real enrollment data from API
            try:
                enrollments = self.hub_client.get_enrollments(course_id=course['id'])
            except HubClientError as e:
                ui.notify(f'Error fetching enrollments: {str(e)}', type='negative')
                enrollments = []

            if not enrollments:
                ui.label('No students enrolled yet').classes('text-gray-500 my-4')
            else:
                for enrollment in enrollments:
                    user_info = enrollment.get('user', {})
                    with ui.row().classes('w-full items-center py-2 border-b'):
                        ui.icon('account_circle').classes('text-gray-400')
                        with ui.column().classes('flex-1 ml-3'):
                            ui.label(f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}").classes('font-bold')
                            ui.label(user_info.get('email', '')).classes('text-sm text-gray-600')
                            ui.label(f"Role: {enrollment.get('role', 'student')}").classes('text-xs text-gray-500')
                        ui.button(
                            icon='delete',
                            on_click=lambda e=enrollment: self.remove_enrollment(e['id'], dialog)
                        ).props('flat dense color=negative')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Add Students', on_click=lambda: self.show_add_student_dialog(course, dialog)).props('flat')
                ui.button('Close', on_click=dialog.close).props('color=primary')

        dialog.open()

    def remove_enrollment(self, enrollment_id, parent_dialog):
        """Remove an enrollment"""
        try:
            self.hub_client.delete_enrollment(enrollment_id)
            ui.notify('Enrollment removed successfully', type='positive')
            parent_dialog.close()
            # Could refresh the dialog here, or just close it
        except HubClientError as e:
            ui.notify(f'Error removing enrollment: {str(e)}', type='negative')

    def show_add_student_dialog(self, course, parent_dialog):
        """Show dialog to add students to course"""
        ui.notify('Add student dialog not yet implemented', type='info')

    def admin_labs(self, request: Request):
        """Lab management page"""
        user = self.require_admin(request)
        if not user:
            return

        with ui.header().classes('items-center justify-between bg-indigo-600'):
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin')).props('flat text-color=white')
                ui.label('Lab Management').classes('text-xl font-bold text-white ml-2')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')

        with ui.column().classes('w-full max-w-7xl mx-auto p-8'):
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label('Labs').classes('text-3xl font-bold')
                ui.button('Register Lab', icon='add', on_click=lambda: self.show_register_lab_dialog()).props('color=primary')

            try:
                self.hub_client.token = request.cookies.get(self.SESSION_COOKIE_NAME)
                labs = self.hub_client.get_labs()

                for lab in labs:
                    with ui.card().classes('w-full mb-4'):
                        with ui.row().classes('w-full items-start justify-between'):
                            with ui.column().classes('flex-1'):
                                ui.label(lab['name']).classes('text-2xl font-bold mb-2')
                                ui.label(lab['description']).classes('text-gray-600 mb-4')

                                with ui.row().classes('gap-4'):
                                    with ui.column():
                                        ui.label('Slug').classes('text-xs text-gray-600')
                                        ui.label(lab['slug']).classes('font-mono text-sm')

                                    with ui.column():
                                        ui.label('Status').classes('text-xs text-gray-600')
                                        if lab['is_active']:
                                            ui.badge('Active', color='green')
                                        else:
                                            ui.badge('Inactive', color='gray')

                                with ui.row().classes('gap-2 mt-4'):
                                    ui.button('Edit', icon='edit', on_click=lambda lab_item=lab: self.edit_lab(lab_item)).props('flat')
                                    ui.button('View Sessions', on_click=lambda lab_item=lab: self.view_lab_sessions(lab_item)).props('flat')
                                    ui.button(
                                        'Deactivate' if lab['is_active'] else 'Activate',
                                        on_click=lambda lab_item=lab: self.toggle_lab_status(lab_item)
                                    ).props('flat color=orange')

                            ui.button(icon='launch', on_click=lambda lab_item=lab: ui.run_javascript(f"window.open('{lab_item['ui_url']}', '_blank')")).props('flat')

            except Exception as e:
                ui.label(f'Error loading labs: {str(e)}').classes('text-red-500')

    def show_register_lab_dialog(self):
        """Dialog to register a new lab"""
        with ui.dialog() as dialog, ui.card().classes('w-[500px]'):
            ui.label('Register New Lab').classes('text-xl font-bold mb-4')

            slug = ui.input('Slug', placeholder='exoplanet').classes('w-full')
            name = ui.input('Name', placeholder='Exoplanet Transit Lab').classes('w-full')
            description = ui.textarea('Description').classes('w-full')
            ui_url = ui.input('UI URL', placeholder='http://localhost:8013').classes('w-full')
            api_url = ui.input('API URL', placeholder='http://localhost:8020').classes('w-full')
            session_url = ui.input('Session Manager URL', placeholder='http://localhost:8021').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Register', on_click=lambda: self.register_lab(
                    slug.value, name.value, description.value,
                    ui_url.value, api_url.value, session_url.value, dialog
                )).props('color=primary')

        dialog.open()

    def register_lab(self, slug, name, description, ui_url, api_url, session_url, dialog):
        """Register a new lab"""
        try:
            # Use SDK method
            self.hub_client.register_lab(
                slug=slug,
                name=name,
                description=description,
                ui_url=ui_url,
                api_url=api_url,
                session_manager_url=session_url
            )

            ui.notify(f'Lab {name} registered successfully', type='positive')
            dialog.close()
            ui.navigate.to('/admin/labs')
        except HubClientError as e:
            ui.notify(f'Error registering lab: {str(e)}', type='negative')

    def edit_lab(self, lab):
        """Edit lab details"""
        ui.notify(f'Edit {lab["name"]} - Not implemented yet')

    def view_lab_sessions(self, lab):
        """View active sessions for a lab"""
        with ui.dialog() as dialog, ui.card().classes('w-[800px]'):
            ui.label(f'Active Sessions: {lab["name"]}').classes('text-xl font-bold mb-4')

            # Fetch real session data from API
            try:
                sessions = self.hub_client.get_sessions(lab_id=lab['id'])
            except HubClientError as e:
                ui.notify(f'Error fetching sessions: {str(e)}', type='negative')
                sessions = []

            if not sessions:
                ui.label('No active sessions').classes('text-gray-500 my-4')
            else:
                # Create table columns
                columns = [
                    {'name': 'user', 'label': 'Student', 'field': 'user', 'align': 'left'},
                    {'name': 'course', 'label': 'Course', 'field': 'course', 'align': 'left'},
                    {'name': 'started', 'label': 'Started', 'field': 'started', 'align': 'left'},
                    {'name': 'last_activity', 'label': 'Last Activity', 'field': 'last_activity', 'align': 'left'},
                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                ]

                # Prepare rows
                rows = []
                for session in sessions:
                    user_info = session.get('user', {})
                    course_info = session.get('course', {})
                    rows.append({
                        'user': f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}",
                        'course': course_info.get('code', 'N/A') if course_info else 'N/A',
                        'started': session.get('started_at', '')[:16] if session.get('started_at') else '',
                        'last_activity': session.get('last_activity', '')[:16] if session.get('last_activity') else '',
                        'status': 'Completed' if session.get('completed_at') else 'Active',
                    })

                ui.table(columns=columns, rows=rows, row_key='user').classes('w-full')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Close', on_click=dialog.close).props('color=primary')

        dialog.open()

    def toggle_lab_status(self, lab):
        """Toggle lab active status"""
        ui.notify(f'Toggle status for {lab["name"]} - Not implemented yet')

    def admin_analytics(self, request: Request):
        """Analytics and reporting page"""
        user = self.require_admin(request)
        if not user:
            return

        with ui.header().classes('items-center justify-between bg-indigo-600'):
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin')).props('flat text-color=white')
                ui.label('Analytics').classes('text-xl font-bold text-white ml-2')

            with ui.row().classes('items-center gap-4'):
                ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm text-white')

        with ui.column().classes('w-full max-w-7xl mx-auto p-8'):
            ui.label('Analytics & Reporting').classes('text-3xl font-bold mb-8')

        # Time range selector
        with ui.row().classes('w-full mb-6'):
            ui.button('Last 7 Days').props('flat')
            ui.button('Last 30 Days').props('outline')
            ui.button('Last 90 Days').props('flat')
            ui.button('Custom Range').props('flat')

        # Usage stats
        with ui.card().classes('w-full mb-6'):
            ui.label('Lab Usage').classes('text-xl font-bold mb-4')

            # Mock chart data
            ui.label('📊 Chart: Lab sessions over time').classes('text-gray-600 text-center py-12')
            ui.label('(Integrate with charting library like plotly or matplotlib)').classes('text-xs text-gray-400 text-center')

        # Top performing students
        with ui.card().classes('w-full mb-6'):
            ui.label('Top Performing Students').classes('text-xl font-bold mb-4')

            students = [
                {'name': 'Alice Johnson', 'labs_completed': 5, 'avg_score': 95},
                {'name': 'Bob Williams', 'labs_completed': 4, 'avg_score': 88},
                {'name': 'Charlie Brown', 'labs_completed': 4, 'avg_score': 92},
            ]

            columns = [
                {'name': 'name', 'label': 'Student', 'field': 'name', 'align': 'left'},
                {'name': 'completed', 'label': 'Labs Completed', 'field': 'completed', 'align': 'center'},
                {'name': 'score', 'label': 'Avg Score', 'field': 'score', 'align': 'center'},
            ]

            rows = [
                {'name': s['name'], 'completed': s['labs_completed'], 'score': f"{s['avg_score']}%"}
                for s in students
            ]

            ui.table(columns=columns, rows=rows).classes('w-full')

        # Course completion rates
        with ui.card().classes('w-full'):
            ui.label('Course Completion Rates').classes('text-xl font-bold mb-4')

            courses = [
                {'name': 'ASTR-101', 'enrolled': 25, 'completed': 20, 'rate': 80},
                {'name': 'ASTR-201', 'enrolled': 18, 'completed': 12, 'rate': 67},
            ]

            for course in courses:
                with ui.row().classes('w-full items-center mb-4'):
                    ui.label(course['name']).classes('w-32 font-bold')
                    ui.linear_progress(course['rate'] / 100).classes('flex-1')
                    ui.label(f"{course['rate']}%").classes('w-16 text-right')
                    ui.label(f"({course['completed']}/{course['enrolled']})").classes('text-sm text-gray-600 ml-2')
