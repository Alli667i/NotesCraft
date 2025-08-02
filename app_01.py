import base64
import mimetypes
import os
import time
import threading
import uuid
from nicegui import ui, app
from pathlib import Path
from tempfile import NamedTemporaryFile
from process_content_to_notes_base import generate_notes_from_content
from process_to_word_02 import generate_word_file
from process_pdf_to_Json import send_msg_to_ai
import requests
import secrets

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))



@ui.page('/')
def main_page():

    ui.add_head_html('<link rel="icon" href="assets/favicon.ico">')

    session = app.storage.user
    session.uploaded_file_path = None
    session.uploaded_file_name = "Notes"

    welcome_popup = ui.dialog()

    def handle_upload(e):
        session.uploaded_file_name = e.name
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(e.content.read())
            session.uploaded_file_path = Path(temp_file.name)
        ui.notify("File successfully Uploaded!")

    def process_with_ai():
        if not session.uploaded_file_path or not session.uploaded_file_path.exists():
            ui.notify(message='Please Upload a File', type='warning')
            return

        def background_task():
            generate_button.visible = False
            spinner.visible = True
            status_label.text = "📄 Extracting Content from the document"
            ui.update()

            extracted_json = send_msg_to_ai(session.uploaded_file_path)

            if extracted_json:
                status_label.text = "✅ Content Extracted Successfully"
                ui.update()
                time.sleep(2)
                try:
                    status_label.text = "🛠 Generating Notes "
                    ui.update()

                    notes_generated = generate_notes_from_content(extracted_json)
                    status_label.text = "📄 Generating Word File"
                    ui.update()

                    unique_name = f"{session.uploaded_file_name}_{uuid.uuid4().hex[:6]}.docx"
                    file_generated = generate_word_file(notes_generated, file_name=unique_name.replace(' ', '_'))

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

                    status_label.text = "📕 Your Notes are Ready!"
                    spinner.visible = False
                    download_button.visible = True
                    time.sleep(3)

                    feedback_label.visible = True
                    feedback_input.visible = True
                    submit_feedback_button.visible = True
                    time.sleep(3.5)

                    reset_button.visible = True

                except Exception as e:

                    ui.notify(f"❌ Error while generating Notes: {e}", type='negative')
            else:
                ui.notify("❌ Failed to extract content.", type='negative')
            ui.update()

        threading.Thread(target=background_task).start()


    def reset_app():

        session.uploaded_file_path = None
        session.uploaded_file_name = "Notes"
        status_label.text = ""
        spinner.visible = False
        download_button.visible = False
        generate_button.visible = True
        reset_button.visible = False
        feedback_label.visible = False
        feedback_input.visible = False
        submit_feedback_button.visible = False
        upload_component.reset()
        ui.notify("Ready for another file!")


    def submit_feedback():

        feedback = feedback_input.value.strip()

        if not feedback:
            ui.notify("Please write something before submitting!", type="warning")
            return



        payload = {"Feedback": feedback}

        try:
            requests.post(
                'https://script.google.com/macros/s/AKfycbxVqOxMMrwj0DUvfCARivTz7XIhIncxOE-U_Qy4stjNLJHJlHFX4J6ktZX8xSFXRne3/exec',
                json=payload
            )


            ui.notify("✅ Thank you for your feedback!")
            ui.update()

            feedback_input.value = ""

        except Exception as e:

            ui.notify(f"❌ Failed to send feedback: {e}", type="negative")

    with ui.column().classes('items-center w-full p-4 text-sm'):

        with ui.row().classes('items-center justify-center gap-4'):
            # ui.image('/assets/logo3.svg').classes('w-12 h-12 rounded-full')
            ui.label('NotesCraft AI – Powered by Intelligence, Built for Learners') \
                .classes('text-2xl md:text-4xl font-bold text-emerald-800 text-center')

        ui.label('Transform your PDFs into professional study notes using the power of AI.') \
            .classes('text-base md:text-lg text-gray-600 text-center mb-6 px-4')

        with ui.card().classes('w-full max-w-md p-4 bg-white shadow rounded-lg border border-gray-200'):
            upload_component = ui.upload(
                label='📄 Upload PDF or Word File',
                auto_upload=True,
                multiple=False,
                on_upload=handle_upload
            ).classes('w-full h-40 border-2 border-dashed border-emerald-300 rounded-xl text-emerald-600 bg-emerald-50 text-sm flex items-center justify-center')

            status_label = ui.label('').classes('text-gray-800 mt-3 text-base')

            with ui.row().classes('w-full justify-center items-center'):
                spinner = ui.spinner(size='md').classes('text-emerald-600 mt-2')
                spinner.visible = False

            download_button = ui.button('Download Notes').props('icon=download').classes(
                'w-full mt-3 bg-emerald-500 text-white text-sm font-medium rounded-md hover:bg-emerald-600'
            )
            download_button.visible = False

            generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).classes(
                'w-full mt-4 bg-emerald-500 text-white text-sm font-semibold rounded-md shadow-md hover:bg-emerald-600'
            )

            reset_button = ui.button('🔄 Upload Another File', on_click=reset_app).classes(
                'w-full mt-2 bg-gray-200 text-gray-800 text-sm font-semibold rounded-md shadow-sm hover:bg-gray-300'
            )
            reset_button.visible = False


            feedback_label = ui.label('✍️ Share your thoughts about NotesCraft').classes(
                'text-base font-semibold text-gray-800 mt-6')

            feedback_input = ui.textarea(label='Your Feedback', placeholder='What can we improve?').classes('w-full')


            submit_feedback_button = ui.button('Submit Feedback', icon='send', on_click=submit_feedback).classes(
                'bg-blue-600 text-white mt-2 hover:bg-blue-700')

            feedback_label.visible = False
            feedback_input.visible = False
            submit_feedback_button.visible = False


            with welcome_popup:

                with ui.card().classes('bg-blue-50 text-gray-800 shadow-xl rounded-xl p-6 max-w-xl mx-auto'):

                    ui.label('📘 Welcome to NotesCraft').classes('text-2xl font-bold text-blue-900 mb-4')

                    ui.label('No more stress making study notes.').classes('text-base font-medium text-indigo-800 mb-2')

                    ui.label('Just upload your class PDF, slides, or handouts — we’ll turn them into clear, exam-ready notes.')\
                        .classes('text-base mb-2')

                    ui.label(
                        '✅ Smart note-making in minutes\n'
                        '✅ No formatting or editing needed\n'
                        '✅ You focus on learning, we handle the rest'
                    ).classes('text-sm mb-4 whitespace-pre-line')

                    ui.label('Fast. Accurate. Reliable.').classes('text-sm italic text-gray-700 mb-4')

                    ui.button('Get Started 🚀', on_click=welcome_popup.close).classes(
                        'bg-blue-600 text-white hover:bg-blue-700 rounded-md')

    with ui.footer().classes('w-full flex flex-col items-center justify-center py-4 bg-gray-50'):
        ui.label('⚡ NotesCraft AI is just getting started!').classes('text-base font-semibold text-indigo-900 text-center')
        ui.label('This early version may not be perfect yet — but we’re improving it every day!').classes('text-sm text-gray-700 text-center px-6')

    ui.timer(1.0, welcome_popup.open, once=True)

ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
    storage_secret=os.environ.get('STORAGE_SECRET', secrets.token_hex(32)),
    title='NotesCraft AI – Smart Notes Maker'
)
