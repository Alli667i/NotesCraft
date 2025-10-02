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
from Ins_for_extraction import instructions
# import our new error handler
from error_handler import handle_api_error, handle_file_error

from db_logger import log_extraction_start, log_extraction_complete

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
    """Remove Markdown formatting from AI response."""
    if not ai_response:
        return ""
    return ai_response.replace("```json", "").replace("```", "").strip()


def finalize_extracted_content(json_string: str) -> dict | str | None:
    """Parse JSON safely, return dict or error dict."""
    try:
        return json.loads(json_string)

    except json.JSONDecodeError as e:
        # Use error handler for JSON parsing issues
        error_result = handle_file_error(
            f"JSON parsing failed: {str(e)} | Raw response: {json_string[:300]}...",
            "JSON Validation"
        )

        # Report technical error for debugging
        report_error(error_result["technical_error"])



        print(f"Failed Extraction: {json_string}")

        # Return error dict instead of string
        return error_result


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
        # Use error handler for response extraction issues
        error_result = handle_api_error(
            f"Error extracting text from Gemini response: {str(e)}",
            "Response Processing"
        )

        report_error(error_result["technical_error"])


        return None


def send_msg_to_ai(uploaded_file,session_id= None):
    """Send file to Gemini and return structured JSON or error dict."""

    if session_id:
        print(f"ID: {session_id}")

        log_extraction_start(session_id)

    try:
        # Check API key first
        if not GOOGLE_API_KEY:
            error_result = handle_api_error(
                "GOOGLE_API_KEY not found in environment variables",
                "API Configuration"
            )
            report_error(error_result["technical_error"])

            return error_result

        client = genai.Client(api_key=GOOGLE_API_KEY)




        # Try to read file
        try:
            file_data = uploaded_file.read_bytes()
        except Exception as e:
            error_result = handle_file_error(
                f"Could not read uploaded file: {str(e)}",
                "File Reading"
            )
            report_error(error_result["technical_error"])


            return error_result

        # Send to Gemini API
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=instructions),
                contents=[
                    types.Part.from_bytes(
                        data=file_data,
                        mime_type="application/pdf"
                    )
                ]
            )
        except Exception as e:
            # Handle different API errors
            error_msg = str(e).lower()

            if "api key" in error_msg or "authentication" in error_msg:
                error_result = handle_api_error(str(e), "API Authentication")
            elif "rate limit" in error_msg or "429" in error_msg:
                error_result = handle_api_error(str(e), "Rate Limiting")
            elif "quota" in error_msg or "limit exceeded" in error_msg:
                error_result = handle_api_error(str(e), "Quota Exceeded")
            else:
                error_result = handle_api_error(str(e), "API Request")

            report_error(error_result["technical_error"])



            return error_result

        if not response:
            error_result = handle_api_error(
                "No response received from Gemini API",
                "API Response"
            )
            report_error(error_result["technical_error"])


            return error_result

        raw_text = safe_get_text(response)

        # Log token usage
        input_token = response.usage_metadata.prompt_token_count
        output_token = response.usage_metadata.candidates_token_count
        total_token = response.usage_metadata.total_token_count
        #
        # print(f'\nRaw Extracted Text: {raw_text}')
        # print(f'\nInput Token of extraction: {input_token}')
        # print(f'\nOutput Token extraction: {output_token}')
        # print(f'\nTotal Token of extraction: {total_token}')

        if session_id:
            print(f"ID: {session_id}")
            log_extraction_complete(session_id,input_token,output_token,total_token)


        if not raw_text:
            error_result = handle_api_error(
                "No text extracted from Gemini response - response was empty",
                "Text Extraction"
            )
            # report_error(error_result["technical_error"])



            return error_result

        cleaned = clean_raw_response_from_ai(raw_text)

        # print(f"Extraction Finalized: {cleaned}")
        # print("------------------------------------------------------------------------")

        parsed = finalize_extracted_content(cleaned)

        # Check if parsing returned an error dict
        if isinstance(parsed, dict) and "error_type" in parsed:
            return parsed  # Return error dict
        elif parsed is None:
            error_result = handle_file_error(
                "Content extraction returned None after processing",
                "Content Processing"
            )
            report_error(error_result["technical_error"])
            return error_result

        return parsed  # Success, return dictionary

    except Exception as e:
        # Catch any unexpected errors
        error_result = handle_api_error(
            f"Unexpected error in send_msg_to_ai: {str(e)}",
            "System Error"
        )

        report_error(error_result["technical_error"])
        return error_result
