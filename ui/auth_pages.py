from nicegui import ui
from fastapi import Request
from client.sdk import AuthenticationError, SDKClientError
from session_manager import session_manager


def login_page(request: Request):
    """Login page"""
    # Check if already logged in
    user = session_manager.get_current_user(request)
    if user:
        ui.navigate.to('/')
        return

    with ui.column().classes('absolute-center items-center'):
        ui.label('NovaLabs Hub').classes('text-4xl font-bold mb-2')
        ui.label('Sign in to access your labs').classes('text-gray-600 mb-8')

        with ui.card().classes('w-96 p-6'):
            email_input = ui.input('Email', placeholder='your.email@example.com').classes('w-full')
            email_input.props('autofocus')

            password_input = ui.input(
                'Password',
                password=True,
                password_toggle_button=True
            ).classes('w-full')

            error_label = ui.label('').classes('text-red-500 text-sm')
            error_label.visible = False

            def handle_login():
                error_label.visible = False

                if not email_input.value or not password_input.value:
                    error_label.text = 'Please enter email and password'
                    error_label.visible = True
                    return

                try:
                    # Login and create server-side session
                    session_id = session_manager.login(email_input.value, password_input.value)
                    session_manager.set_session_cookie(session_id)
                except AuthenticationError:
                    error_label.text = 'Invalid email or password'
                    error_label.visible = True
                except SDKClientError as e:
                    error_label.text = f'Error: {str(e)}'
                    error_label.visible = True

            password_input.on('keydown.enter', handle_login)
            ui.button('Sign In', on_click=handle_login).classes('w-full').props('color=primary')

        with ui.row().classes('mt-4'):
            ui.label("Don't have an account?").classes('text-gray-600')
            ui.link('Register', '/register').classes('text-blue-600')


def register_page(request: Request):
    """Registration page"""
    user = session_manager.get_current_user(request)
    if user:
        ui.navigate.to('/')
        return

    with ui.column().classes('absolute-center items-center'):
        ui.label('Create Account').classes('text-4xl font-bold mb-2')
        ui.label('Join NovaLabs').classes('text-gray-600 mb-8')

        with ui.card().classes('w-96 p-6'):
            first_name = ui.input('First Name').classes('w-full')
            last_name = ui.input('Last Name').classes('w-full')
            email = ui.input('Email').classes('w-full')
            institution = ui.input('Institution (optional)').classes('w-full')
            password = ui.input('Password', password=True).classes('w-full')
            confirm = ui.input('Confirm Password', password=True).classes('w-full')

            error_label = ui.label('').classes('text-red-500 text-sm')
            error_label.visible = False

            def handle_register():
                error_label.visible = False

                # Validation
                if not all([first_name.value, last_name.value, email.value, password.value]):
                    error_label.text = 'All fields except institution are required'
                    error_label.visible = True
                    return

                if password.value != confirm.value:
                    error_label.text = 'Passwords do not match'
                    error_label.visible = True
                    return

                if len(password.value) < 8:
                    error_label.text = 'Password must be at least 8 characters'
                    error_label.visible = True
                    return

                try:
                    # Register via SDK
                    client = session_manager.create_client()
                    client.register(
                        email=email.value,
                        password=password.value,
                        first_name=first_name.value,
                        last_name=last_name.value,
                        institution=institution.value or None
                    )

                    # Auto-login after registration
                    session_id = session_manager.login(email.value, password.value)
                    session_manager.set_session_cookie(session_id)

                except SDKClientError as e:
                    error_label.text = f'Registration failed: {str(e)}'
                    error_label.visible = True

            ui.button('Create Account', on_click=handle_register).classes('w-full').props('color=primary')

        with ui.row().classes('mt-4'):
            ui.label('Already have an account?').classes('text-gray-600')
            ui.link('Sign In', '/login').classes('text-blue-600')
