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



# Clean up raw response received from AI(remove markdown wrappers)

def clean_raw_response_from_ai(ai_response: str) -> str:
    if not ai_response:
        return ""
    return ai_response.replace("```json", "").replace("```", "").strip()


def finalize_extracted_content(json_string: str) -> str:
    try:

        return  json.loads(json_string) # It will conv the json string into a dictionary
        # return json.dumps(parsed_data, indent=2, ensure_ascii=False) # It will conv dictionary into json string

    except json.JSONDecodeError as e:

        return f"⚠️ JSON parsing error: {str(e)}\nRaw response: {json_string[:500]}..."


# Extract text safely from Gemini response
def safe_get_text(response):
    try:
        if not response:
            return None

        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    return "".join([getattr(p, "text", "") for p in candidate.content.parts])
        return None
    except Exception as e:
        print(f"⚠️ Error extracting text: {e}")
        return None


# Send file + instructions to Gemini
def send_msg_to_ai(uploaded_file, instructions_by_user="Extract everything as per instructions and ignore the text in green boxes and diagrams"):
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=instructions),
            contents=[
                types.Part.from_bytes(
                    data=uploaded_file.read_bytes(),
                    mime_type="application/pdf"
                ),
                instructions_by_user
            ]
        )

        # Debugging: check if response is empty
        if not response:
            print("⚠️ No response received from Gemini.")
            return None

        print(f"\nRaw response from AI: {response.text}")

        verify_response = safe_get_text(response)

        if not verify_response:
            print("⚠️ No text extracted from response.")
            return None

        # Clean the response to remove unwanted things and objects from it
        cleaned = clean_raw_response_from_ai(verify_response)

        print(f"\nAI response after cleaning: {cleaned}")

        print(f"\nFinal product : {finalize_extracted_content(cleaned)}")

        return finalize_extracted_content(cleaned) if cleaned else None

    except Exception as e:

        print(f"❌ Error occurred in send_msg_to_ai: {str(e)}")

        return None
