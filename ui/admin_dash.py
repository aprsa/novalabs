from nicegui import ui
from fastapi import Request
from client.sdk import SDKClientError
from session_manager import session_manager


def admin_dashboard(request: Request):
    """Main admin dashboard with tabbed interface"""
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
            ui.label(f"{user['first_name']} {user['last_name']} ({user['role']})").classes('text-sm text-white')
            ui.button('Logout', on_click=lambda: logout(request)).props('flat text-color=white')

    # Main content with tabs
    with ui.column().classes('w-full p-8'):
        with ui.tabs().classes('w-full') as tabs:
            overview_tab = ui.tab('Overview')
            users_tab = ui.tab('Users')
            labs_tab = ui.tab('Labs')
            progress_tab = ui.tab('Progress')
            sessions_tab = ui.tab('Sessions')

        with ui.tab_panels(tabs, value=overview_tab).classes('w-full'):
            # Overview Tab
            with ui.tab_panel(overview_tab):
                show_overview(client)

            # Users Tab
            with ui.tab_panel(users_tab):
                show_users_crud(client)

            # Labs Tab
            with ui.tab_panel(labs_tab):
                show_labs_view(client)

            # Progress Tab
            with ui.tab_panel(progress_tab):
                show_progress_view(client)

            # Sessions Tab
            with ui.tab_panel(sessions_tab):
                show_sessions_view(client)


def show_overview(client):
    """Dashboard overview with statistics"""
    ui.label('Dashboard Overview').classes('text-3xl font-bold mb-8')

    try:
        users = client.get_users()
        labs = client.get_labs()

        # Count users by role
        students = [u for u in users if u['role'] == 'student']
        instructors = [u for u in users if u['role'] == 'instructor']
        admins = [u for u in users if u['role'] == 'admin']

        # Stats cards
        with ui.row().classes('w-full gap-4 mb-8'):
            with ui.card().classes('flex-1 p-4'):
                ui.label('Total Users').classes('text-gray-600 text-sm')
                ui.label(str(len(users))).classes('text-4xl font-bold text-indigo-600')
                ui.label(f'Students: {len(students)} | Instructors: {len(instructors)} | Admins: {len(admins)}').classes('text-xs text-gray-500 mt-2')

            with ui.card().classes('flex-1 p-4'):
                ui.label('Available Labs').classes('text-gray-600 text-sm')
                ui.label(str(len(labs))).classes('text-4xl font-bold text-green-600')

        # Recent users
        with ui.card().classes('w-full p-4'):
            ui.label('Recent Users').classes('text-xl font-bold mb-4')

            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'},
                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
                {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left'},
                {'name': 'rank', 'label': 'Rank', 'field': 'rank', 'align': 'left'},
            ]

            rows = [
                {
                    'id': u['id'],
                    'email': u['email'],
                    'name': f"{u['first_name']} {u['last_name']}",
                    'role': u['role'],
                    'rank': u['rank']
                }
                for u in users[-10:]  # Last 10 users
            ]

            ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

    except SDKClientError as e:
        ui.label(f'Error loading data: {str(e)}').classes('text-red-500')


def show_users_crud(client):
    """User management with full CRUD"""
    ui.label('User Management').classes('text-3xl font-bold mb-4')

    # Container for user list (will be refreshed)
    users_container = ui.column().classes('w-full')

    def refresh_users():
        """Refresh the user list"""
        users_container.clear()
        with users_container:
            try:
                users = client.get_users()

                # Add user button
                with ui.row().classes('w-full justify-end mb-4'):
                    ui.button('Add New User', on_click=lambda: show_add_user_dialog(client, refresh_users)).props('color=primary')

                # Users table
                columns = [
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                    {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left', 'sortable': True},
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left', 'sortable': True},
                    {'name': 'rank', 'label': 'Rank', 'field': 'rank', 'align': 'left', 'sortable': True},
                    {'name': 'score', 'label': 'Total Score', 'field': 'score', 'align': 'right', 'sortable': True},
                    {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                ]

                rows = [
                    {
                        'id': u['id'],
                        'email': u['email'],
                        'name': f"{u['first_name']} {u['last_name']}",
                        'role': u['role'],
                        'rank': u['rank'],
                        'score': f"{u['total_score']:.1f}",
                        'user_data': u  # Store full user data
                    }
                    for u in users
                ]

                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key='id',
                    pagination={'rowsPerPage': 20, 'sortBy': 'id', 'descending': True}
                ).classes('w-full')

                # Add action buttons in each row
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn size="sm" flat dense icon="visibility" color="primary" />
                        <q-btn size="sm" flat dense icon="edit" color="orange" />
                        <q-btn size="sm" flat dense icon="delete" color="red" />
                    </q-td>
                ''')

                # Handle row click to view details
                def handle_row_click(e):
                    user_data = e.args['user_data']
                    show_user_details_dialog(client, user_data, refresh_users)

                table.on('rowClick', handle_row_click)

            except SDKClientError as e:
                ui.label(f'Error loading users: {str(e)}').classes('text-red-500')

    refresh_users()


def show_add_user_dialog(client, refresh_callback):
    """Dialog to add a new user"""
    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label('Add New User').classes('text-xl font-bold mb-4')
        
        ui.label('Note: New users are created as students by default.').classes('text-xs text-gray-500 mb-2')
        
        email_input = ui.input('Email', placeholder='user@example.com').classes('w-full')
        password_input = ui.input('Password', password=True, placeholder='Min 8 characters').classes('w-full')
        first_name_input = ui.input('First Name').classes('w-full')
        last_name_input = ui.input('Last Name').classes('w-full')
        
        error_label = ui.label('').classes('text-red-500')
        
        def create_user():
            try:
                client.register(
                    email=email_input.value,
                    password=password_input.value,
                    first_name=first_name_input.value,
                    last_name=last_name_input.value
                )
                ui.notify('User created successfully!', type='positive')
                dialog.close()
                refresh_callback()
            except SDKClientError as e:
                error_label.text = f'Error: {str(e)}'
        
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancel', on_click=dialog.close).props('flat')
            ui.button('Create', on_click=create_user).props('color=primary')
    
    dialog.open()


def show_user_details_dialog(client, user_data, refresh_callback):
    """Dialog to view/edit user details"""
    with ui.dialog() as dialog, ui.card().classes('w-[600px]'):
        ui.label(f"User Details: {user_data['email']}").classes('text-xl font-bold mb-4')
        
        # Display user information
        with ui.column().classes('w-full gap-2 mb-4'):
            ui.label(f"ID: {user_data['id']}").classes('text-sm')
            ui.label(f"Email: {user_data['email']}").classes('text-sm')
            ui.label(f"Name: {user_data['first_name']} {user_data['last_name']}").classes('text-sm')
            ui.label(f"Role: {user_data['role']}").classes('text-sm font-bold text-indigo-600')
            ui.label(f"Rank: {user_data['rank']}").classes('text-sm')
            ui.label(f"Total Score: {user_data['total_score']:.1f}").classes('text-sm')
            ui.label(f"Bonus Points: {user_data['total_bonus_points']:.1f}").classes('text-sm')
        
        ui.separator()
        
        # View user progress
        ui.label('User Progress').classes('text-lg font-bold mt-4 mb-2')
        
        try:
            progress_data = client.get_user_progress(user_data['id'])
            
            if progress_data.get('labs'):
                prog_columns = [
                    {'name': 'lab', 'label': 'Lab', 'field': 'lab', 'align': 'left'},
                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
                    {'name': 'score', 'label': 'Score', 'field': 'score', 'align': 'right'},
                    {'name': 'attempts', 'label': 'Attempts', 'field': 'attempts', 'align': 'right'},
                ]
                
                prog_rows = [
                    {
                        'lab': entry['meta']['name'],
                        'status': entry['progress']['status'],
                        'score': f"{entry['progress']['score']:.1f}" if entry['progress']['score'] is not None else '-',
                        'attempts': entry['progress']['attempts']
                    }
                    for entry in progress_data['labs']
                    if entry['progress']['status'] != 'locked'  # Only show started/completed labs
                ]
                
                if prog_rows:
                    ui.table(columns=prog_columns, rows=prog_rows, row_key='lab').classes('w-full')
                else:
                    ui.label('No progress yet').classes('text-gray-500 italic')
            else:
                ui.label('No progress yet').classes('text-gray-500 italic')
        
        except SDKClientError as e:
            ui.label(f'Error loading progress: {str(e)}').classes('text-red-500 text-sm')
        
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Close', on_click=dialog.close).props('flat')
    
    dialog.open()


def show_labs_view(client):
    """View all labs"""
    ui.label('Labs').classes('text-3xl font-bold mb-4')
    
    try:
        labs = client.get_labs()
        
        with ui.row().classes('w-full justify-end mb-4'):
            ui.label(f'Total Labs: {len(labs)}').classes('text-lg font-semibold')
        
        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
            {'name': 'ref', 'label': 'Ref', 'field': 'ref', 'align': 'left', 'sortable': True},
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
            {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left', 'sortable': True},
            {'name': 'sequence', 'label': 'Sequence', 'field': 'sequence', 'align': 'center', 'sortable': True},
            {'name': 'bonus', 'label': 'Has Bonus', 'field': 'bonus', 'align': 'center'},
            {'name': 'prerequisites', 'label': 'Prerequisites', 'field': 'prerequisites', 'align': 'left'},
        ]
        
        rows = [
            {
                'id': lab['id'],
                'ref': lab['ref'],
                'name': lab['name'],
                'category': lab['category'],
                'sequence': lab['sequence_order'],
                'bonus': '✓' if lab['has_bonus_challenge'] else '',
                'prerequisites': ', '.join(lab['prerequisite_refs']) if lab['prerequisite_refs'] else 'None'
            }
            for lab in labs
        ]
        
        ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            pagination={'rowsPerPage': 20, 'sortBy': 'sequence'}
        ).classes('w-full')
        
    except SDKClientError as e:
        ui.label(f'Error loading labs: {str(e)}').classes('text-red-500')


def show_progress_view(client):
    """View all user progress entries"""
    ui.label('User Progress Entries').classes('text-3xl font-bold mb-4')
    
    # User selector
    user_select_container = ui.column().classes('w-full mb-4')
    progress_container = ui.column().classes('w-full')
    
    def load_users_dropdown():
        user_select_container.clear()
        with user_select_container:
            try:
                users = client.get_users()
                user_options = {
                    f"{u['first_name']} {u['last_name']} ({u['email']})": u['id']
                    for u in users
                }
                
                def on_user_select(e):
                    if e.value:
                        user_id = user_options[e.value]
                        load_user_progress(user_id)
                
                ui.select(
                    label='Select User to View Progress',
                    options=list(user_options.keys()),
                    on_change=on_user_select
                ).classes('w-full')
                
            except SDKClientError as e:
                ui.label(f'Error loading users: {str(e)}').classes('text-red-500')
    
    def load_user_progress(user_id):
        progress_container.clear()
        with progress_container:
            try:
                progress_data = client.get_user_progress(user_id)
                user_info = progress_data['user']
                
                # User summary
                with ui.card().classes('w-full p-4 mb-4'):
                    ui.label(f"{user_info['first_name']} {user_info['last_name']}").classes('text-xl font-bold')
                    rank_score_text = (
                        f"Rank: {user_info['rank']} | "
                        f"Total Score: {user_info['total_score']:.1f} | "
                        f"Bonus: {user_info['total_bonus_points']:.1f}"
                    )
                    ui.label(rank_score_text).classes('text-sm text-gray-600')
                
                # Progress table
                if progress_data.get('labs'):
                    columns = [
                        {'name': 'lab', 'label': 'Lab', 'field': 'lab', 'align': 'left'},
                        {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
                        {'name': 'score', 'label': 'Score', 'field': 'score', 'align': 'right'},
                        {'name': 'bonus', 'label': 'Bonus', 'field': 'bonus', 'align': 'right'},
                        {'name': 'attempts', 'label': 'Attempts', 'field': 'attempts', 'align': 'right'},
                        {'name': 'started', 'label': 'Started', 'field': 'started', 'align': 'left'},
                        {'name': 'completed', 'label': 'Completed', 'field': 'completed', 'align': 'left'},
                    ]
                    
                    rows = [
                        {
                            'lab': f"{entry['meta']['name']} ({entry['meta']['ref']})",
                            'status': entry['progress']['status'],
                            'score': f"{entry['progress']['score']:.1f}" if entry['progress']['score'] is not None else '-',
                            'bonus': f"{entry['progress']['bonus_points']:.1f}" if entry['progress']['bonus_points'] is not None else '-',
                            'attempts': entry['progress']['attempts'],
                            'started': entry['progress']['started_at'] or '-',
                            'completed': entry['progress']['completed_at'] or '-',
                        }
                        for entry in progress_data['labs']
                        if entry['progress']['status'] != 'locked'  # Only show non-locked labs
                    ]
                    
                    if rows:
                        ui.table(columns=columns, rows=rows, row_key='lab').classes('w-full')
                    else:
                        ui.label('No progress entries for this user').classes('text-gray-500 italic')
                else:
                    ui.label('No progress entries for this user').classes('text-gray-500 italic')
                
            except SDKClientError as e:
                ui.label(f'Error loading progress: {str(e)}').classes('text-red-500')
    
    load_users_dropdown()


def show_sessions_view(client):
    """View all active sessions"""
    ui.label('Active Sessions').classes('text-3xl font-bold mb-4')
    
    # User selector
    user_select_container = ui.column().classes('w-full mb-4')
    sessions_container = ui.column().classes('w-full')
    
    def load_users_dropdown():
        user_select_container.clear()
        with user_select_container:
            try:
                users = client.get_users()
                user_options = {
                    f"{u['first_name']} {u['last_name']} ({u['email']})": u['id']
                    for u in users
                }
                
                def on_user_select(e):
                    if e.value:
                        user_id = user_options[e.value]
                        load_user_sessions(user_id)
                
                ui.select(
                    label='Select User to View Sessions',
                    options=list(user_options.keys()),
                    on_change=on_user_select
                ).classes('w-full')
                
            except SDKClientError as e:
                ui.label(f'Error loading users: {str(e)}').classes('text-red-500')
    
    def load_user_sessions(user_id):
        sessions_container.clear()
        with sessions_container:
            try:
                sessions = client.get_user_sessions(user_id)
                
                if sessions:
                    columns = [
                        {'name': 'session_id', 'label': 'Session ID', 'field': 'session_id', 'align': 'left'},
                        {'name': 'created', 'label': 'Created', 'field': 'created', 'align': 'left'},
                        {'name': 'last_activity', 'label': 'Last Activity', 'field': 'last_activity', 'align': 'left'},
                        {'name': 'expires', 'label': 'Expires', 'field': 'expires', 'align': 'left'},
                    ]
                    
                    rows = [
                        {
                            'session_id': s['session_id'][:16] + '...',
                            'created': s['created_at'],
                            'last_activity': s['last_activity'],
                            'expires': s['expires_at'],
                        }
                        for s in sessions
                    ]
                    
                    ui.table(columns=columns, rows=rows, row_key='session_id').classes('w-full')
                else:
                    ui.label('No active sessions for this user').classes('text-gray-500 italic')
                
            except SDKClientError as e:
                ui.label(f'Error loading sessions: {str(e)}').classes('text-red-500')
    
    load_users_dropdown()


def logout(request: Request):
    """Logout helper"""
    session_manager.logout(request)
    session_manager.clear_session_cookie()
