import asyncio
import base64
import mimetypes
import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
import secrets
import requests
from nicegui import ui, app, background_tasks, run
from process_content_to_notes_base import generate_notes_from_content
from process_pdf_to_Json import send_msg_to_ai
from process_to_word_02 import generate_word_file

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# Ensure root container fills full viewport on mobile
ui.add_head_html("""
<style>
html, body, #__nicegui_root {
    height: 100%;
    margin: 0;
    padding: 0;
}
</style>
""")


@ui.page('/')
def main_page():
    ui.add_head_html('<link rel="icon" href="assets/favicon.ico">')

    session = app.storage.user
    session.uploaded_file_path = None
    session.uploaded_file_name = "Notes"

    # --- Helper Functions ---
    def report_error(Error):
        if Error:
            try:
                requests.post(
                    'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec',
                    json={"Error": Error},
                )
            except Exception as e:
                print(f"Error reporting failed: {e}")

    def reset_app():
        session.uploaded_file_path = None
        session.uploaded_file_name = "Notes"

        status_label.text = ""
        spinner.visible = False
        animation_placeholder.visible = False
        download_button.visible = False

        generate_button.visible = True
        reset_button.visible = False

        # feedback_label.visible = False
        # feedback_input.visible = False
        # submit_feedback_button.visible = False

        error_label.text = ""
        try_again_button.visible = False

        render_upload()
        ui.notify("Ready for another file!")

    # def submit_feedback():
    #     feedback = feedback_input.value.strip()
    #     if not feedback:
    #         ui.notify("Please write something before submitting!", type="warning")
    #         return
    #
    #     ui.notify("✉️ Sending your feedback...")
    #
    #     async def send_async():
    #         try:
    #             await asyncio.to_thread(
    #                 requests.post,
    #                 'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec',
    #                 json={"Feedback": feedback},
    #             )
    #             feedback_input.value = ""
    #             ui.notify("✅ Feedback sent!")
    #         except Exception as e:
    #             ui.notify(f"❌ Feedback failed: {e}", type="negative")
    #
    #     background_tasks.create(send_async())

    async def process_with_ai():
        if not session.uploaded_file_path or not session.uploaded_file_path.exists():
            ui.notify(message='Please Upload a File', type='warning')
            return

        async def background_job():

            try:
                generate_button.visible = False
                spinner.visible = True
                animation_placeholder.visible = True
                status_label.text = "📄 Extracting Content from the document..."
                ui.update()

                # extracted_json = await run.io_bound(send_msg_to_ai, session.uploaded_file_path)
                extracted_json = "Abc"
                if not extracted_json:
                    error_label.text = "⚠️ Failed to extract text. Please try another file."
                    spinner.visible = False
                    animation_placeholder.visible = False
                    try_again_button.visible = True
                    generate_button.visible = False
                    ui.update()
                    return

                status_label.text = "🤖 AI Analyzing and Generating Notes..."
                ui.update()

                notes_generated = await run.io_bound(generate_notes_from_content, extracted_json)

                status_label.text = "📕 Preparing Word File..."
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

                download_button.on('click', trigger_download)

                status_label.text = "✅ Your Notes are Ready!"
                spinner.visible = False
                animation_placeholder.visible = False
                download_button.visible = True

                # feedback_label.visible = True
                # feedback_input.visible = True
                # submit_feedback_button.visible = True

                reset_button.visible = True
                ui.update()

            except Exception as e:
                report_error(str(e))
                error_label.text = "⚠️ Something went wrong. Please try again."
                spinner.visible = False
                animation_placeholder.visible = False
                try_again_button.visible = True
                ui.update()

        background_tasks.create(background_job())

    with ui.column().classes(
            'items-center w-full min-h-screen bg-gradient-to-br from-emerald-50 to-blue-50 p-4 sm:p-6'):
        ui.label('📚 NotesCraft AI').classes(
            'text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-blue-600 text-center')
        ui.label('Transform your PDFs into beautiful, structured study notes.').classes(
            'text-lg sm:text-xl text-gray-700 text-center mb-6 sm:mb-8 px-2 sm:px-4')

        with ui.card().classes(
                'w-full max-w-2xl sm:max-w-3xl mx-auto p-6 sm:p-8 bg-white/90 backdrop-blur-lg shadow-2xl rounded-3xl border border-gray-200 flex flex-col items-center space-y-4'):
            upload_container = ui.column().classes('w-full items-center')

            def handle_upload(e):
                session.uploaded_file_name = e.name
                with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(e.content.read())
                    session.uploaded_file_path = Path(temp_file.name)

                upload_container.clear()
                with upload_container:
                    with ui.card().classes(
                            'w-full max-w-xl p-6 sm:p-8 rounded-2xl border border-emerald-300 bg-emerald-50 text-center shadow-md flex flex-col items-center justify-center'):
                        ui.icon("picture_as_pdf").classes("text-red-500 text-5xl sm:text-6xl")
                        ui.label(session.uploaded_file_name).classes(
                            "text-lg sm:text-xl font-semibold text-gray-800 mt-2")
                        ui.label("File Uploaded Successfully ✅").classes("text-sm sm:text-base text-gray-600 mt-1")

            def render_upload():
                upload_container.clear()
                with upload_container:
                    uploader = ui.upload(label='', on_upload=handle_upload, auto_upload=True, multiple=False).props(
                        'accept=.pdf,.docx').classes('hidden')
                    with ui.card().classes(
                            'w-full max-w-xl h-44 sm:h-48 border-2 border-dashed border-gray-300 bg-white/80 hover:bg-emerald-50 rounded-2xl flex flex-col items-center justify-center cursor-pointer transition-all text-center shadow-md').on(
                            'click', lambda: uploader.run_method('pickFiles')):
                        ui.icon('cloud_upload').classes('text-5xl sm:text-6xl text-emerald-600')
                        ui.label('Click to upload your PDF or Word file').classes(
                            'text-lg sm:text-xl font-medium text-gray-700 mt-2')

            render_upload()

            status_label = ui.label('').classes('text-gray-800 mt-3 text-base sm:text-lg text-center')
            error_label = ui.label('').classes('mt-3 text-base sm:text-lg text-rose-500 font-semibold text-center')
            spinner = ui.spinner(size='lg').classes('text-emerald-600 mt-4')
            spinner.visible = False

            animation_placeholder = ui.card().classes(
                'w-full max-w-md h-36 sm:h-40 flex items-center justify-center bg-gradient-to-r from-emerald-100 to-blue-100 rounded-2xl shadow-inner text-gray-500 font-medium mt-4')
            animation_placeholder.visible = False
            with animation_placeholder:
                ui.label("✨ Animation will appear here...")

            download_button = ui.button('Download Notes').props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-4 sm:px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center')

            download_button.visible = False

            generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-4 sm:px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center')


            reset_button = ui.button('🔄 Upload Another File', on_click=reset_app).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-4 sm:px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center')


            reset_button.visible = False


            try_again_button = ui.button('🔄 Try Again', on_click=reset_app).props(
                'unelevated rounded color=indigo text-color=white').classes(
                'w-full max-w-md mx-auto mt-4 sm:mt-6 px-4 sm:px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center')


            try_again_button.visible = False

            # feedback_label = ui.label('✍️ Share your thoughts about NotesCraft').classes(
            #     'text-base sm:text-lg font-semibold text-gray-800 mt-6 text-center')
            #
            # feedback_input = ui.textarea(label='Your Feedback', placeholder='What can we improve?').classes('w-full')
            #
            #
            # submit_feedback_button = ui.button('Submit Feedback', icon='send', on_click=submit_feedback).classes(
            #     'bg-blue-600 text-white mt-2 hover:bg-blue-700')
            #
            # feedback_label.visible = False
            # feedback_input.visible = False
            # submit_feedback_button.visible = False


ui.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)),
       storage_secret=os.environ.get('STORAGE_SECRET', secrets.token_hex(32)),
       title='NotesCraft AI – Smart Notes Maker')

