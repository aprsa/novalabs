"""
Lab page - Handles lab content display and interaction.

Dynamically loads the appropriate lab UI class based on:
1. Explicit declaration in lab.toml [ui].class
2. Convention: {lab_dir}/ui.py with {PascalSlug}Lab class  
3. Default: BaseLabUI

The lab page instantiates both the logic layer (BaseLab) and the
presentation layer (BaseLabUI or custom), then renders the UI.
"""

import logging
from pathlib import Path

from nicegui import ui
from fastapi import Request, Query

from novalabs.client.sdk import SDKClientError
from novalabs.common.database import init_db
from novalabs.core.models import Lab
from novalabs.core.labs import BaseLab
from novalabs.core.ui import resolve_ui_class, import_class, BaseLabUI
from .session_manager import session_manager

logger = logging.getLogger(__name__)


async def lab_page(request: Request, lab_ref: str = Query(...)):
    """
    Main lab page - loads and displays a lab.

    Args:
        request: FastAPI request
        lab_ref: Lab slug (from query parameter)
    """
    # Require authentication
    user = session_manager.require_auth(request)
    if not user:
        ui.navigate.to('/login')
        return

    # Get authenticated client
    client = session_manager.get_authenticated_client(request)
    if not client:
        ui.label('Session expired. Please login again.').classes('text-red-500')
        return

    # Header
    with ui.header().classes('items-center justify-between'):
        ui.button('← Back to Dashboard', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label(f"🔭 {lab_ref}").classes('text-xl font-bold')
        ui.label(f"{user['first_name']} {user['last_name']}").classes('text-sm')

    # Main content area
    with ui.column().classes('w-full h-screen overflow-hidden'):
        try:
            await init_db()

            # Get lab from database
            lab = await Lab.get_or_none(slug=lab_ref)

            if not lab:
                ui.label(f'Lab "{lab_ref}" not found').classes('text-red-500 text-lg p-4')
                return
            
            # Check if lab is active
            if not lab.is_active:
                ui.label(f'Lab "{lab_ref}" is not currently available').classes('text-orange-500 text-lg p-4')
                return

            # Resolve UI class (runtime resolution)
            lab_path = Path(lab.content_path) if lab.content_path else None
            
            if lab_path and lab_path.exists():
                ui_class_path = resolve_ui_class(lab_path)
                logger.debug(f"Resolved UI class for {lab_ref}: {ui_class_path}")
            else:
                ui_class_path = "novalabs.core.ui.base:BaseLabUI"
                logger.debug(f"No content path for {lab_ref}, using default BaseLabUI")

            try:
                LabUIClass = import_class(ui_class_path)
            except (ImportError, AttributeError) as e:
                # Let it fail loudly - this needs to be fixed
                logger.error(f"Failed to import UI class '{ui_class_path}' for {lab_ref}: {e}")
                raise

            logger.info(f"Loading lab {lab_ref} with UI class: {LabUIClass.__name__}")

            # Initialize logic layer
            lab_logic = BaseLab(user_id=user['id'], lab=lab)
            await lab_logic.init()

            # Initialize UI layer
            lab_ui = LabUIClass(lab_logic)

            # Render the lab UI
            await lab_ui.render()

            # Notify hub that lab started (for tracking)
            try:
                client.start_lab(lab_ref)
            except SDKClientError:
                pass  # Silent fail if already started

        except Exception as e:
            logger.exception(f"Lab page error for {lab_ref}")
            ui.label(f'Error loading lab: {str(e)}').classes('text-red-500 text-lg p-4')
            
            # Show details for debugging (could be hidden in production)
            with ui.expansion('Error Details').classes('text-sm text-gray-500'):
                import traceback
                ui.code(traceback.format_exc()).classes('text-xs')
