import os
import json
# import google ai  library to access gemini
from google import genai
# import types library from Google genai to work with different files then text
from google.genai import types
# import dotenv library to load api key
from dotenv import load_dotenv
# import the system instructions for AI
from Instructions_for_extraction import instructions

# Load the .env file to get API key
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



# This func removes the extra spaces and elements from the json response created by AI
def clean_raw_json(ai_response):
    return ai_response.replace("```json", "").replace("```", "").strip()


# This func fix the json created by AI for further use
def finalize_json(json_string):

    try:
        # Parse the JSON string into a Python object
        parsed_data = json.loads(json_string)

        # Convert back to a nicely formatted JSON string for display
        formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)

        return formatted_json

    except json.JSONDecodeError as e:

        return f"JSON parsing error: {str(e)}\nRaw response: {json_string[:500]}..."




# This func takes the uploaded file and instruction from user and extract the content from it as per instructions and return it in the form of Json
def send_msg_to_ai(uploaded_file,instructions_by_user= "Extract everything as per instructions"):

    try:

        client = genai.Client(api_key=GOOGLE_API_KEY)

        response = client.models.generate_content(

            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=instructions

            ),
            contents=[
                types.Part.from_bytes(
                    data=uploaded_file.read_bytes(),
                    mime_type="application/pdf"

                ),

                instructions_by_user
            ]

        )

        # Clean and format the JSON
        cleaned = clean_raw_json(response.text)

        formatted_result = finalize_json(cleaned)


        return formatted_result

    except Exception as Error:

        print(f"Error OCCURED : {str(Error)}")


