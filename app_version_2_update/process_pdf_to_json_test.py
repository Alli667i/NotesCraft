import os
import json

import requests
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


def report_error(Error):

    if Error:

        try:
            requests.post(
                'https://script.google.com/macros/s/AKfycbz6Gbht0iZ4tW7lp48x3hDYCvYIDGZbOYdwnpbmyHSQjxsdZ0D0zsx7ZU84eN9n0g2T9w/exec',
                json={"Error": Error},
            )
        except Exception as e:

            print(f"Error reporting failed: {e}")



def clean_raw_response_from_ai(ai_response: str) -> str:
    """Remove markdown formatting from AI response."""
    if not ai_response:
        return ""
    return ai_response.replace("```json", "").replace("```", "").strip()


def finalize_extracted_content(json_string: str) -> dict | str | None:
    """Parse JSON safely, log if it fails, return dict or error string."""
    try:
        return json.loads(json_string)

    except json.JSONDecodeError as e:

        error_msg = f"⚠️ JSON parsing error: {str(e)} | Raw response (first 300 chars): {json_string[:300]}..."

        report_error(error_msg)

        return "Extraction Failed: Incomplete or invalid JSON from AI"


def safe_get_text(response):
    """Extract plain text from Gemini response object."""
    try:
        if not response:
            return None
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    return "".join([getattr(p, "text", "") for p in candidate.content.parts])

        return None

    except Exception as e:

        error_msg = f"⚠️ Error extracting text from Gemini response: {e}"

        report_error(error_msg)

        return None


def send_msg_to_ai(uploaded_file, instructions_by_user="Extract everything as per instructions"):

    """Send file to Gemini and return structured JSON or error string."""

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)

        # ✅ Detect MIME type dynamically
        mime_type = (
            "application/pdf"
            if uploaded_file.suffix.lower() == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=instructions),
            contents=[
                types.Part.from_bytes(
                    data=uploaded_file.read_bytes(),
                    mime_type=mime_type
                )
            ]
        )

        if not response:
            error_msg = "⚠️ No response received from Gemini API."
            report_error(error_msg)
            return "Extraction Failed: No response from AI"

        raw_text = safe_get_text(response)

        if not raw_text:

            error_msg = "⚠️ No text extracted from Gemini response."

            report_error(error_msg)

            return "Extraction Failed: AI returned empty text"

        cleaned = clean_raw_response_from_ai(raw_text)

        print(f"Content Extracted: {cleaned}")

        print("------------------------------------------------------------------------")

        parsed = finalize_extracted_content(cleaned)

        if parsed is None or isinstance(parsed, str):
            # Already logged inside finalize_extracted_content
            return parsed

        return parsed  # ✅ Success, return dictionary

    except Exception as e:

        error_msg = f"❌ Unexpected error in send_msg_to_ai: {str(e)}"

        report_error(error_msg)

        return "Extraction Failed: Unexpected internal error"
