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
from Instructions_for_Notes_genearation import for_detail_notes,for_summarize_notes

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

note_options = {
    "📝  In-Depth Notes": for_detail_notes,
    "📌 Quick Summary": for_summarize_notes

}

# Initially file is none as nothing is uploaded
uploaded_file_path = None
original_filename = None


def process_with_ai():
    # Check if file is uploaded or not
    if not uploaded_file_path or not uploaded_file_path.exists():
        ui.notify(message='Please Upload a File', type='warning')
        return

    def background_task():

        status_label.visible = True

        # When the notes generation will start it will hide the Start button
        generate_button.visible = False

        # For showing loading animation
        text_extraction_animation.visible = True

        # Informing user about what's happening
        status_message.text = "Extracting Content from the document"

        # Updating these changes on UI
        ui.update()

        # Sending the uploaded file to AI for text Extraction
        extracted_json = send_msg_to_ai(uploaded_file_path)

        # If content is successfully extracted then
        if extracted_json:

            # Inform User for successful extraction
            status_message.text = "Content Extracted Successfully"

            print(extracted_json)
            # Update changes on UI

            ui.update()

            # A small delay for smoothness
            time.sleep(3)

            try:

                # Hide the text extraction animation

                text_extraction_animation.visible = False

                # Show the notes generation animation

                notes_generation_animation.visible = True

                # Generate Notes from the extracted content and inform User

                status_message.text = "Generating Notes  "

                ui.update()

                # Send content to AI to Generate Notes from it

                instruction = note_options[selected_prompt.value]

                notes_generated = generate_notes_from_content(instruction, extracted_json)

                # After successfully generating notes passing it to func to make Word Document of it
                print(notes_generated)

                # Hide the notes generating animation

                notes_generation_animation.visible = False


                # Show the Word File making animation

                word_file_generation_animation.visible = True

                status_message.text = "📄 Generating Word File"

                # Updating Changes
                ui.update()

                # Generating Word File
                file_generated = generate_word_file(notes_generated, file_name="Ch_01")

                time.sleep(3)

                status_message.text = "📕 Your Notes are Ready!"

                # Showing the download to user to Download the Ready Notes



                download_button.on('click', lambda: ui.download(file_generated))

                word_file_generation_animation.visible = False

                download_button.visible = True

                time.sleep(2)


                reset_button.visible= True

            except Exception as e:

                # If notes generation fails then notify user

                ui.notify(f"❌ Error while generating Notes: {e}", type='negative')

        else:
            # If content Extraction fails then
            ui.notify("❌ Failed to extract content.", type='negative')

        ui.update()

    # Run this operation in a separate thread
    threading.Thread(target=background_task).start()



def reset_all():
    global uploaded_file_path

    uploaded_file_path = None

    # Reset UI elements
    status_message.text = ''
    download_button.visible = False
    generate_button.visible = True
    word_file_generation_animation.visible = False

    # Reset selected option (optional)
    selected_prompt.value = list(note_options.keys())[0]  # default to first option

    render_upload()  # Reset upload UI visually

    reset_button.visible = False
    status_label.visible = False


    ui.notify('Reset successful! You can upload a new file.')
    ui.update()

with ui.column().classes(
    'absolute inset-0 w-full h-full overflow-x-hidden bg-gradient-to-br '
    'from-gray-900 via-gray-950 to-black px-4 sm:px-8 py-8 sm:py-12 text-white font-sans'
):

    # 🚀 App Header
    with ui.column().classes('w-full items-center text-center mb-10'):
        ui.icon('auto_awesome').classes('text-5xl text-cyan-400 mb-2')
        ui.label('NotesCraft AI – Smart Notes Maker').classes(
            'text-4xl sm:text-5xl font-extrabold tracking-tight text-white text-center drop-shadow-md'
        )
        ui.label('Turn your PDFs into structured notes, instantly.').classes(
            'text-lg text-gray-300 mt-2'
        )

    # 📤 Upload Area
    with ui.card().classes(
        'w-full max-w-2xl mx-auto bg-white/10 backdrop-blur-lg border border-white/20 '
        'rounded-3xl shadow-2xl p-6 sm:p-10 text-center'
    ):

        upload_container = ui.column().classes('items-center w-full')

        uploaded_file_label = ui.label().classes('hidden')

        def handle_files(e):
            global uploaded_file_path, original_filename

            original_filename = e.name

            with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(e.content.read())
                uploaded_file_path = Path(temp_file.name)

            upload_container.clear()
            with upload_container:
                with ui.column().classes('items-center'):
                    with ui.card().classes(
                        'bg-white/20 text-white border border-white/30 shadow-md px-5 py-3 rounded-xl '
                        'flex items-center gap-3 mb-4'
                    ):
                        ui.icon("picture_as_pdf").classes("text-red-400 text-3xl")
                        ui.label(original_filename).classes("text-lg font-medium")

                    ui.label("Please confirm this is the file you'd like to upload.").classes(
                        'text-base text-gray-300 mb-1'
                    )
                    ui.label("Processing may take a few seconds.").classes(
                        'text-sm text-gray-500 mb-4'
                    )

                    with ui.row().classes("gap-4 mt-2"):
                        ui.button("✅ Confirm", on_click=confirm_file_upload).classes(
                            'bg-gradient-to-r from-emerald-400 to-cyan-500 text-white px-5 py-2 rounded-xl '
                            'hover:scale-105 hover:shadow-lg transition-all'
                        )
                        ui.button("❌ Cancel", on_click=render_upload).classes(
                            'bg-white/20 text-white border border-gray-500 px-5 py-2 rounded-xl '
                            'hover:bg-white/30 transition-all'
                        )

        def confirm_file_upload():
            upload_container.clear()
            with upload_container:
                with ui.card().classes(
                    'bg-white/10 backdrop-blur border border-white/30 text-white shadow-md '
                    'px-6 py-4 rounded-xl flex items-center justify-center'
                ):
                    ui.icon("picture_as_pdf").classes("text-red-400 text-2xl mr-2")
                    ui.label(original_filename).classes("text-lg font-medium")

            selected_prompt.visible = True
            generate_button.visible = True
            status_label.visible = True

        def render_upload():
            upload_container.clear()

            with upload_container:
                uploader = ui.upload(
                    on_upload=handle_files,
                    auto_upload=True,
                    multiple=False
                ).props('accept=.pdf').classes('hidden')

                with ui.card().classes(
                    'w-full max-w-lg h-44 border-2 border-dashed border-gray-500 bg-white/10 '
                    'hover:bg-white/20 rounded-2xl flex flex-col items-center justify-center '
                    'cursor-pointer transition-all text-white shadow-md'
                ).on('click', lambda: uploader.run_method('pickFiles')):
                    ui.icon('cloud_upload').classes('text-4xl text-cyan-400 mb-2')
                    ui.label('Click to upload your PDF').classes('text-lg font-medium text-white')
                    ui.label('Drag & drop not supported yet').classes('text-sm text-gray-400')

        render_upload()

    # 📚 Dropdown (Initially Hidden)
    selected_prompt = ui.select(
        options=list(note_options.keys()),
        value=list(note_options.keys())[0],
        label='📚 Choose Note Generation Mode'
    ).classes(
        'w-full max-w-md mx-auto mt-6 px-4 py-3 text-sm sm:text-base text-white bg-white/10 '
        'border border-white/30 rounded-full shadow-md backdrop-blur focus:outline-none focus:ring-2 '
        'focus:ring-cyan-400'
    )
    selected_prompt.visible = False

    # 📊 Status Label
    status_label = ui.label('Status:').classes(
        'text-cyan-400 mt-6 text-base sm:text-lg font-semibold text-center'
    )
    status_label.visible = False

    # 🌀 Animation Container
    with ui.column().classes('w-full items-center mt-6'):
        with ui.column().classes('flex flex-row justify-center gap-6'):
            text_extraction_animation = ui.html("""
                <lottie-player src="/assets/document-search.json" background="transparent" speed="1"
                               style="width: 120px; height: 120px;" loop autoplay></lottie-player>
            """)
            notes_generation_animation = ui.html("""
                <lottie-player src="/assets/generate_notes.json" background="transparent" speed="1"
                               style="width: 120px; height: 120px;" loop autoplay></lottie-player>
            """)
            word_file_generation_animation = ui.html("""
                <lottie-player src="/assets/generate_word_file.json" background="transparent" speed="1"
                               style="width: 120px; height: 120px;" loop autoplay></lottie-player>
            """)
            for anim in [text_extraction_animation, notes_generation_animation, word_file_generation_animation]:
                anim.visible = False

        status_message = ui.label('').classes(
            'text-white mt-4 text-center text-base sm:text-lg font-medium'
        )

    # ⬇️ Buttons Section
    generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).classes(
        'w-full max-w-md mx-auto mt-6 px-6 py-3 text-lg font-semibold text-white '
        'bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl shadow-lg '
        'hover:scale-105 hover:shadow-xl transition-all duration-200'
    )
    generate_button.visible = False

    download_button = ui.button('⬇️ Download Notes').props(
        'unelevated rounded color=cyan text-color=white'
    ).classes(
        'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base font-semibold text-white '
        'bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-xl shadow-lg hover:scale-105 '
        'hover:shadow-xl transition-all duration-200 text-center'
    )
    download_button.visible = False

    reset_button = ui.chip('🔄 Start Over', on_click=reset_all).props(
        'unelevated rounded color=white text-color=gray'
    ).classes(
        'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold text-white/90 '
        'bg-white/10 backdrop-blur border border-white/20 rounded-xl shadow-md hover:bg-white/20 '
        'transition-all duration-200 text-center'
    )
    reset_button.visible = False


# 📂 Make assets available
app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# 🚀 Start the app
ui.run()
