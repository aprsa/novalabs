from nicegui import ui
from fastapi import Request
from novalabs.client.sdk import SDKClientError
from .session_manager import session_manager


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
    """Lab management with activate/deactivate and ordering"""
    ui.label('Lab Management').classes('text-3xl font-bold mb-4')

    # Container for refreshable content
    labs_container = ui.column().classes('w-full')
    
    async def refresh_labs():
        """Refresh the labs list from database"""
        labs_container.clear()
        with labs_container:
            await render_labs_management()
    
    async def render_labs_management():
        """Render the lab management interface"""
        from novalabs.common.database import init_db
        from novalabs.core.models import Lab, AdminNotification
        
        try:
            await init_db()
            labs = await Lab.all().order_by('sort_order', 'slug')
            
            # Stats row
            with ui.row().classes('w-full justify-between items-center mb-4'):
                active_count = sum(1 for lab in labs if lab.is_active)
                ui.label(f'Total Labs: {len(labs)} ({active_count} active)').classes('text-lg font-semibold')
                
                # Check for unread notifications
                unread_count = await AdminNotification.filter(is_read=False).count()
                if unread_count > 0:
                    with ui.button(on_click=lambda: show_notifications_dialog(refresh_labs)).classes('bg-red-500'):
                        ui.label(f'⚠️ {unread_count} Error(s)').classes('text-white')
            
            if not labs:
                ui.label('No labs found. Run novalabs-loadlabs to discover and load labs.').classes('text-gray-500 italic')
                return
            
            # Labs table
            with ui.column().classes('w-full gap-2'):
                for i, lab in enumerate(labs):
                    await render_lab_row(lab, i, len(labs), refresh_labs)
                    
        except Exception as e:
            ui.label(f'Error loading labs: {str(e)}').classes('text-red-500')
            import traceback
            with ui.expansion('Details').classes('text-xs'):
                ui.code(traceback.format_exc())
    
    async def render_lab_row(lab, index: int, total: int, refresh_callback):
        """Render a single lab management row"""
        from novalabs.core.models import Lab
        
        is_active = lab.is_active
        bg_color = 'bg-white' if is_active else 'bg-gray-100'
        text_color = '' if is_active else 'text-gray-500'
        
        with ui.card().classes(f'w-full p-4 {bg_color}'):
            with ui.row().classes('w-full items-center justify-between'):
                # Lab info
                with ui.column().classes('flex-1'):
                    with ui.row().classes('items-center gap-2'):
                        status_icon = '✓' if is_active else '○'
                        status_color = 'text-green-600' if is_active else 'text-gray-400'
                        ui.label(status_icon).classes(f'{status_color} text-lg')
                        ui.label(lab.title).classes(f'font-bold {text_color}')
                        if lab.version:
                            ui.label(f'v{lab.version}').classes('text-xs text-gray-400 bg-gray-200 px-2 py-0.5 rounded')
                    
                    with ui.row().classes('gap-4 text-sm'):
                        ui.label(f'Slug: {lab.slug}').classes(f'text-gray-500 {text_color}')
                        if lab.content_path:
                            source = 'user' if '.novalabs' in lab.content_path else 'bundled'
                            source_color = 'text-blue-500' if source == 'user' else 'text-gray-400'
                            ui.label(f'[{source}]').classes(f'{source_color} text-xs')
                
                # Controls
                with ui.row().classes('items-center gap-2'):
                    # Sort order display
                    ui.label(f'#{lab.sort_order}').classes('text-gray-400 text-sm w-8 text-center')
                    
                    # Move up button
                    up_disabled = index == 0
                    ui.button(
                        '↑',
                        on_click=lambda l=lab: move_lab(l, 'up', refresh_callback)
                    ).props(f'flat dense {"disabled" if up_disabled else ""}').classes('w-8')
                    
                    # Move down button
                    down_disabled = index == total - 1
                    ui.button(
                        '↓',
                        on_click=lambda l=lab: move_lab(l, 'down', refresh_callback)
                    ).props(f'flat dense {"disabled" if down_disabled else ""}').classes('w-8')
                    
                    # Active toggle
                    async def toggle_active(lab_obj, value):
                        lab_obj.is_active = value
                        await lab_obj.save()
                        status = 'activated' if value else 'deactivated'
                        ui.notify(f'Lab "{lab_obj.title}" {status}')
                        await refresh_callback()
                    
                    ui.switch(
                        'Active',
                        value=is_active,
                        on_change=lambda e, l=lab: toggle_active(l, e.value)
                    )
    
    async def move_lab(lab, direction: str, refresh_callback):
        """Move a lab up or down in sort order"""
        from novalabs.core.models import Lab
        
        all_labs = await Lab.all().order_by('sort_order', 'slug')
        lab_list = list(all_labs)
        
        # Find current index
        current_idx = next((i for i, l in enumerate(lab_list) if l.id == lab.id), None)
        if current_idx is None:
            return
        
        # Calculate target index
        if direction == 'up' and current_idx > 0:
            target_idx = current_idx - 1
        elif direction == 'down' and current_idx < len(lab_list) - 1:
            target_idx = current_idx + 1
        else:
            return
        
        # Swap sort orders
        target_lab = lab_list[target_idx]
        lab.sort_order, target_lab.sort_order = target_lab.sort_order, lab.sort_order
        
        await lab.save()
        await target_lab.save()
        
        ui.notify(f'Moved "{lab.title}" {direction}')
        await refresh_callback()
    
    async def show_notifications_dialog(refresh_callback):
        """Show admin notifications dialog"""
        from novalabs.core.models import AdminNotification
        
        with ui.dialog() as dialog, ui.card().classes('w-[800px] max-h-[600px]'):
            ui.label('Admin Notifications').classes('text-xl font-bold mb-4')
            
            notifications = await AdminNotification.filter(is_read=False).order_by('-created_at').limit(20)
            
            if not notifications:
                ui.label('No unread notifications').classes('text-gray-500 italic')
            else:
                for notif in notifications:
                    severity_colors = {
                        'error': 'border-red-500 bg-red-50',
                        'warning': 'border-yellow-500 bg-yellow-50',
                        'info': 'border-blue-500 bg-blue-50',
                    }
                    color = severity_colors.get(notif.severity, 'border-gray-500')
                    
                    with ui.card().classes(f'w-full p-3 mb-2 border-l-4 {color}'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column():
                                ui.label(notif.title).classes('font-bold')
                                ui.label(notif.message).classes('text-sm text-gray-600')
                                ui.label(f'Created: {notif.created_at}').classes('text-xs text-gray-400')
                            
                            async def mark_read(n=notif):
                                n.is_read = True
                                await n.save()
                                ui.notify('Marked as read')
                                dialog.close()
                                await refresh_callback()
                            
                            ui.button('✓', on_click=mark_read).props('flat dense')
                        
                        if notif.traceback:
                            with ui.expansion('Traceback').classes('text-xs'):
                                ui.code(notif.traceback).classes('text-xs')
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Close', on_click=dialog.close).props('flat')
        
        dialog.open()
    
    # Initial render
    import asyncio
    asyncio.create_task(refresh_labs())


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
