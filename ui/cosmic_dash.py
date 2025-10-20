"""
Cosmic Journey Dashboard - A visually stunning astronomy-themed interface
showing labs as a journey from Earth through the Solar System to distant galaxies
"""
from nicegui import ui
from fastapi import Request
from client.sdk import SDKClientError
from session_manager import session_manager


def cosmic_dashboard(request: Request):
    """Astronomy-themed dashboard with visual lab journey"""
    user = session_manager.require_auth(request)
    if not user:
        return

    client = session_manager.get_authenticated_client(request)
    if not client:
        ui.label('Session expired. Please login again.').classes('text-red-500')
        return

    # Custom CSS for astronomy theme
    ui.add_head_html('''
        <style>
            body {
                margin: 0;
                overflow: hidden;
            }

            .cosmic-bg {
                background: linear-gradient(to bottom, 
                    #000000 0%, 
                    #0a0a1a 30%, 
                    #1a0a2e 60%, 
                    #000814 100%
                );
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                overflow: hidden;
            }

            .stars {
                position: absolute;
                width: 100%;
                height: 100%;
                background-image: 
                    radial-gradient(2px 2px at 20% 30%, white, transparent),
                    radial-gradient(2px 2px at 60% 70%, white, transparent),
                    radial-gradient(1px 1px at 50% 50%, white, transparent),
                    radial-gradient(1px 1px at 80% 10%, white, transparent),
                    radial-gradient(2px 2px at 90% 60%, white, transparent),
                    radial-gradient(1px 1px at 33% 80%, white, transparent),
                    radial-gradient(1px 1px at 15% 60%, white, transparent),
                    radial-gradient(3px 3px at 45% 25%, rgba(255, 255, 255, 0.8), transparent),
                    radial-gradient(2px 2px at 75% 85%, rgba(255, 255, 255, 0.7), transparent),
                    radial-gradient(1px 1px at 10% 40%, white, transparent),
                    radial-gradient(2px 2px at 85% 45%, white, transparent),
                    radial-gradient(1px 1px at 30% 90%, white, transparent),
                    radial-gradient(3px 3px at 65% 15%, rgba(200, 220, 255, 0.9), transparent),
                    radial-gradient(2px 2px at 95% 75%, rgba(255, 240, 200, 0.8), transparent);
                background-repeat: repeat;
                background-size: 400px 400px, 550px 550px, 300px 300px, 600px 600px, 450px 450px, 350px 350px, 500px 500px,
                                 700px 700px, 400px 400px, 250px 250px, 650px 650px, 380px 380px, 520px 520px, 480px 480px;
                animation: twinkle 8s ease-in-out infinite;
                z-index: 1;
            }
            
            .stars::before {
                content: '';
                position: absolute;
                width: 100%;
                height: 100%;
                background-image: 
                    radial-gradient(1px 1px at 25% 60%, rgba(255, 255, 255, 0.6), transparent),
                    radial-gradient(2px 2px at 55% 35%, rgba(255, 255, 255, 0.7), transparent),
                    radial-gradient(1px 1px at 70% 80%, rgba(255, 255, 255, 0.5), transparent),
                    radial-gradient(1px 1px at 40% 20%, white, transparent),
                    radial-gradient(2px 2px at 88% 50%, rgba(220, 230, 255, 0.8), transparent);
                background-repeat: repeat;
                background-size: 350px 350px, 500px 500px, 420px 420px, 280px 280px, 580px 580px;
                animation: twinkle 12s ease-in-out infinite reverse;
            }

            @keyframes twinkle {
                0%, 100% { opacity: 0.7; }
                50% { opacity: 1; }
            }

            #earth {
                width: 600px;
                height: 600px;
                border-radius: 50%;  /* makes square into circle */
                background: url(/assets/earth_texture_50.jpg);
                background-size: 1200px 600px;
                box-shadow:
                    inset 16px 72px 160px 72px rgb(0, 0, 0), 
                    inset -12px 0 24px 8px rgba(255, 255, 255, 0.3),
                    0 0 32px 8px rgba(100, 180, 255, 0.6),
                    0 0 64px 16px rgba(100, 180, 255, 0.4),
                    0 0 96px 24px rgba(100, 180, 255, 0.2),
                    0 0 128px 32px rgba(100, 180, 255, 0.1);
                animation-name: rotate-earth;
                animation-duration: 600s;
                animation-iteration-count: infinite;
                animation-timing-function: linear;
            }
            @keyframes rotate-earth {
                from { background-position: 1200px 0px; }
                to { background-position: 0px 0px; }
            }

            #mars {
                width: 150px;
                height: 150px;
                border-radius: 50%;
                background: url(/assets/mars_texture_50.jpg);
                background-size: 328px 150px;
                box-shadow:
                    inset 0px 0px 10px 4px rgb(0, 0, 0);
                animation-name: rotate-mars;
                animation-duration: 180s;
                animation-iteration-count: infinite;
                animation-timing-function: linear;
            }
            @keyframes rotate-mars {
                from { background-position: 328px 0px; }
                to { background-position: 0px 0px; }
            }

            #jupiter {
                width: 221px;
                height: 221px;
                border-radius: 50%;
                background: url(/assets/jupiter_texture_50.jpg);
                background-size: 500px 250px;
                background-position: center center;
                box-shadow:
                    inset 0px 0px 15px 7px rgb(0, 0, 0);
                animation-name: rotate-jupiter;
                animation-duration: 240s;
                animation-iteration-count: infinite;
                animation-timing-function: linear;
            }
            @keyframes rotate-jupiter {
                from { background-position: 0px center; }
                to { background-position: 500px center; }
            }

            .lab-node {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                font-weight: bold;
                font-size: 14px;
                text-align: center;
                box-shadow: 0 0 20px rgba(255,255,255,0.3);
            }

            .lab-node:hover {
                transform: scale(1.2);
                box-shadow: 0 0 40px rgba(255,255,255,0.8);
                z-index: 100;
            }

            .lab-locked {
                background: linear-gradient(135deg, #4b5563 0%, #1f2937 100%);
                border: 2px solid #6b7280;
                color: #9ca3af;
                cursor: not-allowed;
            }

            .lab-unlocked {
                background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                border: 2px solid #fbbf24;
                color: #000;
                animation: pulse 2s ease-in-out infinite;
            }

            .lab-in-progress {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                border: 2px solid #60a5fa;
                color: #fff;
            }

            .lab-completed {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                border: 2px solid #34d399;
                color: #fff;
            }

            @keyframes pulse {
                0%, 100% { box-shadow: 0 0 20px rgba(251, 191, 36, 0.5); }
                50% { box-shadow: 0 0 40px rgba(251, 191, 36, 1); }
            }

            .lab-path {
                stroke: #4b5563;
                stroke-width: 2;
                fill: none;
                stroke-dasharray: 5, 5;
                opacity: 0.5;
            }

            .lab-path-active {
                stroke: #60a5fa;
                stroke-width: 3;
                opacity: 0.8;
                animation: flow 2s linear infinite;
            }

            @keyframes flow {
                to { stroke-dashoffset: -10; }
            }

            .galaxy {
                width: 200px;
                height: 200px;
                border-radius: 50%;
                background: radial-gradient(ellipse at center, 
                    rgba(147, 51, 234, 0.8) 0%,
                    rgba(124, 58, 237, 0.6) 20%,
                    rgba(99, 102, 241, 0.4) 40%,
                    rgba(59, 130, 246, 0.2) 60%,
                    transparent 80%
                );
                animation: rotate 30s linear infinite reverse;
                box-shadow: 
                    0 0 60px rgba(147, 51, 234, 0.6),
                    inset 0 0 40px rgba(147, 51, 234, 0.4);
            }

            .planet {
                border-radius: 50%;
                box-shadow: inset -10px -10px 20px rgba(0,0,0,0.5);
                animation: orbit 15s ease-in-out infinite;
            }

            @keyframes orbit {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-20px); }
            }

            .saturn {
                width: 100px;
                height: 100px;
                background: linear-gradient(135deg, #f4e4c1 0%, #e0c097 100%);
                box-shadow: 
                    inset -20px -20px 30px rgba(0,0,0,0.3),
                    0 0 30px rgba(244, 228, 193, 0.5);
                position: relative;
            }

            .saturn::after {
                content: '';
                position: absolute;
                top: 50%;
                left: -30%;
                right: -30%;
                height: 8px;
                background: linear-gradient(90deg, 
                    transparent 0%,
                    rgba(244, 228, 193, 0.8) 20%,
                    rgba(244, 228, 193, 0.4) 50%,
                    rgba(244, 228, 193, 0.8) 80%,
                    transparent 100%
                );
                transform: translateY(-50%) rotateX(75deg);
                border-radius: 50%;
            }

            .info-panel {
                background: rgba(10, 10, 26, 0.9);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                padding: 20px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 30px rgba(59, 130, 246, 0.2);
            }

            .rank-badge {
                background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                color: #000;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                display: inline-block;
                box-shadow: 0 0 20px rgba(251, 191, 36, 0.5);
            }
        </style>
    ''')

    # Main cosmic background
    with ui.element('div').classes('cosmic-bg'):
        # Twinkling stars background
        ui.element('div').classes('stars')

        # Header bar
        with ui.element('div').style('position: absolute; top: 0; left: 0; right: 0; z-index: 1000;'):
            with ui.row().classes('w-full items-center justify-between p-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.label('🔭 NovaLabs').classes('text-3xl font-bold text-white')
                    ui.label('Cosmic Journey').classes('text-xl text-blue-300')

                with ui.row().classes('items-center gap-4'):
                    ui.label(f"{user['first_name']} {user['last_name']}").classes('text-white')
                    ui.label().classes('rank-badge').bind_text_from(
                        globals(), 'current_rank', 
                        backward=lambda: user.get('rank', 'Dabbler').upper()
                    )
                    ui.button('Dashboard', on_click=lambda: ui.navigate.to('/')).props('flat color=white')
                    ui.button('Logout', on_click=lambda: logout(request)).props('flat color=white')

        # Main canvas for the cosmic journey
        with ui.element('div').style(
            'position: absolute; top: 80px; left: 0; right: 0; bottom: 0; overflow: hidden;'
        ):
            create_cosmic_journey(client, user, request)


def create_cosmic_journey(client, user, request):
    """Create the visual cosmic journey with labs"""
    try:
        # Get lab and progress data
        progress_data = client.get_my_progress()
        all_labs = progress_data.get('labs', [])

        if not all_labs:
            with ui.column().classes('items-center justify-center w-full h-full'):
                ui.label('No labs available yet').classes('text-white text-2xl')
            return

        # Sort labs by sequence
        sorted_labs = sorted(all_labs, key=lambda x: x.get('meta', {}).get('sequence_order', 999))

        # SVG container for the entire journey
        svg_width = "100%"
        svg_height = "100%"

        with ui.element('svg').props(f'width="{svg_width}" height="{svg_height}" viewBox="0 0 1920 1080"').style(
            'position: absolute; top: 0; left: 0;'
        ):
            # Define the journey path coordinates
            positions = calculate_lab_positions(len(sorted_labs))

            # Draw connection paths
            for i in range(len(positions) - 1):
                x1, y1 = positions[i]
                x2, y2 = positions[i + 1]

                # Determine if path should be active
                current_status = sorted_labs[i].get('progress', {}).get('status', 'locked')
                path_class = 'lab-path-active' if current_status == 'completed' else 'lab-path'

                ui.element('path').props(
                    f'd="M {x1} {y1} Q {(x1+x2)/2} {(y1+y2)/2 - 50} {x2} {y2}"'
                ).classes(path_class)

        # Overlay container for interactive elements
        with ui.element('div').style('position: relative; width: 100%; height: 100%;'):
            # Earth:
            with ui.element('div').style(
                'position: absolute; bottom: -150px; left: -150px; z-index: 10;'
            ):
                with ui.column().classes('items-center gap-2'):
                    ui.html('<div id="earth"></div>', sanitize=False)

            # Planets in the middle region
            with ui.element('div').style(
                'position: absolute; top: 22%; left: 28%; z-index: 5;'
            ):
                ui.html('<div style="transform: rotate(25deg);"><div id="mars"></div></div>', sanitize=False)

            with ui.element('div').style(
                'position: absolute; top: 5%; left: 47%; z-index: 5;'
            ):
                ui.html('<div style="transform: rotate(-15deg);"><div id="jupiter"></div></div>', sanitize=False)

            with ui.element('div').style(
                'position: absolute; top: 50%; left: 65%; z-index: 5;'
            ):
                ui.element('div').classes('planet saturn')

            # Galaxy in top right
            with ui.element('div').style(
                'position: absolute; top: 50px; right: 50px; z-index: 10;'
            ):
                with ui.column().classes('items-center gap-2'):
                    ui.element('div').classes('galaxy')
                    ui.label('Deep Space').classes('text-white text-lg font-bold')
                    ui.label('Advanced Labs').classes('text-purple-300 text-sm')

            # Lab nodes
            for i, lab in enumerate(sorted_labs):
                x, y = positions[i]
                create_lab_node(lab, x, y, client, request)

        # Info panel at bottom
        create_info_panel(user, progress_data)

    except SDKClientError as e:
        with ui.column().classes('items-center justify-center w-full h-full'):
            ui.label(f'Error loading labs: {str(e)}').classes('text-red-400 text-xl')


def calculate_lab_positions(num_labs):
    """Calculate positions for labs along a cosmic journey path"""
    positions = []

    # Define the journey path from bottom-left to top-right
    # Earth region (bottom left) -> Solar system (middle) -> Galaxy (top right)

    for i in range(num_labs):
        progress = i / max(1, num_labs - 1) if num_labs > 1 else 0

        # Create a curved path
        if progress < 0.33:  # Earth to inner solar system
            t = progress / 0.33
            x = 200 + (t * 400)
            y = 850 - (t * 250)
        elif progress < 0.66:  # Inner to outer solar system
            t = (progress - 0.33) / 0.33
            x = 600 + (t * 600)
            y = 600 - (t * 150)
        else:  # Outer solar system to deep space
            t = (progress - 0.66) / 0.34
            x = 1200 + (t * 450)
            y = 450 - (t * 200)

        positions.append((x, y))

    return positions


def create_lab_node(lab, x, y, client, request):
    lab_meta = lab['meta']
    lab_progress = lab['progress']

    """Create an interactive lab node"""
    status = lab_progress.get('status', 'locked')
    # lab_ref = lab_meta.get('ref', '')
    lab_name = lab_meta.get('name', 'Unknown Lab')

    # Determine status class
    status_class = f'lab-{status}'

    # Create clickable node
    with ui.element('div').style(
        f'position: absolute; left: {x}px; top: {y}px; transform: translate(-50%, -50%); z-index: 50;'
    ):
        with ui.element('div').classes(f'lab-node {status_class}').on('click', lambda lab=lab, client=client, request=request: handle_lab_click(lab, client, request)):
            with ui.column().classes('items-center gap-1 p-2'):
                # Lab number/icon
                sequence = lab_meta.get('sequence_order', 0)
                ui.label(f'#{sequence + 1}').classes('text-xs')

                # Status icon
                if status == 'completed':
                    ui.label('✓').classes('text-2xl')
                elif status == 'in_progress':
                    ui.label('▶').classes('text-xl')
                elif status == 'unlocked':
                    ui.label('🔓').classes('text-xl')
                else:
                    ui.label('🔒').classes('text-xl')

        # Lab name tooltip
        ui.label(lab_name).classes('text-white text-xs mt-2 text-center').style(
            'max-width: 120px; text-shadow: 0 0 10px rgba(0,0,0,0.8);'
        )


def create_info_panel(user, progress_data):
    """Create the information panel at the bottom"""
    with ui.element('div').style(
        'position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 100; min-width: 800px;'
    ):
        with ui.element('div').classes('info-panel'):
            with ui.row().classes('items-center justify-between gap-8'):
                # User stats
                with ui.column().classes('gap-1'):
                    ui.label('Progress Overview').classes('text-blue-300 text-sm font-bold')
                    ui.label(f"Rank: {user.get('rank', 'Dabbler').title()}").classes('text-white')
                    ui.label(f"Total Score: {user.get('total_score', 0):.1f}").classes('text-white')
                    ui.label(f"Bonus Points: {user.get('total_bonus_points', 0):.1f}").classes('text-yellow-300')
                
                # Lab stats
                labs = progress_data.get('labs', [])
                completed = len([lab for lab in labs if lab.get('progress', {}).get('status') == 'completed'])
                in_progress = len([lab for lab in labs if lab.get('progress', {}).get('status') == 'in_progress'])
                unlocked = len([lab for lab in labs if lab.get('progress', {}).get('status') == 'unlocked'])
                total = len(labs)
                
                with ui.column().classes('gap-1'):
                    ui.label('Lab Status').classes('text-blue-300 text-sm font-bold')
                    ui.label(f"✓ Completed: {completed}/{total}").classes('text-green-400')
                    ui.label(f"▶ In Progress: {in_progress}").classes('text-blue-400')
                    ui.label(f"🔓 Available: {unlocked}").classes('text-yellow-400')
                
                # Legend
                with ui.column().classes('gap-1'):
                    ui.label('Legend').classes('text-blue-300 text-sm font-bold')
                    with ui.row().classes('items-center gap-2'):
                        ui.element('div').style(
                            'width: 16px; height: 16px; border-radius: 50%; background: linear-gradient(135deg, #10b981 0%, #059669 100%);'
                        )
                        ui.label('Completed').classes('text-white text-sm')
                    with ui.row().classes('items-center gap-2'):
                        ui.element('div').style(
                            'width: 16px; height: 16px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);'
                        )
                        ui.label('In Progress').classes('text-white text-sm')
                    with ui.row().classes('items-center gap-2'):
                        ui.element('div').style(
                            'width: 16px; height: 16px; border-radius: 50%; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);'
                        )
                        ui.label('Available').classes('text-white text-sm')


def handle_lab_click(lab, client, request):
    """Handle clicking on a lab node"""
    status = lab['progress'].get('status', 'locked')

    if status == 'locked':
        ui.notify('This lab is locked. Complete prerequisites first!', type='warning')
        return

    # Show lab details dialog
    show_lab_dialog(lab, client, request)


def show_lab_dialog(lab, client, request):
    """Show detailed lab information dialog"""
    with ui.dialog() as dialog, ui.card().classes('w-[600px]').style(
        'background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 100%); border: 2px solid rgba(59, 130, 246, 0.5);'
    ):
        ui.label(lab['meta']['name']).classes('text-3xl font-bold text-white mb-4')

        with ui.column().classes('gap-4 text-white'):
            # Lab details
            ui.label(lab['meta'].get('description', 'No description available')).classes('text-gray-300')

            ui.separator().classes('bg-blue-500 opacity-30')

            # Status and score
            with ui.row().classes('gap-8'):
                with ui.column().classes('gap-2'):
                    ui.label('Status').classes('text-blue-300 font-bold')
                    status_colors = {
                        'locked': 'text-gray-400',
                        'unlocked': 'text-yellow-400',
                        'in_progress': 'text-blue-400',
                        'completed': 'text-green-400'
                    }
                    ui.label(lab['progress']['status'].replace('_', ' ').title()).classes(
                        f"{status_colors.get(lab['progress']['status'], 'text-white')} text-lg"
                    )

                if lab.get('progress', {}).get('score') is not None:
                    with ui.column().classes('gap-2'):
                        ui.label('Score').classes('text-blue-300 font-bold')
                        ui.label(f"{lab['progress']['score']:.1f}").classes('text-green-400 text-lg')

                if lab.get('progress', {}).get('bonus_points'):
                    with ui.column().classes('gap-2'):
                        ui.label('Bonus Points').classes('text-blue-300 font-bold')
                        ui.label(f"{lab['progress']['bonus_points']:.1f}").classes('text-yellow-400 text-lg')

            # Prerequisites
            if lab.get('meta', {}).get('prerequisite_refs'):
                ui.separator().classes('bg-blue-500 opacity-30')
                ui.label('Prerequisites').classes('text-blue-300 font-bold')
                for prereq in lab['meta']['prerequisite_refs']:
                    ui.label(f"• {prereq}").classes('text-gray-300')

            # Action buttons
            ui.separator().classes('bg-blue-500 opacity-30')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Close', on_click=dialog.close).props('flat color=white')

                if lab['progress']['status'] == 'unlocked':
                    ui.button(
                        'Start Lab',
                        on_click=lambda: start_lab(client, lab['meta']['ref'], dialog, request)
                    ).props('color=primary')
                elif lab['progress']['status'] in ['in_progress', 'completed']:
                    ui.button(
                        'Launch Lab',
                        on_click=lambda: launch_lab_ui(lab.get('meta', {}).get('ui_url'))
                    ).props('color=primary')

    dialog.open()


def start_lab(client, lab_ref, dialog, request):
    """Start a lab"""
    try:
        client.start_lab(lab_ref)
        ui.notify('Lab started!', type='positive')
        dialog.close()
        # Reload page to refresh progress
        ui.navigate.to(request.url.path)
    except SDKClientError as e:
        ui.notify(f'Error: {str(e)}', type='negative')


def launch_lab_ui(ui_url):
    """Launch the lab UI in a new window"""
    if ui_url:
        ui.run_javascript(f'window.open("{ui_url}", "_blank")')
    else:
        ui.notify('Lab UI not available', type='warning')


def logout(request: Request):
    """Logout helper"""
    session_manager.logout(request)
    session_manager.clear_session_cookie()
    ui.navigate.to('/login')
