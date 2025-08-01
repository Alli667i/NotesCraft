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


                time.sleep(5)


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

# def confirm_file_upload():
#     upload_container.clear()
#     with upload_container:
#         with ui.card().classes(
#             'w-full max-w-xl p-4 rounded-2xl border border-emerald-300 bg-emerald-50 '
#             'text-center shadow-md flex items-center justify-center space-x-4'
#         ):
#             # Your PNG icon
#             ui.image("/assets/Doc_pic.png").classes("w-10 h-10")  # Adjust size with w- and h- classes
#
#             # File name label
#             ui.label(original_filename).classes(
#                 'text-xl font-semibold text-emerald-800'
#             )
#
#             ui.notify("File Uploaded Successfully")


def confirm_file_upload():
    upload_container.clear()
    with upload_container:
        with ui.card().classes(
            'w-full max-w-xl p-6 rounded-2xl bg-gradient-to-br from-emerald-100 to-white '
            'shadow-xl border border-emerald-300 flex items-center space-x-4'
        ):
            # PNG icon
            ui.image('/assets/Doc_pic.png').classes("w-10 h-10")

            # File info (filename + label)
            with ui.column().classes('items-start'):
                ui.label("File Uploaded").classes(
                    'text-sm font-medium text-emerald-600'
                )
                ui.label(original_filename).classes(
                    'text-lg font-semibold text-emerald-900 truncate max-w-xs'
                )

            ui.notify("✅ File Uploaded Successfully!")


with ui.column().classes(
    'absolute inset-0 w-full h-full overflow-x-hidden bg-gradient-to-tr '
    'from-emerald-200 via-white to-indigo-100 px-3 sm:px-6 py-6 sm:py-12 text-base sm:text-lg'):

    # 💡 Heading
    with ui.column().classes('w-full items-center'):
        ui.label('📘 NotesCraft AI – Smart Notes Maker').classes(
            'text-3xl sm:text-5xl font-bold text-emerald-700 mb-8 text-center tracking-wide drop-shadow-md'
        )

    # 📦 Main Content Card
    with ui.card().classes(
        'w-full max-w-2xl sm:max-w-3xl mx-auto p-4 sm:p-8 bg-white/90 backdrop-blur-md shadow-2xl '
        'rounded-2xl border border-gray-300'
    ):

        upload_container = ui.column().classes('w-full items-center')

        uploaded_file_label = ui.label().classes('hidden')  # placeholder for label access


        def handle_files(e):

            global uploaded_file_path, original_filename

            original_filename = e.name  # Store the real uploaded file name

            with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(e.content.read())
                uploaded_file_path = Path(temp_file.name)

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
                            ui.label(original_filename).classes("text-lg font-medium text-gray-800")

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
                # hidden uploader
                uploader = ui.upload(
                    on_upload=handle_files,
                    auto_upload=True,
                    multiple=False
                ).props('accept=.pdf').classes('hidden')

                # styled clickable area
                with ui.card().classes(
                        'w-full max-w-xl h-48 border-2 border-dashed border-gray-300 bg-white/80 '
                        'hover:bg-emerald-50 rounded-2xl flex flex-col items-center justify-center '
                        'cursor-pointer transition-all text-center shadow-md'
                ).on('click', lambda: uploader.run_method('pickFiles')):
                    ui.icon('cloud_upload').classes('text-5xl text-emerald-600')
                    ui.label('Click to upload your PDF').classes('text-lg font-medium text-gray-700')
                    ui.label('or drag and drop here (not active yet)').classes('text-sm text-gray-500')



        # 🚀 Initial render

        render_upload()

        # 📝 Dropdown

        selected_prompt = ui.select(
            options=list(note_options.keys()),
            value=list(note_options.keys())[0],
            label='📚 Choose how to generate your notes'
        ).classes(
            'w-full max-w-md mx-auto mt-5 px-4 py-2 text-sm sm:text-base bg-white border border-gray-300 rounded-full shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400'
        )

        # 🟡 Status Label

        status_label = ui.label('Status:').classes(
            'text-indigo-700 mt-4 text-base sm:text-lg font-semibold'
        )
        status_label.visible = False


        # 🎞️ Animations

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

        # ⬇️ Download Notes Chip

        download_button = ui.button('⬇️ Download Notes',).props(
            'unelevated rounded color=indigo text-color=white'
        ).classes(
            'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
        )

        download_button.visible = False


       # Generate Notes Button

        generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).props(
            'unelevated rounded color=indigo text-color=white'
        ).classes(
            'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
        )


        # 🔄 Reset Chip

        reset_button = ui.button('🔄 Start Over', on_click=reset_all).props(
            'unelevated rounded color=indigo text-color=white'
        ).classes(
            'w-full max-w-md mx-auto mt-6 px-6 py-3 text-base sm:text-lg font-semibold shadow-sm transition-all duration-200 text-center'
        )

        reset_button.visible = False

# 📂 Make assets available
app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

# 🚀 Start the app
ui.run()
