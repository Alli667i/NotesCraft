import base64
import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
import secrets
import requests
from dotenv import load_dotenv

load_dotenv()  # Add this line

from nicegui import ui, app, background_tasks, run
from generate_notes import generate_notes_from_content
from extract_content import send_msg_to_ai
from generate_word_file import generate_word_file

from temp_db_auth import MongoUserAuth

from db_logger import (
    start_file_processing,
    log_processing_success,
    log_processing_failure,
    file_logger,
)

user_auth = MongoUserAuth()

# Import libraries for page counting
import fitz  # PyMuPDF for PDFs
import hashlib
import os

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# Ensure root container fills full viewport on mobile


# Defined range for n.o of allowed pages per generation
MAX_PAGES = 35
MAX_FILE_SIZE_MB = 50  # Additional safety check


# Count number of pages in the uploaded file
def count_pages(file_path):
    """Count pages in PDF files only"""
    try:
        if Path(file_path).suffix.lower() != '.pdf':
            return 0, "Only PDF files are supported"

        doc = fitz.open(file_path)
        page_count = doc.page_count
        doc.close()
        return page_count, None
    except Exception as e:
        return 0, f"Error reading PDF: {str(e)}"


# Validate if file size is in defined range
def validate_file(file_path, file_size_bytes):
    """
    Validate uploaded file against size and page limits
    Returns: (is_valid, error_message, page_count)
    """
    # Check file size first (quick check)
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large ({file_size_mb:.1f}MB). Maximum size is {MAX_FILE_SIZE_MB}MB.", 0

    # Count pages
    page_count, error = count_pages(file_path)

    if error:
        return False, error, 0

    if page_count > MAX_PAGES:
        return False, f"Document has {page_count} pages. Maximum allowed is {MAX_PAGES} pages.", page_count

    return True, None, page_count


# Add Users


# User Login Page UI
def show_beautiful_user_login():
    """Simple centered login page with early access signup"""
    ui.add_head_html('''
        <link rel="manifest" href="assets/manifest.json">
        <link rel="icon" href="assets/favicon.ico">
        <meta name="theme-color" content="#ffffff">
        ''')

    ui.add_head_html('<title>NotesCraft AI - Login</title>')

    # Simple CSS
    ui.add_head_html("""
    <style>
        .login-bg {
            background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
            min-height: 100vh;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        .signup-card {
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
    </style>
    """)

    with ui.column().classes('login-bg w-full h-screen flex items-center justify-center p-6'):
        with ui.column().classes('items-center w-full max-w-md'):
            # Brand name at top center
            ui.label('NotesCraft AI').classes('text-5xl font-extrabold text-emerald-600 mb-12 text-center')

            # Login card
            with ui.card().classes('login-card w-full p-8 shadow-lg rounded-2xl'):
                with ui.column().classes('w-full space-y-6'):
                    # Login form
                    email_input = ui.input('Email', placeholder='your@email.com').props('outlined').classes('w-full')
                    # password_input = ui.input('Password', password=True, placeholder='Password').props(
                    #     'outlined').classes('w-full')

                    error_label = ui.label('').classes('text-red-500 text-center text-sm')

                    def handle_login():
                        session = app.storage.user
                        email = email_input.value.strip().lower()
                        # password = password_input.value

                        if not email :
                            error_label.text = 'Please enter your registered email'
                            return

                        if user_auth.verify_user(email) and user_auth.is_user_active(email):
                            session['user_logged_in'] = True
                            session['user_email'] = email
                            ui.navigate.to('/')
                        else:
                            error_label.text = 'Invalid credentials'
                            # password_input.value = ''
                            # password_input.run_method('focus')

                    # Login button
                    ui.button('Sign In', on_click=handle_login).props('unelevated size=lg').classes(
                        'w-full bg-emerald-500 text-white py-3 text-lg font-semibold rounded-xl hover:bg-emerald-600'
                    )

                    # password_input.on('keydown.enter', handle_login)

                    # Small text below login form
                    ui.label("Use credentials given to you when you joined early access").classes(
                        'text-xs text-gray-500 text-center mt-2')

            # Early access signup card
            with ui.card().classes('signup-card w-full p-6 mt-6 shadow-md rounded-2xl'):
                with ui.column().classes('w-full items-center space-y-4'):
                    ui.label("Don't have early access yet?").classes('text-lg font-semibold text-gray-800 text-center')

                    def join_early_access():
                        ui.run_javascript("window.open('https://notescraftai.com/#early-access', '_blank')")

                    ui.button('Join Early Access Now', on_click=join_early_access).props('unelevated size=lg').classes(
                        'bg-blue-500 text-white px-8 py-3 text-lg font-semibold rounded-xl hover:bg-blue-600 transition-colors'
                    )


@ui.page('/login')
def user_login_page():
    """Simple login page"""
    show_beautiful_user_login()


# Verify Access to admin panel

class SecureAdminAuth:
    def __init__(self):
        self.admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")
        if not self.admin_password_hash:
            print("⚠️ No admin password set! Using default: 'admin123'")
            self.admin_password_hash = self.hash_password("admin123")

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hash_obj = hashlib.sha256(salt_bytes + password_bytes)
        password_hash = hash_obj.hexdigest()
        return f"{salt}:{password_hash}"

    def verify_password(self, password: str) -> bool:
        if not self.admin_password_hash:
            return False
        try:
            stored_salt, stored_hash = self.admin_password_hash.split(':', 1)
            password_bytes = password.encode('utf-8')
            salt_bytes = stored_salt.encode('utf-8')
            hash_obj = hashlib.sha256(salt_bytes + password_bytes)
            password_hash = hash_obj.hexdigest()
            return password_hash == stored_hash
        except:
            return False


# Create the auth system
admin_auth = SecureAdminAuth()


# Admin Panel UI

@ui.page('/admin')
def admin_page():
    """Beautiful modern admin dashboard"""

    session = app.storage.user

    if not session.get('admin_logged_in', False):
        show_beautiful_login()
    else:
        show_beautiful_dashboard()


def show_beautiful_login():
    """Modern login page"""
    ui.add_head_html('<title>Admin Login - NotesCraft AI</title>')

    # Add custom CSS for login
    ui.add_head_html("""
    <style>
        .login-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .login-card {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
    </style>
    """)

    with ui.column().classes('login-container absolute inset-0 flex items-center justify-center'):
        with ui.card().classes('login-card w-full max-w-md p-8 shadow-2xl rounded-2xl'):
            # Logo and title
            with ui.column().classes('items-center mb-8'):
                ui.icon('admin_panel_settings').classes('text-6xl text-indigo-600 mb-4')
                ui.label('Admin Dashboard').classes('text-3xl font-bold text-gray-800')
                ui.label('NotesCraft AI Analytics').classes('text-sm text-gray-600')

            # Login form
            password_input = ui.input('Enter Admin Password', password=True).props('outlined').classes('w-full')
            error_label = ui.label('').classes('text-red-500 text-center text-sm mt-2')

            def check_password():
                session = app.storage.user
                if admin_auth.verify_password(password_input.value):  # Use secure verification
                    session['admin_logged_in'] = True
                    ui.navigate.to('/admin')
                else:
                    error_label.text = 'Incorrect password'
                    password_input.value = ''

            ui.button('Access Dashboard', on_click=check_password).props('unelevated').classes(
                'w-full mt-6 bg-indigo-600 text-white py-3 text-lg font-semibold rounded-lg hover:bg-indigo-700'
            )

            # Allow Enter key
            password_input.on('keydown.enter', check_password)

            # Footer
            ui.label('🔒 Secure admin access only').classes('text-xs text-gray-500 text-center mt-6')


def show_beautiful_dashboard():
    """Beautiful modern dashboard with user management"""
    ui.add_head_html('<title>Analytics Dashboard - NotesCraft AI</title>')

    # Add custom CSS for dashboard
    ui.add_head_html("""
    <style>
        .dashboard-bg {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        .glass-card {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .status-success { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .status-failed { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .status-processing { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
        .metric-card {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
    </style>
    """)

    with ui.column().classes('dashboard-bg w-full min-h-screen'):
        # Header Section
        with ui.row().classes('w-full p-6 items-center justify-between'):
            with ui.column():
                ui.label('Analytics Dashboard').classes('text-4xl font-bold text-gray-800')
                ui.label('Real-time insights for NotesCraft AI').classes('text-lg text-gray-600')

            with ui.row().classes('gap-4'):
                ui.link('Back to App', '/').classes(
                    'px-4 py-2 bg-white rounded-lg text-indigo-600 font-medium hover:bg-indigo-50 shadow-sm'
                )

                def logout():
                    session = app.storage.user
                    session['admin_logged_in'] = False
                    ui.navigate.to('/admin')

                ui.button('Logout', on_click=logout).props('outline').classes(
                    'px-4 py-2 text-red-600 border-red-300 hover:bg-red-50'
                )

        # Main Content
        with ui.column().classes('w-full px-6 pb-6'):
            # Quick Stats Overview
            stats = file_logger.get_stats_summary()

            with ui.row().classes('w-full gap-6 mb-8'):
                # Total Processed
                with ui.card().classes('metric-card glass-card p-6 flex-1 text-center'):
                    ui.icon('description').classes('text-4xl text-blue-600 mb-2')
                    ui.label(str(stats['total_processed'])).classes('text-3xl font-bold text-gray-800')
                    ui.label('Files Processed').classes('text-sm text-gray-600 font-medium')

                # Success Rate
                success_rate = round((stats['successful'] / max(stats['total_processed'], 1)) * 100, 1)
                with ui.card().classes('metric-card glass-card p-6 flex-1 text-center'):
                    ui.icon('check_circle').classes('text-4xl text-green-600 mb-2')
                    ui.label(f'{success_rate}%').classes('text-3xl font-bold text-gray-800')
                    ui.label('Success Rate').classes('text-sm text-gray-600 font-medium')

                # Total Tokens
                total_tokens = stats['total_extraction_tokens'] + stats['total_generation_tokens']
                with ui.card().classes('metric-card glass-card p-6 flex-1 text-center'):
                    ui.icon('psychology').classes('text-4xl text-purple-600 mb-2')
                    ui.label(f'{total_tokens:,}').classes('text-3xl font-bold text-gray-800')
                    ui.label('Total Tokens').classes('text-sm text-gray-600 font-medium')

                # Avg Processing Time
                with ui.card().classes('metric-card glass-card p-6 flex-1 text-center'):
                    ui.icon('schedule').classes('text-4xl text-orange-600 mb-2')
                    ui.label(f'{stats["average_processing_time"]}s').classes('text-3xl font-bold text-gray-800')
                    ui.label('Avg Time').classes('text-sm text-gray-600 font-medium')

            # User Management Section - More compact
            with ui.row().classes('w-full gap-6 mb-8'):
                # User Summary Card
                users = user_auth.list_users()
                active_users = len([u for u in users if u['active']])

                with ui.card().classes('metric-card glass-card p-6 flex-1 text-center'):
                    ui.icon('group').classes('text-4xl text-indigo-600 mb-2')
                    ui.label(str(len(users))).classes('text-3xl font-bold text-gray-800')
                    ui.label('Total Users').classes('text-sm text-gray-600 font-medium')
                    ui.label(f'{active_users} active').classes('text-xs text-green-600')

                # Quick Add User
                with ui.card().classes('glass-card p-6 flex-2'):
                    ui.label('Quick Add User').classes('text-lg font-bold text-gray-800 mb-4')

                    with ui.row().classes('w-full gap-3'):
                        new_email = ui.input('Email', placeholder='user@example.com').classes('flex-1')
                        new_password = ui.input('Password').classes('flex-1')

                        def add_new_user():
                            if new_email.value and new_password.value:
                                success = user_auth.add_user(
                                    new_email.value.strip().lower(),
                                    new_password.value,
                                    None
                                )
                                if success:
                                    ui.notify(f'User {new_email.value} added!', type='positive')
                                    new_email.value = ''
                                    new_password.value = ''
                                    refresh_user_list()
                                else:
                                    ui.notify('User already exists', type='negative')
                            else:
                                ui.notify('Email and password required', type='warning')

                        ui.button('Add', on_click=add_new_user).classes('bg-green-600 text-white')

                    # Show last few users
                    recent_users = users[-3:] if users else []
                    if recent_users:
                        ui.label('Recent Users:').classes('text-sm text-gray-600 mt-3 mb-2')
                        for user in recent_users:
                            status_dot = '🟢' if user['active'] else '🔴'
                            ui.label(f'{status_dot} {user["email"]}').classes('text-xs text-gray-600')

                # User Management Button
                with ui.card().classes('glass-card p-6 flex-1 text-center'):
                    ui.icon('settings').classes('text-4xl text-gray-600 mb-2')

                    def show_user_management():
                        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl p-6'):
                            ui.label('User Management').classes('text-2xl font-bold mb-6')

                            # User list in dialog
                            users_container = ui.column().classes('w-full max-h-96 overflow-auto')

                            def refresh_dialog_users():
                                users_container.clear()
                                users = user_auth.list_users()

                                with users_container:
                                    if not users:
                                        ui.label('No users found').classes('text-gray-500 text-center py-8')
                                    else:
                                        for user in users:
                                            with ui.row().classes(
                                                    'w-full items-center justify-between p-3 border-b gap-4'):
                                                with ui.column().classes('flex-1'):
                                                    ui.label(user['email']).classes('font-medium')
                                                    if user['name']:
                                                        ui.label(user['name']).classes('text-sm text-gray-600')

                                                with ui.row().classes('gap-2 items-center'):
                                                    # Status
                                                    status = '🟢 Active' if user['active'] else '🔴 Inactive'
                                                    ui.label(status).classes('text-sm')

                                                    # Actions
                                                    def toggle_user(email=user['email'], active=user['active']):
                                                        if active:
                                                            user_auth.deactivate_user(email)
                                                        else:
                                                            user_auth.activate_user(email)
                                                        refresh_dialog_users()
                                                        refresh_user_list()

                                                    def remove_user(email=user['email']):
                                                        user_auth.remove_user(email)
                                                        refresh_dialog_users()
                                                        refresh_user_list()

                                                    toggle_text = 'Deactivate' if user['active'] else 'Activate'
                                                    ui.button(toggle_text, on_click=lambda e=user['email'], a=user[
                                                        'active']: toggle_user(e, a)).props('size=sm outline')
                                                    ui.button('Remove',
                                                              on_click=lambda e=user['email']: remove_user(e)).props(
                                                        'size=sm color=red outline')

                            refresh_dialog_users()

                            ui.button('Close', on_click=dialog.close).classes('mt-4')
                        dialog.open()

                    ui.button('Manage Users', on_click=show_user_management).classes('w-full')
                    ui.label('View & Edit All Users').classes('text-xs text-gray-500 mt-2')

                def refresh_user_list():
                    # Refresh the user count display
                    pass

            # Detailed Stats Row
            with ui.row().classes('w-full gap-6 mb-8'):
                # Status Breakdown
                with ui.card().classes('glass-card p-6 flex-1'):
                    ui.label('Processing Status').classes('text-xl font-bold text-gray-800 mb-4')

                    with ui.column().classes('gap-3'):
                        # Success
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('check_circle').classes('text-green-500')
                                ui.label('Successful').classes('font-medium')
                            ui.label(str(stats['successful'])).classes('font-bold text-green-600')

                        # Failed
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('error').classes('text-red-500')
                                ui.label('Failed').classes('font-medium')
                            ui.label(str(stats['failed'])).classes('font-bold text-red-600')

                        # Downloaded
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('download').classes('text-blue-500')
                                ui.label('Downloaded').classes('font-medium')
                            ui.label(str(stats['downloaded'])).classes('font-bold text-blue-600')

                # Token Breakdown
                with ui.card().classes('glass-card p-6 flex-1'):
                    ui.label('Token Usage').classes('text-xl font-bold text-gray-800 mb-4')

                    with ui.column().classes('gap-3'):
                        # Extraction tokens
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('search').classes('text-indigo-500')
                                ui.label('Extraction').classes('font-medium')
                            ui.label(f'{stats["total_extraction_tokens"]:,}').classes('font-bold text-indigo-600')

                        # Generation tokens
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('auto_fix_high').classes('text-purple-500')
                                ui.label('Generation').classes('font-medium')
                            ui.label(f'{stats["total_generation_tokens"]:,}').classes('font-bold text-purple-600')

                        # Total
                        ui.separator().classes('my-2')
                        with ui.row().classes('items-center justify-between'):
                            ui.label('Total').classes('font-bold')
                            ui.label(f'{total_tokens:,}').classes('font-bold text-gray-800 text-lg')

            # File Processing History
            logs = file_logger.read_logs()

            if not logs:
                with ui.card().classes('glass-card p-12 text-center'):
                    ui.icon('folder_open').classes('text-6xl text-gray-400 mb-4')
                    ui.label('No files processed yet').classes('text-xl text-gray-500 font-medium')
                    ui.label('Upload and process some files to see analytics here').classes('text-gray-400')
                return

            # Files Section Header
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label('Recent File Processing').classes('text-2xl font-bold text-gray-800')
                ui.label(f'{len(logs)} files processed').classes('text-gray-600')

            # Files Grid
            recent_logs = sorted(logs, key=lambda x: x.get('start_time', ''), reverse=True)[:10]

            with ui.column().classes('w-full gap-4'):
                for log in recent_logs:
                    show_beautiful_file_card(log)


def show_beautiful_file_card(log):
    """Beautiful file processing card"""
    filename = log.get('filename', 'Unknown file')
    status = log.get('status', 'unknown')
    start_time = log.get('start_time', '')
    total_duration = log.get('total_duration', 0)
    downloaded = log.get('downloaded', False)

    # Format time
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(start_time)
        formatted_time = dt.strftime('%b %d, %Y at %H:%M')
    except:
        formatted_time = start_time

    # Determine card style and status
    if status == 'success':
        if downloaded:
            card_class = 'glass-card border-l-4 border-green-500'
            status_badge = 'bg-green-100 text-green-800'
            status_icon = '✅'
            status_text = 'Completed & Downloaded'
        else:
            card_class = 'glass-card border-l-4 border-yellow-500'
            status_badge = 'bg-yellow-100 text-yellow-800'
            status_icon = '⚠️'
            status_text = 'Completed (Not Downloaded)'
    elif status == 'failed':
        card_class = 'glass-card border-l-4 border-red-500'
        status_badge = 'bg-red-100 text-red-800'
        status_icon = '❌'
        status_text = 'Processing Failed'
    else:
        card_class = 'glass-card border-l-4 border-blue-500'
        status_badge = 'bg-blue-100 text-blue-800'
        status_icon = '🔄'
        status_text = 'Processing...'

    with ui.card().classes(f'w-full p-6 {card_class} hover:shadow-lg transition-shadow'):
        with ui.row().classes('w-full items-start justify-between'):
            # Main content
            with ui.column().classes('flex-1'):
                # File header
                with ui.row().classes('items-center gap-3 mb-3'):
                    ui.icon('description').classes('text-2xl text-gray-600')
                    ui.label(filename).classes('text-xl font-bold text-gray-800')

                    # Status badge
                    with ui.row().classes(f'px-3 py-1 rounded-full {status_badge}'):
                        ui.label(f'{status_icon} {status_text}').classes('text-sm font-medium')

                # Time and basic info
                ui.label(formatted_time).classes('text-sm text-gray-500 mb-3')

                # File metrics
                pages = log.get('page_count', 0)
                size = log.get('file_size_mb', 0)

                with ui.row().classes('gap-6 mb-4'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('description').classes('text-sm text-gray-500')
                        ui.label(f'{pages} pages').classes('text-sm text-gray-600')

                    with ui.row().classes('items-center gap-1'):
                        ui.icon('storage').classes('text-sm text-gray-500')
                        ui.label(f'{size} MB').classes('text-sm text-gray-600')

                    if total_duration:
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('schedule').classes('text-sm text-gray-500')
                            ui.label(f'{total_duration}s').classes('text-sm text-gray-600')

                # Processing details (if successful)
                if status == 'success':
                    extraction = log.get('extraction', {})
                    generation = log.get('generation', {})

                    with ui.row().classes('gap-8'):
                        # Extraction info
                        ext_tokens = extraction.get('tokens', {}).get('total', 0)
                        ext_time = extraction.get('duration', 0)
                        if ext_tokens > 0:
                            with ui.column().classes('bg-indigo-50 p-3 rounded-lg'):
                                ui.label('🔍 Extraction').classes('text-xs font-bold text-indigo-600 uppercase')
                                ui.label(f'{ext_tokens:,} tokens').classes('text-sm font-medium')
                                if ext_time:
                                    ui.label(f'{ext_time}s').classes('text-xs text-gray-500')

                        # Generation info
                        gen_tokens = generation.get('tokens', {}).get('total', 0)
                        gen_time = generation.get('duration', 0)
                        if gen_tokens > 0:
                            with ui.column().classes('bg-purple-50 p-3 rounded-lg'):
                                ui.label('🛠️ Generation').classes('text-xs font-bold text-purple-600 uppercase')
                                ui.label(f'{gen_tokens:,} tokens').classes('text-sm font-medium')
                                if gen_time:
                                    ui.label(f'{gen_time}s').classes('text-xs text-gray-500')

                # Error details (if failed)
                elif status == 'failed' and log.get('error'):
                    error = log['error']
                    error_type = error.get('error_type', 'Unknown')
                    step = error.get('processing_step', 'unknown')

                    # Convert error type to readable
                    readable_errors = {
                        "API_KEY_ERROR": "API Key Missing",
                        "API_RATE_LIMIT": "Rate Limit Exceeded",
                        "API_QUOTA_EXCEEDED": "API Quota Exceeded",
                        "FILE_EXTRACTION_ERROR": "File Reading Failed",
                        "NOTES_GENERATION_ERROR": "Notes Generation Failed"
                    }
                    readable_error = readable_errors.get(error_type, error_type.replace("_", " ").title())

                    with ui.row().classes('bg-red-50 p-3 rounded-lg items-center gap-2'):
                        ui.icon('error').classes('text-red-500')
                        ui.label(f'Failed at {step}: {readable_error}').classes('text-sm text-red-700 font-medium')

            # Actions
            with ui.column().classes('gap-2'):
                # Raw data button
                def show_complete_data():
                    with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl p-6'):
                        ui.label(f'📊 Complete Processing Data').classes('text-2xl font-bold mb-4')
                        ui.label(filename).classes('text-lg text-gray-600 mb-4')

                        json_text = json.dumps(log, indent=2)
                        ui.textarea(value=json_text).classes('w-full h-96 font-mono text-sm')

                        with ui.row().classes('justify-end mt-4'):
                            ui.button('Close', on_click=dialog.close).props('outline')
                    dialog.open()

                ui.button('📊 View Details', on_click=show_complete_data).props('outline').classes(
                    'text-sm px-4 py-2 border-gray-300 text-gray-600 hover:bg-gray-50'
                )


def add_user_management_to_admin():
    """Add this to your admin dashboard to manage users"""

    # Add this section to your admin dashboard
    with ui.card().classes('glass-card p-6 mb-6'):
        ui.label('User Management').classes('text-xl font-bold text-gray-800 mb-4')

        # Add new user section
        with ui.row().classes('w-full gap-4 mb-4'):
            new_email = ui.input('Email').classes('flex-1')
            new_password = ui.input('Password').classes('flex-1')
            new_name = ui.input('Name (optional)').classes('flex-1')

            def add_new_user():
                if new_email.value and new_password.value:
                    success = user_auth.add_user(
                        new_email.value.strip().lower(),
                        new_password.value,
                        new_name.value or None
                    )
                    if success:
                        ui.notify(f'User {new_email.value} added successfully!', type='positive')
                        new_email.value = ''
                        new_password.value = ''
                        new_name.value = ''
                        refresh_user_list()
                    else:
                        ui.notify('Failed to add user', type='negative')
                else:
                    ui.notify('Email and password required', type='warning')

            ui.button('Add User', on_click=add_new_user).classes('bg-green-600 text-white')

        # User list
        users_container = ui.column().classes('w-full')

        def refresh_user_list():
            users_container.clear()
            users = user_auth.list_users()

            with users_container:
                if not users:
                    ui.label('No users found').classes('text-gray-500')
                else:
                    for user in users:
                        with ui.row().classes('w-full items-center justify-between p-2 border-b'):
                            with ui.column():
                                ui.label(user['email']).classes('font-medium')
                                ui.label(user['name']).classes('text-sm text-gray-600')

                            with ui.row().classes('gap-2'):
                                status = 'Active' if user['active'] else 'Inactive'
                                ui.label(status).classes(
                                    'text-green-600 text-sm' if user['active'] else 'text-red-600 text-sm'
                                )

                                def toggle_user(email=user['email'], active=user['active']):
                                    if active:
                                        user_auth.deactivate_user(email)
                                        ui.notify(f'User {email} deactivated', type='info')
                                    else:
                                        user_auth.activate_user(email)
                                        ui.notify(f'User {email} activated', type='positive')
                                    refresh_user_list()

                                def remove_user(email=user['email']):
                                    user_auth.remove_user(email)
                                    ui.notify(f'User {email} removed', type='info')
                                    refresh_user_list()

                                ui.button('Toggle',
                                          on_click=lambda e=user['email'], a=user['active']: toggle_user(e, a)).props(
                                    'size=sm outline')
                                ui.button('Remove', on_click=lambda e=user['email']: remove_user(e)).props(
                                    'size=sm color=red outline')

        refresh_user_list()


# Main App UI
@ui.page('/')
def main_page():
    """Protected main page - checks login first"""
    session = app.storage.user

    # Check if user is logged in
    if not session.get('user_logged_in', False):
        ui.navigate.to('/login')  # Send them to login page
        return  # Stop here, don't show the app

    # If they are logged in, show the normal app
    main_page_content()


def main_page_content():
    ui.add_head_html("""
    <style>
    html, body, #__nicegui_root {
        height: 100%;
        margin: 0;
        padding: 0;
    }
    </style>
    """)

    # ui.add_head_html('<link rel="icon" href="assets/favicon.ico">')
    ui.add_head_html('''
    <link rel="manifest" href="assets/manifest.json">
    <link rel="icon" href="assets/favicon.ico">
    <meta name="theme-color" content="#ffffff">
    ''')

    ui.add_head_html("""
    <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>

    """)

    session = app.storage.user
    session.uploaded_file_path = None
    session.uploaded_file_name = "Notes"

    # --- Helper Functions ---
    def report_error(Error):
        if Error:
            try:
                requests.post(
                    'https://script.google.com/macros/s/AKfycbz6Gbht0iZ4tW7lp48x3hDYCvYIDGZbOYdwnpbmyHSQjxsdZ0D0zsx7ZU84eN9n0g2T9w/exec',
                    json={"Error": Error},
                )
            except Exception as e:
                print(f"Error reporting failed: {e}")

    def calculate_estimated_time(page_count, file_size_mb=None):
        """
        Calculate estimated processing time based on actual performance data
        Returns estimated time in seconds
        """
        # Based on real measurements:
        # 2 pages: 45-50 seconds
        # 4 pages: 81-90 seconds
        # 25 pages: 848-870 seconds

        if page_count <= 2:
            base_time = 50  # Maximum for 2 pages
        elif page_count <= 4:
            base_time = 90  # Maximum for 4 pages
        elif page_count <= 25:
            # Linear interpolation between 4 pages (90s) and 25 pages (870s)
            # Rate: (870-90)/(25-4) = ~37 seconds per page after 4 pages
            base_time = 90 + ((page_count - 4) * 37)
        else:
            # Should not happen with 25-page limit, but safety fallback
            base_time = 870

        # Adjust for file complexity based on size
        if file_size_mb:
            if file_size_mb > 15:  # Very large files likely have complex content
                base_time *= 1.15  # Add 15% for complexity
            elif file_size_mb > 30:  # Extremely large files
                base_time *= 1.25  # Add 25% for high complexity

        # Ensure we don't exceed maximum bounds (25 pages = ~870 seconds = ~14.5 minutes)
        max_time = 900  # 15 minutes maximum
        estimated_time = min(base_time, max_time)

        return int(estimated_time)

    def format_time_remaining(seconds):
        """Format seconds into human-readable time"""
        minutes = seconds // 60
        remaining_seconds = seconds % 60

        if minutes > 0:
            if remaining_seconds > 30:
                minutes += 1  # Round up if more than 30 seconds
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return "less than 1 minute"

    def get_step_progress_info(current_step, total_estimated_time):
        """
        Get progress information for current processing step
        Returns (step_percentage, time_remaining_estimate)
        """
        if current_step == "extracting":
            progress = 0.2  # Assume we're halfway through extraction
            time_remaining = int(total_estimated_time * 0.8)
        elif current_step == "generating":
            progress = 0.4 + 0.25  # 40% done + halfway through generation
            time_remaining = int(total_estimated_time * 0.35)
        elif current_step == "creating_file":
            progress = 0.9  # 90% done
            time_remaining = int(total_estimated_time * 0.1)
        else:
            progress = 0.1
            time_remaining = total_estimated_time

        return progress, time_remaining

    def reset_app():
        """Reset app to initial state with confirmation"""

        def confirm_reset():
            try:
                # Clear session data
                session.uploaded_file_path = None
                session.uploaded_file_name = "Notes"
                session.processing_session_id = None
                session.processing_status = "idle"
                session.processing_result = None
                session.processing_error = None
                session.estimated_total_time = None

                # Reset UI elements
                download_button.visible = False
                feedback_button.visible = False
                reset_button.visible = False
                try_again_button.visible = False
                error_report_button.visible = False

                # Clear animations
                text_extraction_animation.visible = False
                notes_generation_animation.visible = False
                word_file_generation_animation.visible = False
                time_label.visible = False

                # Clear text elements
                status_label.text = ""
                error_label.text = ""

                # Show generate button
                generate_button.visible = True

                # Re-render upload area
                render_upload()

                ui.notify("Ready for another file!", type='positive')

                # Close the confirmation dialog
                reset_dialog.close()

            except Exception as e:
                print(f"Reset error: {e}")
                ui.notify("Reset failed. Please refresh the page.", type='negative')

        def cancel_reset():
            reset_dialog.close()

        # Show confirmation dialog
        with ui.dialog() as reset_dialog, ui.card().classes('w-full max-w-sm p-6'):
            ui.label('Upload Another File?').classes('text-lg font-bold text-gray-800 mb-3')
            ui.label('This will clear your current file and any processing progress.').classes(
                'text-sm text-gray-600 mb-5')

            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancel', on_click=cancel_reset).props('outline').classes(
                    'text-gray-600 border-gray-400 px-4 py-2 font-medium rounded-lg hover:bg-gray-100'
                )
                ui.button('Yes, Upload New File', on_click=confirm_reset).props('unelevated').classes(
                    'bg-emerald-500 text-white px-4 py-2 font-medium rounded-lg hover:bg-emerald-600'
                )

        reset_dialog.open()

    def check_processing_status():
        """
        Enhanced polling function with time estimation
        """
        try:
            if not hasattr(session, 'processing_status'):
                return

            status = session.processing_status

            # Get estimated time if we have page count
            if hasattr(session, 'estimated_total_time') and session.estimated_total_time:
                total_time = session.estimated_total_time
                progress, time_remaining = get_step_progress_info(status, total_time)
                time_text = format_time_remaining(time_remaining)
            else:
                time_text = ""

            if status == "extracting":
                text_extraction_animation.visible = True
                notes_generation_animation.visible = False
                word_file_generation_animation.visible = False
                status_label.text = "Extracting content from document..."
                if time_text:
                    time_label.text = f"Time remaining: ~{time_text}"
                    time_label.visible = True
                else:
                    time_label.visible = False

            elif status == "generating":
                text_extraction_animation.visible = False
                notes_generation_animation.visible = True
                word_file_generation_animation.visible = False
                status_label.text = "🛠 Generating Notes"
                if time_text:
                    time_label.text = f"Time remaining: ~{time_text}"
                    time_label.visible = True
                else:
                    time_label.visible = False

            elif status == "creating_file":
                text_extraction_animation.visible = False
                notes_generation_animation.visible = False
                word_file_generation_animation.visible = True
                status_label.text = "📕 Preparing Word file..."
                if time_text:
                    time_label.text = f"Time remaining: ~{time_text}"
                    time_label.visible = True
                else:
                    time_label.visible = False

            elif status == "completed":
                # Success - show download
                text_extraction_animation.visible = False
                notes_generation_animation.visible = False
                word_file_generation_animation.visible = False
                time_label.visible = False

                # Switch to file ready warning
                ui.timer(0.1, lambda: ui.run_javascript('window.fileReadyForDownload()'), once=True)

                result = session.processing_result

                # Store download data in session for the persistent handler
                session.download_data = {
                    "base64_data": result['base64_data'],
                    "mime_type": result['mime_type'],
                    "filename": result['filename']
                }

                download_button.visible = True
                feedback_button.visible = True
                reset_button.visible = True
                status_label.text = "✅ Your Notes are Ready!"

                session.processing_status = "idle"
                return

            elif status == "error":
                # Error - show error UI
                text_extraction_animation.visible = False
                notes_generation_animation.visible = False
                word_file_generation_animation.visible = False
                generate_button.visible = False
                time_label.visible = False

                # Disable browser close warning (fire and forget)
                # ui.timer(0.1, lambda: ui.run_javascript('window.stopProcessing()'), once=True)

                error = session.processing_error
                if error:
                    error_type = error.get("error_type", "")
                    user_message = error.get("user_message", "An error occurred")

                    if error_type == "API_RATE_LIMIT":
                        error_label.text = "⚠️ We're processing a lot of requests right now. Please wait a moment and try again."
                    elif error_type == "API_QUOTA_EXCEEDED":
                        error_label.text = "⚠️ We've reached our daily processing limit. Please try again tomorrow."
                    elif error_type == "API_KEY_ERROR":
                        error_label.text = "⚠️ Service temporarily unavailable. We're working on it!"
                    else:
                        error_label.text = f"⚠️ {user_message}"

                status_label.text = ""
                error_report_button.visible = True
                try_again_button.visible = True

                session.processing_status = "idle"
                return

            # Continue polling if still processing
            if status in ["starting", "extracting", "generating", "creating_file"]:
                ui.timer(1.0, check_processing_status, once=True)

        except Exception as e:
            print(f"Error in polling function: {e}")
            error_label.text = "⚠️ Something went wrong. Please try again."
            try_again_button.visible = True

    async def process_with_ai():
        if not session.uploaded_file_path or not session.uploaded_file_path.exists():
            ui.notify(message='Please Upload a File', type='warning')
            return

        # ui.notify('Processing may take 5-10 minutes. Mobile devices may experience connection issues.', type='info',
        #           timeout=5000)

        # Set up processing state
        session.processing_status = "starting"
        session.processing_result = None
        session.processing_error = None

        # Start UI updates immediately (before background task)
        generate_button.visible = False
        text_extraction_animation.visible = True
        status_label.text = "Extracting content from the document..."

        # Enable browser close warning
        # await ui.run_javascript('window.startProcessing()')

        # Add mobile guidance notification for all users (simple approach)
        ui.notify('📱 Mobile users: Keep this tab active and screen on during processing to avoid interruptions.',
                  type='info', timeout=10000)

        async def background_job():
            """
            Pure background processing - NO UI UPDATES AT ALL
            Only sets session variables that the polling function can read
            """
            try:
                session.processing_status = "extracting"

                # --- TEXT EXTRACTION ---
                try:
                    extracted_json = await run.io_bound(
                        lambda: send_msg_to_ai(session.uploaded_file_path, session.processing_session_id)
                    )

                    # Check if extraction returned an error
                    if isinstance(extracted_json, dict) and "error_type" in extracted_json:
                        log_processing_failure(
                            session.processing_session_id,
                            extracted_json["error_type"],
                            extracted_json["technical_error"],
                            "extraction"
                        )

                        session.processing_status = "error"
                        session.processing_error = extracted_json
                        return

                except Exception as e:
                    log_processing_failure(
                        session.processing_session_id,
                        "UNEXPECTED_ERROR",
                        f"Unexpected extraction error: {str(e)}",
                        "extraction"
                    )
                    report_error(f"Unexpected Background Error: {str(e)}")

                    session.processing_status = "error"
                    session.processing_error = {
                        "error_type": "UNEXPECTED_ERROR",
                        "user_message": "Something unexpected happened. Please try again!",
                        "technical_error": str(e)
                    }
                    return

                # --- NOTES GENERATION ---
                session.processing_status = "generating"

                try:
                    notes_generated = await run.io_bound(
                        lambda: generate_notes_from_content(extracted_json, session.processing_session_id)
                    )

                    # Check if notes generation returned an error
                    if isinstance(notes_generated, dict) and "error_type" in notes_generated:
                        log_processing_failure(
                            session.processing_session_id,
                            notes_generated["error_type"],
                            notes_generated["technical_error"],
                            "generation"
                        )

                        session.processing_status = "error"
                        session.processing_error = notes_generated
                        return

                    # Additional validation for empty notes
                    if not notes_generated:
                        log_processing_failure(
                            session.processing_session_id,
                            "NOTES_GENERATION_ERROR",
                            "Notes generation returned empty content",
                            "generation"
                        )

                        report_error("Notes Generation Error: Empty content returned")
                        session.processing_status = "error"
                        session.processing_error = {
                            "error_type": "NOTES_GENERATION_ERROR",
                            "user_message": "We couldn't generate any notes from your document. Let's try again!",
                            "technical_error": "Empty content returned"
                        }
                        return

                except Exception as e:
                    log_processing_failure(
                        session.processing_session_id,
                        "UNEXPECTED_ERROR",
                        f"Unexpected generation error: {str(e)}",
                        "generation"
                    )

                    report_error(f"Notes Generation Error: {str(e)}")
                    session.processing_status = "error"
                    session.processing_error = {
                        "error_type": "UNEXPECTED_ERROR",
                        "user_message": "We encountered an issue while generating your notes. Please try again.",
                        "technical_error": str(e)
                    }
                    return

                # --- WORD FILE CREATION ---
                session.processing_status = "creating_file"

                try:
                    unique_name = f"{session.uploaded_file_name}_{uuid.uuid4().hex[:6]}.docx"
                    file_generated = await run.io_bound(generate_word_file, notes_generated,
                                                        file_name=unique_name.replace(' ', '_'))

                    # Prepare download
                    with open(file_generated, 'rb') as f:
                        file_content = f.read()
                    os.remove(file_generated)

                    base64_data = base64.b64encode(file_content).decode('utf-8')
                    mime_type = mimetypes.guess_type("Notes.docx")[0] or "application/octet-stream"

                    log_processing_success(session.processing_session_id)

                    # Store result for polling function
                    session.processing_result = {
                        "base64_data": base64_data,
                        "mime_type": mime_type,
                        "filename": f"{session.uploaded_file_name}_Notes.docx"
                    }
                    session.processing_status = "completed"

                except Exception as e:
                    log_processing_failure(
                        session.processing_session_id,
                        "WORD_FILE_ERROR",
                        f"Word file creation error: {str(e)}",
                        "word_generation"
                    )

                    report_error(f"Word File Creation Error: {str(e)}")
                    session.processing_status = "error"
                    session.processing_error = {
                        "error_type": "WORD_FILE_ERROR",
                        "user_message": "Almost there! Had trouble creating the Word file. Let's retry.",
                        "technical_error": str(e)
                    }
                    return

            except Exception as e:
                # Final catch-all error handler
                print(f"CRITICAL ERROR IN BACKGROUND JOB: {str(e)}")

                log_processing_failure(
                    session.processing_session_id,
                    "SYSTEM_ERROR",
                    f"Critical system error: {str(e)}",
                    "system"
                )

                report_error(f"CRITICAL System Error: {str(e)}")
                session.processing_status = "error"
                session.processing_error = {
                    "error_type": "SYSTEM_ERROR",
                    "user_message": "Something unexpected happened on our end. We're on it!",
                    "technical_error": str(e)
                }

        # Start the background job
        background_tasks.create(background_job())

        # Start polling for updates (this runs in main UI thread)
        check_processing_status()

    # --- UI Layout ---
    with ui.column().classes(
            'absolute inset-0 w-full h-full overflow-x-hidden bg-gradient-to-tr '
            'from-emerald-200 via-white to-indigo-100 px-3 sm:px-6 py-6 sm:py-12 text-base sm:text-lg'):

        with ui.column().classes('w-full items-center'):
            ui.label('NotesCraft AI') \
                .classes(
                'text-4xl md:text-5xl font-bold bg-gradient-to-r from-emerald-600 to-emerald-800 bg-clip-text text-transparent text-center mb-3')

            ui.label('Transform documents into structured, comprehensive notes') \
                .classes('text-lg md:text-xl text-gray-600 text-center mb-6 px-4 max-w-3xl')

        with ui.card().classes(
                'w-full max-w-2xl sm:max-w-3xl mx-auto p-6 sm:p-8 bg-white/90 backdrop-blur-lg shadow-2xl rounded-3xl border border-gray-200 flex flex-col items-center space-y-4'):
            upload_container = ui.column().classes('w-full items-center')

            def handle_upload(e):
                # Store file details temporarily for confirmation
                temp_file_name = e.name
                temp_content = e.content.read()

                if not temp_content:
                    ui.notify("⚠️ Upload failed: empty file received.", type="warning")
                    return

                file_size = len(temp_content)
                suffix = Path(temp_file_name).suffix or ".pdf"

                # Create temporary file for validation
                with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    temp_file.write(temp_content)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                    temp_file_path = Path(temp_file.name)

                # Validate file before showing confirmation
                is_valid, error_msg, page_count = validate_file(temp_file_path, file_size)

                if not is_valid:
                    # Clean up temp file and show error
                    os.unlink(temp_file_path)
                    ui.notify(f"⚠️ {error_msg}", type="negative", timeout=5000)
                    return

                # Calculate estimated time for display
                estimated_time_seconds = calculate_estimated_time(page_count, file_size / (1024 * 1024))
                estimated_time_text = format_time_remaining(estimated_time_seconds)

                def confirm_upload():
                    # Store in session for use during processing
                    session.estimated_total_time = estimated_time_seconds
                    session.uploaded_file_name = temp_file_name
                    session.uploaded_file_path = temp_file_path

                    # Get logged in user's email
                    user_email = session.get('user_email', 'unknown')

                    session.processing_session_id = start_file_processing(
                        temp_file_name,
                        file_size / (1024 * 1024),
                        page_count,
                        user_email
                    )

                    # Show cleaner uploaded file UI
                    upload_container.clear()
                    with upload_container:
                        with ui.card().classes(
                                'w-full max-w-md p-6 rounded-2xl border border-emerald-200 '
                                'bg-emerald-50 text-center shadow-md flex flex-col items-center justify-center'
                        ):
                            # PDF file icon
                            ui.html('<div class="text-red-500 text-4xl mb-2">📄</div>')

                            ui.label('File Uploaded').classes('text-base font-semibold text-emerald-700 mb-1')
                            # ui.label(temp_file_name).classes('text-lg font-bold text-gray-800')
                            ui.label(temp_file_name) \
                                .classes('text-lg font-bold text-gray-800 truncate w-full max-w-[250px]') \
                                .tooltip(temp_file_name)

                def cancel_upload():
                    # User cancelled - clean up temp file and go back to upload area
                    os.unlink(temp_file_path)
                    render_upload()

                # Show inline confirmation instead of popup
                upload_container.clear()
                with upload_container:
                    with ui.card().classes(
                            'w-full max-w-md p-6 rounded-2xl border border-gray-300 '
                            'bg-gray-50 text-center shadow-md flex flex-col items-center justify-center'
                    ):
                        # File icon (PDF only)
                        ui.html('<div class="text-red-500 text-4xl mb-3">📄</div>')

                        # ui.label(temp_file_name).classes('text-lg font-bold text-gray-800 mb-3')
                        ui.label(temp_file_name) \
                            .classes('text-lg font-bold text-gray-800 mb-3 truncate max-w-full sm:max-w-[300px]') \
                            .tooltip(temp_file_name)

                        ui.label('Please confirm this is the file you\'d like to upload').classes(
                            'text-base font-medium text-gray-700 mb-1')
                        ui.label('The uploading may take a few seconds depending on file size.').classes(
                            'text-sm text-gray-600 mb-4')

                        # File details - mobile-friendly layout
                        with ui.column().classes('w-full mb-4 space-y-2 items-center'):
                            # File info on one line
                            with ui.row().classes('justify-center gap-4 text-sm text-gray-600'):
                                ui.label(f'{page_count} pages')
                                ui.label('•')
                                ui.label(f'{file_size / 1024 / 1024:.1f} MB')

                            # Processing time on separate line with clear context
                            ui.label(f'Processing time: ~{estimated_time_text}').classes(
                                'text-sm text-blue-600 font-medium bg-blue-50 px-3 py-1 rounded-full text-center')

                        # Action buttons
                        with ui.row().classes('gap-3'):
                            ui.button('Confirm', on_click=confirm_upload).props('unelevated').classes(
                                'bg-emerald-500 text-white px-6 py-2 font-semibold rounded-lg hover:bg-emerald-600'
                            )
                            ui.button('Cancel', on_click=cancel_upload).props('outline').classes(
                                'text-gray-600 border-gray-400 px-6 py-2 font-semibold rounded-lg hover:bg-gray-100'
                            )

            def render_upload():
                upload_container.clear()
                with upload_container:
                    uploader = ui.upload(label='', on_upload=handle_upload, auto_upload=True, multiple=False).props(
                        'accept=.pdf').classes('hidden')

                    with ui.card().classes(
                            'w-full max-w-xl h-48 border-2 border-dashed border-gray-300 bg-white/80 '
                            'hover:bg-emerald-50 rounded-2xl flex flex-col items-center justify-center '
                            'cursor-pointer transition-all text-center shadow-md'
                    ).on('click', lambda: uploader.run_method('pickFiles')):
                        ui.icon('cloud_upload').classes('text-5xl text-emerald-600')
                        ui.label('Click to upload your PDF').classes('text-lg font-medium text-gray-700')
                        ui.label('or drag and drop here').classes('text-sm text-gray-500')

                    # Add page limit info below the upload area
                    ui.label(f'Maximum {MAX_PAGES} pages allowed').classes('text-xs text-gray-400 mt-2 text-center')

            render_upload()

            with ui.column().classes('w-full items-center'):
                with ui.column().classes('w-full items-center sm:flex-row sm:justify-center sm:gap-6 mt-2'):
                    text_extraction_animation = ui.html("""
                        <lottie-player src="/assets/document-search.json" background="transparent" speed="1"
                                       style="width: 130px; height: 130px;" loop autoplay></lottie-player>
                    """)
                    text_extraction_animation.visible = False

                    notes_generation_animation = ui.html("""
                        <lottie-player src="/assets/generate_notes.json" background="transparent" speed="1"
                                       style="width: 130px; height: 130px;" loop autoplay></lottie-player>
                    """)
                    notes_generation_animation.visible = False

                    word_file_generation_animation = ui.html("""
                        <lottie-player src="/assets/generate_word_file.json" background="transparent" speed="1"
                                       style="width: 130px; height: 130px;" loop autoplay></lottie-player>
                    """)
                    word_file_generation_animation.visible = False

                status_label = ui.label('').classes(
                    'text-gray-900 mt-3 text-center text-base sm:text-lg font-medium'
                )

                time_label = ui.label('').classes(
                    'text-blue-600 mt-1 text-center text-sm font-semibold bg-blue-50 px-4 py-2 rounded-full inline-block'
                )
                time_label.visible = False

                error_label = ui.label('').classes('mt-3 text-base sm:text-lg text-rose-500 font-semibold text-center')

            # Single persistent download handler that uses session data
            def handle_download():
                if hasattr(session, 'download_data') and session.download_data:
                    data = session.download_data
                    ui.run_javascript(f"""
                        const link = document.createElement('a');
                        link.href = "data:{data['mime_type']};base64,{data['base64_data']}";
                        link.download = "{data['filename']}";
                        link.click();
                    """)
                    if hasattr(session, 'processing_session_id'):
                        file_logger.update_download_status(session.processing_session_id)

                    # Disable warnings after download starts
                    ui.timer(0.1, lambda: ui.run_javascript('window.fileDownloaded()'), once=True)

            download_button = ui.button('Download Notes', on_click=handle_download).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-4 py-2 text-base font-medium shadow-sm transition-all duration-200 text-center')
            download_button.visible = False

            feedback_url = "https://forms.gle/gPHd66XpZ1nM17si9"

            def open_feedback_form():
                js_code = f"window.open('{feedback_url}', '_blank');"
                ui.run_javascript(js_code)

            feedback_button = ui.button("📝 Give Feedback", on_click=open_feedback_form).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-3 px-4 py-2 text-sm font-medium shadow-sm transition-all duration-200 text-center')
            feedback_button.visible = False

            error_report_url = "https://forms.gle/Eqjk6SS1jtmWuXGg6"

            def open_error_report_form():
                js_code = f"window.open('{error_report_url}', '_blank');"
                ui.run_javascript(js_code)

            error_report_button = ui.button("🚩 Report Error ", on_click=open_error_report_form).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-3 px-4 py-2 text-sm font-medium shadow-sm transition-all duration-200 text-center')
            error_report_button.visible = False

            generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-5 py-3 text-lg font-semibold shadow-sm transition-all duration-200 text-center')

            reset_button = ui.button('🔄 Upload Another File', on_click=reset_app).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-3 px-4 py-2 text-sm font-medium shadow-sm transition-all duration-200 text-center')
            reset_button.visible = False

            try_again_button = ui.button('🔄 Try Again', on_click=reset_app).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-3 px-4 py-2 text-sm font-medium shadow-sm transition-all duration-200 text-center')
            try_again_button.visible = False


ui.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)),
       storage_secret=os.environ.get('STORAGE_SECRET', secrets.token_hex(32)),
       title='NotesCraft AI – Smart Notes Maker')

