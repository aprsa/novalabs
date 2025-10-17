from nicegui import ui
from fastapi import Request
from client.sdk import AuthenticationError, HubClientError
from base import PageBase


# ============================================================================
# Authentication Pages Class
# ============================================================================

class AuthPages(PageBase):
    """Authentication page implementations"""

    def login_page(self, request: Request):
        """Login page"""
        # Already logged in?
        user = self.get_current_user(request)
        if user:
            ui.navigate.to('/')
            return

        with ui.column().classes('absolute-center items-center'):
            ui.label('NovaLabs Hub').classes('text-4xl font-bold mb-2')
            ui.label('Sign in to access your Nova space').classes('text-gray-600 mb-8')

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
                        token = self.hub_client.login(email_input.value, password_input.value)
                        self.set_auth_cookie(token)
                    except AuthenticationError:
                        error_label.text = 'Invalid email or password'
                        error_label.visible = True
                    except HubClientError as e:
                        error_label.text = f'Error: {str(e)}'
                        error_label.visible = True

                # Enter key triggers login
                password_input.on('keydown.enter', handle_login)

                ui.button('Sign In', on_click=handle_login).classes('w-full').props('color=primary')

            with ui.row().classes('mt-4'):
                ui.label("Don't have an account?").classes('text-gray-600')
                ui.link('Register', '/register').classes('text-blue-600')

    def register_page(self, request: Request):
        """Registration page"""
        # Already logged in?
        user = self.get_current_user(request)
        if user:
            ui.navigate.to('/')
            return

        with ui.column().classes('absolute-center items-center'):
            ui.label('Create Account').classes('text-4xl font-bold mb-2')
            ui.label('Join NovaLabs to access educational labs').classes('text-gray-600 mb-8')

            with ui.card().classes('w-96 p-6'):
                first_name_input = ui.input('First Name').classes('w-full')
                last_name_input = ui.input('Last Name').classes('w-full')
                email_input = ui.input('Email', placeholder='your.email@example.com').classes('w-full')
                institution_input = ui.input('Institution (optional)', placeholder='Your University').classes('w-full')
                password_input = ui.input('Password', password=True, password_toggle_button=True).classes('w-full')
                confirm_input = ui.input('Confirm Password', password=True, password_toggle_button=True).classes('w-full')

                error_label = ui.label('').classes('text-red-500 text-sm')
                error_label.visible = False

                def handle_register():
                    error_label.visible = False

                    # Validation
                    if not all([first_name_input.value, last_name_input.value,
                               email_input.value, password_input.value]):
                        error_label.text = 'All fields except institution are required'
                        error_label.visible = True
                        return

                    if password_input.value != confirm_input.value:
                        error_label.text = 'Passwords do not match'
                        error_label.visible = True
                        return

                    if len(password_input.value) < 8:
                        error_label.text = 'Password must be at least 8 characters'
                        error_label.visible = True
                        return

                    try:
                        # Register via SDK
                        self.hub_client.register(
                            email=email_input.value,
                            password=password_input.value,
                            first_name=first_name_input.value,
                            last_name=last_name_input.value,
                            institution=institution_input.value or None
                        )

                        # Auto-login after registration
                        token = self.hub_client.login(email_input.value, password_input.value)
                        self.set_auth_cookie(token)

                    except HubClientError as e:
                        error_label.text = f'Registration failed: {str(e)}'
                        error_label.visible = True

                ui.button('Create Account', on_click=handle_register).classes('w-full').props('color=primary')

            with ui.row().classes('mt-4'):
                ui.label('Already have an account?').classes('text-gray-600')
                ui.link('Sign In', '/login').classes('text-blue-600')
