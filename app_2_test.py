import os
import secrets
import time
import threading
from nicegui import ui, app
from pathlib import Path
from tempfile import NamedTemporaryFile

from nicegui import ui, app, background_tasks, run

from process_content_to_notes_02 import generate_notes_from_content
from process_to_word_02 import generate_word_file
from dotenv import load_dotenv
from process_pdf_to_Json import send_msg_to_ai
from Instructions_for_Notes_genearation import for_detail_notes, for_summarize_notes

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 📂 Make assets available
app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# 🎨 Global styling and animation script
ui.add_head_html("""
<style>
  body {
    background-color: #f1f5f9;
    font-family: 'Segoe UI', sans-serif;
  }
  ::placeholder {
    color: #94a3b8;
  }
</style>
""")
ui.add_head_html("""
<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
""")


@ui.page('/')
def main_page():
    session = app.storage.user
    session.uploaded_file_path = None
    session.original_filename = "Notes"

    note_options = {
        "📝  In-Depth Notes": for_detail_notes,
        "📌 Quick Summary": for_summarize_notes
    }

    async def process_with_ai():
        session = app.storage.user

        if not session.uploaded_file_path or not session.uploaded_file_path.exists():
            ui.notify(message='Please Upload a File', type='warning')
            return

        async def background_job():
            with card:
                generate_button.visible = False
                try_again_button.visible = False
                spinner.visible = True
                status_label.text = "📄 Extracting Content from the document"
                error_label.text = ""
                ui.update()

            try:
                extracted_json = await run.io_bound(send_msg_to_ai, session.uploaded_file_path)

                if not extracted_json:
                    with card:
                        ui.notify("Text extraction failed. Try again or upload another file.", type='negative')
                        status_label.text = ""
                        error_label.text = "⚠️ We couldn't extract text from your PDF. Please try again or use a different file."
                        spinner.visible = False
                        try_again_button.visible = True
                        ui.update()
                    return

                with card:
                    status_label.text = "🛠 Generating Notes"
                    ui.update()

                notes_generated = await run.io_bound(generate_notes_from_content, extracted_json)

                with card:
                    status_label.text = "📄 Generating Word File"
                    ui.update()

                unique_name = f"{session.uploaded_file_name}_{uuid.uuid4().hex[:6]}.docx"
                file_generated = await run.io_bound(generate_word_file, notes_generated,
                                                    file_name=unique_name.replace(' ', '_'))

                with open(file_generated, 'rb') as f:
                    file_content = f.read()
                os.remove(file_generated)

                base64_data = base64.b64encode(file_content).decode('utf-8')
                mime_type = mimetypes.guess_type("Notes.docx")[0] or "application/octet-stream"

                def trigger_download():
                    ui.run_javascript(f"""
                        const link = document.createElement('a');
                        link.href = "data:{mime_type};base64,{base64_data}";
                        link.download = "{session.uploaded_file_name}_Notes.docx";
                        link.click();
                    """)

                with card:
                    download_button.on('click', trigger_download)
                    status_label.text = "📕 Your Notes are Ready!"
                    spinner.visible = False
                    download_button.visible = True
                    feedback_label.visible = True
                    feedback_input.visible = True
                    submit_feedback_button.visible = True
                    reset_button.visible = True
                    ui.update()

            except Exception as e:
                with card:
                    ui.notify("❌ Something went wrong while generating your notes. Please try again.", type="negative")
                    report_error(str(e))
                    status_label.text = ""
                    error_label.text = "⚠️ Something went wrong. We're working to fix it. Please try again."
                    spinner.visible = False
                    try_again_button.visible = True
                    ui.update()

        background_tasks.create(background_job())

    def reset_all():
        session.uploaded_file_path = None
        session.original_filename = "Notes"
        status_message.text = ''
        download_button.visible = False
        generate_button.visible = True
        word_file_generation_animation.visible = False
        selected_prompt.visible = True
        selected_prompt.value = list(note_options.keys())[0]
        render_upload()
        reset_button.visible = False
        status_label.visible = False
        ui.notify('Reset successful! You can upload a new file.')
        ui.update()

    def confirm_file_upload():
        upload_container.clear()
        with upload_container:
            with ui.card().classes(
                'w-full max-w-xl p-6 rounded-2xl bg-gradient-to-br from-emerald-100 to-white '
                'shadow-xl border border-emerald-300 flex items-center space-x-4'
            ):
                ui.image('/assets/Doc_pic.png').classes("w-10 h-10")
                with ui.column().classes('items-start'):
                    ui.label("File Uploaded").classes('text-sm font-medium text-emerald-600')
                    ui.label(session.original_filename).classes(
                        'text-lg font-semibold text-emerald-900 truncate max-w-xs'
                    )
                ui.notify("✅ File Uploaded Successfully!")

    def handle_files(e):
        session.original_filename = e.name
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(e.content.read())
            session.uploaded_file_path = Path(temp_file.name)

        upload_container.clear()
        with upload_container:
            with ui.card().classes(
                'w-full max-w-xl p-6 rounded-2xl border border-emerald-300 bg-emerald-50 '
                'text-center shadow-md flex flex-col items-center justify-center'
            ):
                with ui.row().classes("justify-center items-center mb-4"):
                    with ui.card().classes(
                            "bg-white shadow-md px-4 py-2 rounded-xl flex items-center gap-3 border border-emerald-300"
                    ):
                        ui.icon("picture_as_pdf").classes("text-red-500 text-3xl")
                        ui.label(session.original_filename).classes("text-lg font-medium text-gray-800")

                ui.label("Please confirm this is the file you'd like to upload").classes(
                    'text-base font-medium text-gray-800 mb-2'
                )
                ui.label("The uploading may take a few seconds depending on file size.").classes(
                    'text-sm text-gray-600 mb-4'
                )

                with ui.row().classes("gap-4"):
                    ui.button("✅ Confirm", on_click=confirm_file_upload).classes(
                        'bg-emerald-500 text-white px-5 py-2 rounded-lg hover:bg-emerald-600 transition-all'
                    )
                    ui.button("❌ Cancel", on_click=render_upload).classes(
                        'bg-gray-300 text-gray-800 px-5 py-2 rounded-lg hover:bg-gray-400 transition-all'
                    )

    def render_upload():
        upload_container.clear()
        with upload_container:
            uploader = ui.upload(
                on_upload=handle_files,
                auto_upload=True,
                multiple=False
            ).props('accept=.pdf').classes('hidden')

            with ui.card().classes(
                'w-full max-w-xl h-48 border-2 border-dashed border-gray-300 bg-white/80 '
                'hover:bg-emerald-50 rounded-2xl flex flex-col items-center justify-center '
                'cursor-pointer transition-all text-center shadow-md'
            ).on('click', lambda: uploader.run_method('pickFiles')):
                ui.icon('cloud_upload').classes('text-5xl text-emerald-600')
                ui.label('Click to upload your PDF').classes('text-lg font-medium text-gray-700')
                ui.label('or drag and drop here (not active yet)').classes('text-sm text-gray-500')

    # 🌐 Main UI Layout
    with ui.column().classes(
        'absolute inset-0 w-full h-full overflow-x-hidden bg-gradient-to-tr '
        'from-emerald-200 via-white to-indigo-100 px-3 sm:px-6 py-6 sm:py-12 text-base sm:text-lg'):

        with ui.column().classes('w-full items-center'):
            ui.label('NotesCraft AI – Powered by Intelligence, Built for Learners') \
                .classes('text-2xl md:text-4xl font-bold text-emerald-800 text-center')

            ui.label('Transform your PDFs into professional study notes using the power of AI.') \
                .classes('text-base md:text-lg text-gray-600 text-center mb-6 px-4')

        with ui.card().classes(
            'w-full max-w-2xl sm:max-w-3xl mx-auto p-4 sm:p-8 bg-white/90 backdrop-blur-md shadow-2xl '
            'rounded-2xl border border-gray-300'
        ):
            upload_container = ui.column().classes('w-full items-center')
            render_upload()

            selected_prompt = ui.select(
                options=list(note_options.keys()),
                value=list(note_options.keys())[0],
                label='📚 Choose how to generate your notes'
            ).classes(
                'w-full max-w-md mx-auto mt-5 px-4 py-2 text-sm sm:text-base bg-white border border-gray-300 rounded-full shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400'
            )
            selected_prompt.visible = True

            status_label = ui.label('Status:').classes(
                'text-indigo-700 mt-4 text-base sm:text-lg font-semibold'
            )
            status_label.visible = False

            with ui.column().classes('w-full items-center'):
                with ui.column().classes('w-full items-center sm:flex-row sm:justify-center sm:gap-6 mt-2'):
                    text_extraction_animation = ui.html("""
                        <lottie-player src="/assets/document-search.json" background="transparent" speed="1"
                                       style="width: 120px; height: 120px;" loop autoplay></lottie-player>
                    """)
                    text_extraction_animation.visible = False

                    notes_generation_animation = ui.html("""
                        <lottie-player src="/assets/generate_notes.json" background="transparent" speed="1"
                                       style="width: 120px; height: 120px;" loop autoplay></lottie-player>
                    """)
                    notes_generation_animation.visible = False

                    word_file_generation_animation = ui.html("""
                        <lottie-player src="/assets/generate_word_file.json" background="transparent" speed="1"
                                       style="width: 120px; height: 120px;" loop autoplay></lottie-player>
                    """)
                    word_file_generation_animation.visible = False

                status_message = ui.label('').classes(
                    'text-gray-900 mt-3 text-center text-base sm:text-lg font-medium'
                )

            download_button = ui.button('⬇️ Download Notes').props(
                'unelevated rounded color=indigo text-color=white'
            ).classes(
                'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
            )
            download_button.visible = False

            generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).props(
                'unelevated rounded color=indigo text-color=white'
            ).classes(
                'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
            )

            reset_button = ui.button('🔄 Start Over', on_click=reset_all).props(
                'unelevated rounded color=indigo text-color=white'
            ).classes(
                'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
            )
            reset_button.visible = False


# 🚀 Run the app
ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
    storage_secret=os.environ.get('STORAGE_SECRET', secrets.token_hex(32)),
    title='NotesCraft AI – Smart Notes Maker'
)
