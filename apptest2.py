import base64
import mimetypes
import os
import time
import threading
import uuid
from nicegui import ui , app
from pathlib import Path
from tempfile import NamedTemporaryFile
from process_content_to_notes_base import generate_notes_from_content
from process_to_word_02 import generate_word_file
from process_pdf_to_Json import send_msg_to_ai
import requests
from datetime import datetime

# https://script.google.com/macros/s/AKfycbxYmVVJzAaolmd1yARTGbhDexlmTV8_CdOSPpoowHLayhYzh_ZYlPfkgxgRNbKFWFE6/exec


# This is used to set theme and color of the Web UI
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
# Used to add support for playing animations in the Web UI
ui.add_head_html("""
<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
""")



# Initially file is none as nothing is uploaded
uploaded_file_path = None

uploaded_file_name = "Notes"





def handle_upload(e):



    # Global variable to get the file path for any other function
    global uploaded_file_path,uploaded_file_name

    uploaded_file_name = e.name

    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:

        temp_file.write(e.content.read())

        uploaded_file_path = Path(temp_file.name)

    ui.notify("File successfully Uploaded!")




def process_with_ai():
    # Check if file is uploaded or not

    if not uploaded_file_path or not uploaded_file_path.exists():
        ui.notify(message='Please Upload a File', type='warning')
        return

    def background_task():

        # When the notes generation will start it will hide the Start button
        generate_button.visible = False

        # For showing loading animation
        spinner.visible = True

        # Informing user about what's happening
        status_label.text = "📄 Extracting Content from the document"

        # Updating these changes on UI
        ui.update()

        # Sending the uploaded file to AI for text Extraction
        extracted_json = send_msg_to_ai(uploaded_file_path)

        # If content is successfully extracted then
        if extracted_json:

            # Inform User for successful extraction
            status_label.text = "✅ Content Extracted Successfully"

            # Update changes on UI

            ui.update()

            # A small delay for smoothness
            time.sleep(2)

            try:
                # Generate Notes from the extracted content and inform User

                status_label.text = "🛠 Generating Notes "

                ui.update()

                # Send content to AI to Generate Notes from it
                notes_generated = generate_notes_from_content(extracted_json)

                # After successfully generating notes passing it to func to make Word Document of it

                status_label.text = "📄 Generating Word File"

                # Updating Changes
                ui.update()

                # Generating Word File
                # Give the generated file a unique name (with uploaded file name)
                unique_name = f"{uploaded_file_name}_{uuid.uuid4().hex[:6]}.docx"
                file_generated = generate_word_file(notes_generated, file_name=unique_name.replace(' ', '_'))

                # Read file and delete it
                with open(file_generated, 'rb') as f:
                    file_content = f.read()

                os.remove(file_generated)

                # Encode to base64
                base64_data = base64.b64encode(file_content).decode('utf-8')

                # Get MIME type
                mime_type = mimetypes.guess_type("Notes.docx")[0] or "application/octet-stream"

                # JavaScript to trigger download in browser
                def trigger_download():

                    ui.run_javascript(f"""
                        const link = document.createElement('a');
                        link.href = "data:{mime_type};base64,{base64_data}";
                        link.download = "{uploaded_file_name}_Notes.docx";
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

                time.sleep(5)

                reset_button.visible = True


            except Exception as e:

                # If notes generation fails then notify user

                ui.notify(f"❌ Error while generating Notes: {e}", type='negative')

        else:
            # If content Extraction fails then
            ui.notify("❌ Failed to extract content.", type='negative')

        ui.update()

    # Run this operation in a separate thread
    threading.Thread(target=background_task).start()


def reset_app():
    global uploaded_file_path, uploaded_file_name

    # Clear stored file info
    uploaded_file_path = None
    uploaded_file_name = "Notes"

    # Reset all UI elements
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

    ui.notify("Submitting Feedback...")

    ui.update()

    payload = {
        "Feedback": feedback,
    }
    try:
        requests.post(
            'https://script.google.com/macros/s/AKfycbxVqOxMMrwj0DUvfCARivTz7XIhIncxOE-U_Qy4stjNLJHJlHFX4J6ktZX8xSFXRne3/exec',  # replace with your actual URL
            json=payload
        )
        ui.notify("✅ Thank you for your feedback!")
        ui.update()

        feedback_input.value = ""

    except Exception as e:
        ui.notify(f"❌ Failed to send feedback: {e}", type="negative")


# Design of the Web UI

with ui.column().classes('items-center w-full p-4 text-sm'):
    ui.label('📘 NotesCraft AI — Your Personal Study Assistant') \
        .classes('text-2xl md:text-4xl font-bold text-emerald-800 text-center mt-6')

    ui.label('Upload your PDFs and get clean, exam-ready notes — instantly.') \
        .classes('text-base md:text-lg text-gray-600 text-center mb-6 px-4')

    with ui.card().classes('w-full max-w-md p-4 bg-white shadow rounded-lg border border-gray-200'):

        # To Show an Upload file Area for user to upload files
        upload_component = ui.upload(

            label='📄 Upload PDF or Word File',
            auto_upload=True,
            multiple=False,
            on_upload=handle_upload

        ).classes('w-full h-40 border-2 border-dashed border-emerald-300 rounded-xl text-emerald-600 bg-emerald-50 text-sm flex items-center justify-center')



        # Area were all the updates will be shown

        status_label = ui.label('').classes('text-gray-800 mt-3 text-base')

        # Create a popup dialog to welcome the user
        welcome_popup = ui.dialog()

        with welcome_popup:
            with ui.card().classes('bg-blue-50 text-gray-800 shadow-xl rounded-xl p-6 max-w-xl mx-auto'):
                ui.label('📘 Welcome to NotesCraft').classes('text-2xl font-bold text-blue-900 mb-4')

                ui.label('No more stress making study notes.').classes('text-base font-medium text-indigo-800 mb-2')

                ui.label(
                    'Just upload your class PDF, slides, or handouts — we’ll turn them into clear, exam-ready notes.').classes(
                    'text-base mb-2')

                ui.label(
                    '✅ Smart note-making in minutes\n'
                    '✅ No formatting or editing needed\n'
                    '✅ You focus on learning, we handle the rest'
                ).classes('text-sm mb-4 whitespace-pre-line')

                ui.label('Fast. Accurate. Reliable.').classes('text-sm italic text-gray-700 mb-4')

                ui.button('Get Started 🚀', on_click=welcome_popup.close).classes(
                    'bg-blue-600 text-white hover:bg-blue-700 rounded-md')

        # To show loading and processing animation while generating notes
        with ui.row().classes('w-full justify-center items-center'):


            spinner = ui.spinner(size='md').classes('text-emerald-600 mt-2')
            spinner.visible = False



        # Download Button at the end to download Notes
        download_button = ui.button('Download Notes').props('icon=download').classes(
            'w-full mt-3 bg-emerald-500 text-white text-sm font-medium rounded-md hover:bg-emerald-600'
        )

        #Hiden at first and shown when notes are ready
        download_button.visible = False


        # Start button fot starting notes generation

        generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).classes(
        'w-full mt-4 bg-emerald-500 text-white text-sm font-semibold rounded-md shadow-md hover:bg-emerald-600'
    )

        reset_button = ui.button('🔄 Upload Another File').classes(
            'w-full mt-2 bg-gray-200 text-gray-800 text-sm font-semibold rounded-md shadow-sm hover:bg-gray-300'
        )

        reset_button.visible = False  # Hide it at first

        reset_button.on('click', reset_app)

        # Feedback Section (hidden initially)
        feedback_label = ui.label('✍️ Share your thoughts about NotesCraft').classes(
            'text-base font-semibold text-gray-800 mt-6'
        )
        feedback_input = ui.textarea(label='Your Feedback', placeholder='What can we improve?').classes('w-full')
        submit_feedback_button = ui.button('Submit Feedback', icon='send').classes(
            'bg-blue-600 text-white mt-2 hover:bg-blue-700'
        )

        submit_feedback_button.on('click', submit_feedback)

        # Hide these initially
        feedback_label.visible = False
        feedback_input.visible = False
        submit_feedback_button.visible = False



with ui.footer().classes('w-full flex flex-col items-center justify-center py-4 bg-gray-50'):
    ui.label('⚡ NotesCraft AI is just getting started!') \
        .classes('text-base font-semibold text-indigo-900 text-center')

    ui.label('This early version may not be perfect yet — but we’re improving it every day!') \
        .classes('text-sm text-gray-700 text-center px-6')



# To load the directory which has all the animation files

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

ui.timer(2.5, welcome_popup.open, once=True)

# To start the Web UI
ui.run()
