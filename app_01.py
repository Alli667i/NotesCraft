import asyncio
import base64
import mimetypes
import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
import secrets
import requests
from nicegui import ui, app, background_tasks, run, Client
from process_content_to_notes_base import generate_notes_from_content
from process_pdf_to_Json import send_msg_to_ai
from process_to_word_02 import generate_word_file

app.add_static_files('/assets', os.path.join(os.path.dirname(__file__), 'assets'))

@ui.page('/')
def main_page():
    # To add a favicon for the web app
    ui.add_head_html('<link rel="icon" href="assets/favicon.ico">')


    session = app.storage.user
    session.uploaded_file_path = None
    session.uploaded_file_name = "Notes"

    welcome_popup = ui.dialog()

# Used to upload files to send to AI
    def handle_upload(e):

        session.uploaded_file_name = e.name

        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:

            temp_file.write(e.content.read())

            session.uploaded_file_path = Path(temp_file.name)

        ui.notify("File successfully Uploaded!")


    async def process_with_ai():
        # Check if file is uploaded successfully or not
        if not session.uploaded_file_path or not session.uploaded_file_path.exists():

            ui.notify(message='Please Upload a File', type='warning')

            return

        async def background_job():

            with card:

                # After successful file upload extract content from document

                # Hide the start button after starting
                generate_button.visible = False
                # Show loading bar while processing
                spinner.visible = True
                # Show status of what's processing
                status_label.text = "📄 Extracting Content from the document"
                # Update on UI
                ui.update()

            try:
                extracted_json = await run.io_bound(send_msg_to_ai, session.uploaded_file_path)

                # If text extraction fails then inform user

                if not extracted_json:

                    with card:

                        ui.notify("Text extraction failed. Try again or upload another file.", type='negative')

                        status_label.text = ""

                        error_label.text = "⚠️ We couldn't extract text from your PDF. Please try again or use a different file."

                        spinner.visible = False


                        generate_button.visible = False

                        try_again_button.visible = True

                        ui.update()

                    return


                #if extraction successful then start generating notes from the content
                with card:

                    status_label.text = "🛠 Generating Notes "

                    ui.update()

                notes_generated = await run.io_bound(generate_notes_from_content, extracted_json)

                # After successful generating notes generate word file of it
                with card:

                    status_label.text = "📄 Generating Word File"

                    ui.update()

                # make name for the Word file
                unique_name = f"{session.uploaded_file_name}_{uuid.uuid4().hex[:6]}.docx"


                file_generated = await run.io_bound(generate_word_file, notes_generated, file_name=unique_name.replace(' ', '_'))

                # Process the generated Word document to make it download able for users
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

                # Show download button after everything is done
                with card:

                    download_button.on('click', trigger_download)

                    status_label.text = "📕 Your Notes are Ready!"

                    # Hide the loading bar
                    spinner.visible = False

                    download_button.visible = True

                    # SHow the input area to get feedback
                    feedback_label.visible = True

                    feedback_input.visible = True

                    submit_feedback_button.visible = True

                    # Show the reset button to reset everything to start over for a new file
                    reset_button.visible = True

                    ui.update()

            # If notes generation fails then inform user
            except Exception as e:

                with card:

                    ui.notify("❌ Something went wrong while generating your notes. Please try again.", type="negative")


                    report_error(str(e))

                    status_label.text = ""

                    error_label.text = "⚠️ Something went wrong. We're working to fix it. Please try again."

                    spinner.visible = False

                    try_again_button.visible=True

                    ui.update()

        background_tasks.create(background_job())




    def report_error(Error):

            if Error:
                payload = {"Error": Error}

                try:
                    requests.post(
                        'https://script.google.com/macros/s/AKfycbz6Gbht0iZ4tW7lp48x3hDYCvYIDGZbOYdwnpbmyHSQjxsdZ0D0zsx7ZU84eN9n0g2T9w/exec',
                        json=payload
                    )
                    print("Feedback Sent!")

                except Exception as e:
                    print(f"Feedback Failed!:{e}")






# Function to rest and clear everything from the UI
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

        error_label.text=""

        try_again_button.visible = False
        upload_component.reset()

        ui.notify("Ready for another file!")



# Function to send feedback of users to developers

    def submit_feedback():
        feedback = feedback_input.value.strip()
        if not feedback:
            ui.notify("Please write something before submitting!", type="warning")
            return

        ui.notify("✉️ Sending your feedback...")

        async def send_async():
            try:
                await asyncio.to_thread(
                    requests.post,
                    'https://script.google.com/macros/s/AKfycbx…/exec',
                    json={"Feedback": feedback}
                )
                for client in Client.instances.values():
                    if not client.has_socket_connection:
                        continue
                    with client:
                        ui.notify("✅ Feedback sent!")
                        feedback_input.value = ""
            except Exception as e:
                for client in Client.instances.values():
                    if not client.has_socket_connection:
                        continue
                    with client:
                        ui.notify(f"❌ Feedback failed: {e}", type="negative")

        background_tasks.create(send_async())






    # MAIN WEB UI


    with ui.column().classes('items-center w-full p-4 text-sm'):

        with ui.row().classes('items-center justify-center gap-4'):

            # Show main Title
            ui.label('NotesCraft AI – Powered by Intelligence, Built for Learners') \
                .classes('text-2xl md:text-4xl font-bold text-emerald-800 text-center')

        # Show subtitle
        ui.label('Transform your PDFs into professional study notes using the power of AI.') \
            .classes('text-base md:text-lg text-gray-600 text-center mb-6 px-4')

        # Show file upload area
        with ui.card().classes('w-full max-w-md p-4 bg-white shadow rounded-lg border border-gray-200') as card:

            upload_component = ui.upload(
                label='📄 Upload PDF or Word File',
                auto_upload=True,
                multiple=False,
                on_upload=handle_upload
            ).classes('w-full h-40 border-2 border-dashed border-emerald-300 rounded-xl text-emerald-600 bg-emerald-50 text-sm flex items-center justify-center')


            status_label = ui.label('').classes('text-gray-800 mt-3 text-base')


            error_label = ui.label('').classes(
                'mt-3 text-base text-rose-500 font-semibold'
            )


            # Area where loading spinner will be shown
            with ui.row().classes('w-full justify-center items-center'):
                spinner = ui.spinner(size='md').classes('text-emerald-600 mt-2')
                spinner.visible = False

            # Download button designed and area designated on UI
            download_button = ui.button('Download Notes').props('icon=download').classes(
                'w-full mt-3 bg-emerald-500 text-white text-sm font-medium rounded-md hover:bg-emerald-600'
            )
            download_button.visible = False


            # Generate(Start) button designed and area designated on UI

            generate_button = ui.button('🚀 Generate Notes', on_click=process_with_ai).classes(
                'w-full mt-4 bg-emerald-500 text-white text-sm font-semibold rounded-md shadow-md hover:bg-emerald-600'
            )

            # Reset button designed and area designated on UI

            reset_button = ui.button('🔄 Upload Another File', on_click=reset_app).classes(
                'w-full mt-2 bg-gray-200 text-gray-800 text-sm font-semibold rounded-md shadow-sm hover:bg-gray-300'
            )

            reset_button.visible = False


            try_again_button = ui.button('🔄 Upload Again! ', on_click=reset_app).classes(
                'w-full mt-2 bg-gray-200 text-gray-800 text-sm font-semibold rounded-md shadow-sm hover:bg-gray-300'
            )

            try_again_button.visible = False

            # Feedback button designed and area designated on UI

            feedback_label = ui.label('✍️ Share your thoughts about NotesCraft').classes(
                'text-base font-semibold text-gray-800 mt-6')

            feedback_input = ui.textarea(label='Your Feedback', placeholder='What can we improve?').classes('w-full')


            submit_feedback_button = ui.button('Submit Feedback', icon='send', on_click=submit_feedback).classes(
                'bg-blue-600 text-white mt-2 hover:bg-blue-700')

            feedback_label.visible = False
            feedback_input.visible = False
            submit_feedback_button.visible = False

           # Welcome popup to aware user how to use the app
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
    title='NotesCraft AI – Smart Notes Maker',

)


