import google.generativeai as genai
from dotenv import load_dotenv
import os
from Ins_for_notes_generation import for_detail_notes
import re
import json
# import our new error handler
from error_handler import handle_api_error, handle_generation_error

from logger import log_generation_start, log_generation_complete

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


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


def validate_and_fix_json(ai_output: str):
    """
    Validates and fixes AI JSON output.
    Handles:
    - Proper JSON directly (no regex needed)
    - Broken JSON with stray characters
    - Multi-line text fields
    """

    # Step 1: Try parsing directly
    try:
        parsed = json.loads(ai_output)
        # Ensure it's always a list of objects
        if isinstance(parsed, dict):
            return [parsed]
        elif isinstance(parsed, list):
            return parsed
    except Exception:
        pass  # fall back to regex repair if json.loads fails

    # Step 2: Cleanup obvious junk
    cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)

    # Step 3: Regex to capture "type" and "text"
    pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
    matches = re.findall(pattern, cleaned)

    if not matches:
        return {
            "error": "No valid objects found. AI output too malformed.",
            "original_output": ai_output
        }

    # Step 4: Build list of dicts (no manual escaping!)
    result = []
    for typ, text in matches:
        result.append({"type": typ.strip(), "text": text.strip()})

    return result


def clean_raw_json(raw_data):
    """Clean the raw json response given by the LLM"""
    return raw_data.replace("```json", '').replace("```", '').replace("'", "").replace('[', '').replace(']', '')


def generate_notes_from_content(book_text,session_id=None):
    """
    Generate notes from extracted content.
    Returns generated notes or error dict.
    """

    # Check if we received an error from extraction
    if isinstance(book_text, dict) and "error_type" in book_text:
        return book_text  # Pass through the error

    try:
        # Check API key
        if not GOOGLE_API_KEY:
            error_result = handle_api_error(
                "GOOGLE_API_KEY not found in environment variables",
                "API Configuration"
            )
            return error_result

        genai.configure(api_key=GOOGLE_API_KEY)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=for_detail_notes
        )

        collect_response = []  # Store all LLM responses
        cleaned_response = []  # Store cleaned responses

        total_tokens_used = 0
        total_input_tokens_used = 0
        total_output_tokens_used = 0

        if session_id:
            log_generation_start(session_id,len(book_text))

        # Process each topic and content
        for number, (topic, content) in enumerate(book_text.items(), start=1):
            try:
                response = model.generate_content(f"{topic} {content}")
                response_validated = safe_get_text(response)

                if not response_validated:
                    error_result = handle_generation_error(
                        f"Empty response from AI for topic {number}: {topic}",
                        "Content Generation"
                    )
                    return error_result

                collect_response.append(response_validated)

                # Track token usage
                total_input_tokens_used += response.usage_metadata.prompt_token_count
                total_output_tokens_used += response.usage_metadata.candidates_token_count
                total_tokens_used += response.usage_metadata.total_token_count


            except Exception as e:
                # Handle API errors during generation
                error_msg = str(e).lower()

                if "api key" in error_msg or "authentication" in error_msg:
                    error_result = handle_api_error(str(e), "API Authentication")
                elif "rate limit" in error_msg or "429" in error_msg:
                    error_result = handle_api_error(str(e), "Rate Limiting")
                elif "quota" in error_msg or "limit exceeded" in error_msg:
                    error_result = handle_api_error(str(e), "Quota Exceeded")
                else:
                    error_result = handle_generation_error(
                        f"Error generating content for topic {number}: {str(e)}",
                        "Content Generation"
                    )

                return error_result

        # Clean all responses
        for each in collect_response:
            cleaned = clean_raw_json(each)
            cleaned_response.append(cleaned)

        # Combine all JSON responses
        connect_all_json = ",".join(cleaned_response)
        full_json_array = "[" + connect_all_json + "]"

        print(f"\nTotal Input Tokens Used: {total_input_tokens_used}")
        print(f"\nTotal Output Tokens Used: {total_output_tokens_used}")

        print(f"\nTotal Tokens Used: {total_tokens_used}")

        if session_id:
            log_generation_complete(
                session_id,
                total_input_tokens_used,
                total_output_tokens_used,
                total_tokens_used
            )


        # Validate and fix the JSON
        final_json_array = validate_and_fix_json(full_json_array)

        # Check if validation failed
        if isinstance(final_json_array, dict) and "error" in final_json_array:
            error_result = handle_generation_error(
                f"JSON validation failed: {final_json_array['error']}",
                "Response Validation"
            )
            return error_result

        # Convert to proper format
        try:
            json_str = json.dumps(final_json_array)
            generated_json_for_word = json.loads(json_str)
        except Exception as e:
            error_result = handle_generation_error(
                f"Final JSON processing failed: {str(e)}",
                "JSON Processing"
            )
            return error_result

        print(f"\nFinal Notes Generated: {generated_json_for_word}")

        return generated_json_for_word

    except Exception as e:
        # Catch any unexpected errors
        error_result = handle_generation_error(
            f"Unexpected error in generate_notes_from_content: {str(e)}",
            "System Error"
        )

        return error_result