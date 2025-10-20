from nicegui import ui
from fastapi import Request
from client.sdk import SDKClientError
from session_manager import session_manager


def student_dashboard(request: Request):
    """Main student dashboard"""
    user = session_manager.require_auth(request)
    if not user:
        return

    # Redirect admins to admin dashboard
    if user['role'] == 'admin':
        ui.navigate.to('/admin')
        return

    # Header
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center'):
            ui.label('🔭 NovaLabs').classes('text-xl font-bold')

        with ui.row().classes('items-center gap-4'):
            ui.button('🌌 Cosmic View', on_click=lambda: ui.navigate.to('/cosmic')).props('flat color=primary')
            ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm')
            ui.button('Logout', on_click=lambda: logout(request)).props('flat dense')

    # Main content
    with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
        ui.label(f"Hello, {user['first_name']}!").classes('text-3xl font-bold mb-2')
        ui.label(f"{user['institution'] or 'Student'}").classes('text-gray-600 mb-8')

        # Get authenticated client for API calls
        client = session_manager.get_authenticated_client(request)
        if not client:
            ui.label('Session expired. Please login again.').classes('text-red-500')
            return

        try:
            # Fetch user progress data
            progress_data = client.get_my_progress()
            labs_with_progress = progress_data.get('labs', [])

            # Labs Section
            with ui.card().classes('w-full'):
                ui.label('Your Labs').classes('text-2xl font-bold mb-4')

                if not labs_with_progress:
                    ui.label('No labs available yet.').classes('text-gray-600')
                else:
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        for item in labs_with_progress:
                            lab = item['meta']
                            progress = item.get('progress')
                            
                            with ui.card().classes('hover:shadow-lg transition-shadow'):
                                ui.label(lab['name']).classes('text-xl font-bold mb-2')
                                ui.label(lab['description']).classes('text-gray-600 text-sm mb-4')

                                # Display status and score
                                if progress:
                                    status = progress.get('status', 'locked')
                                    ui.label(f"Status: {status.replace('_', ' ').title()}").classes('text-sm mb-2')
                                    
                                    if progress.get('score') is not None:
                                        ui.label(f"Score: {progress['score']:.1f}%").classes('text-sm font-bold text-green-600')
                                    
                                    if status == 'unlocked':
                                        ui.button(
                                            'Start Lab',
                                            on_click=lambda lab_ref=lab['ref']: start_lab(client, lab_ref)
                                        ).props('color=primary')
                                    elif status == 'in_progress':
                                        ui.button(
                                            'Continue',
                                            on_click=lambda url=lab.get('ui_url'): launch_lab_ui(url)
                                        ).props('color=orange')
                                    elif status == 'completed':
                                        ui.button(
                                            'Retake',
                                            on_click=lambda lab_ref=lab['ref']: start_lab(client, lab_ref)
                                        ).props('outline color=primary')
                                else:
                                    ui.label('Status: Locked').classes('text-sm text-gray-500')

        except SDKClientError as e:
            ui.label(f'Error loading dashboard: {str(e)}').classes('text-red-500')


def start_lab(client, lab_ref: str):
    """Start a lab (marks as in_progress)"""
    try:
        client.start_lab(lab_ref)
        ui.notify('Lab started!', type='positive')
        ui.navigate.reload()
    except SDKClientError as e:
        ui.notify(f'Error starting lab: {str(e)}', type='negative')


def launch_lab_ui(ui_url: str):
    """Launch lab UI in new tab"""
    if ui_url:
        ui.run_javascript(f"window.open('{ui_url}', '_blank')")
        ui.notify('Opening lab...', type='positive')
    else:
        ui.notify('Lab UI URL not available', type='warning')


def logout(request: Request):
    """Logout and clear session"""
    session_manager.logout(request)
    session_manager.clear_session_cookie()
