import os
import time
import threading

from nicegui import ui , app
from pathlib import Path
from tempfile import NamedTemporaryFile
from process_content_to_notes_02 import generate_notes_from_content
from process_to_word_02 import generate_word_file
from dotenv import load_dotenv
from process_pdf_to_Json import send_msg_to_ai

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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



# Initially file is none as notjing is uploaded
uploaded_file_path = None

def handle_upload(e):

    # Global variable to get the file path for any other function
    global uploaded_file_path

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
        loading_animation.visible = True

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
                notes_generated = generate_notes_from_content(instruction_input.value.strip(), extracted_json)

                # After successfully generating notes passing it to func to make Word Document of it

                status_label.text = "📄 Generating Word File"

                # Updating Changes
                ui.update()

                # Generating Word File
                file_generated = generate_word_file(notes_generated, file_name="Ch_01")

                status_label.text = "📕 Your Notes are Ready!"

                # Showing the download to user to Download the Ready Notes

                download_button.on('click', lambda: ui.download(file_generated))

                download_button.visible = True

            except Exception as e:

                # If notes generation fails then notify user

                ui.notify(f"❌ Error while generating Notes: {e}", type='negative')

        else:
            # If content Extraction fails then
            ui.notify("❌ Failed to extract content.", type='negative')

        ui.update()

    # Run this operation in a seperate thread
    threading.Thread(target=background_task).start()


# Design of the Web UI

with ui.column().classes('items-center w-full p-4 text-sm'):

    ui.label('📘 NotesCraft AI – Smart Notes Maker').classes(
        'text-lg font-semibold text-emerald-700 mb-3'
    )

    with ui.card().classes('w-full max-w-md p-4 bg-white shadow rounded-lg border border-gray-200'):

        # To Show an Upload file Area for user to upload files
        ui.upload(

            label='📄 Upload PDF or Word File',
            auto_upload=True,
            multiple=False,
            on_upload=handle_upload

        ).classes('w-full h-28 border-2 border-dashed border-emerald-300 rounded-md text-emerald-600 bg-emerald-50 text-sm')


        # An input area where users can give extra instructions for notes generation

        instruction_input = ui.input(

            label='📚 Customize how your notes are made',
        placeholder = 'e.g., Summarize each section, list all important terms, focus on conclusions...'

        ).props('filled').classes('w-full mt-3 text-sm text-gray-800 bg-gray-100 px-2 py-1 rounded-md')


        # Area were all the updates will be shown

        status_label = ui.label('').classes('text-gray-800 mt-3 text-base')

        # To show loading and processing animation while generating notes
        with ui.row().classes('w-full justify-center items-center'):

            loading_animation = ui.html("""
            <lottie-player src="/assets/document-scan.json" background="transparent" speed="1"
                           style="width: 200px; height: 200px;" loop autoplay></lottie-player>
            """)

            # Hide at first and shown when notes generation is started
            loading_animation.visible = False

        # spinner = ui.spinner(size='md').classes('text-emerald-600 mt-2')
        # spinner.visible = False



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

# To load the directory which has all the animation files

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# To start the Web UI
ui.run()
