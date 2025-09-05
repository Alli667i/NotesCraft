import google.generativeai as genai
import requests
from dotenv import load_dotenv
import os
from Instructions_for_Notes_genearation import for_detail_notes
import re
import json
import logging
import traceback
from datetime import datetime

load_dotenv()

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notes_generation_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class NotesGenerationError:
    """Centralized error handling for notes generation"""

    @staticmethod
    def log_debug_error(error_type: str, error_details: str, context: str = "", additional_data: dict = None):
        """Log detailed errors for developer debugging"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_details": error_details,
            "context": context,
            "additional_data": additional_data or {},
            "traceback": traceback.format_exc()
        }

        logger.error(f"NOTES GENERATION ERROR: {error_type} | {error_details} | Context: {context}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Send to external error reporting
        try:
            requests.post(
                'https://script.google.com/macros/s/AKfycbz6Gbht0iZ4tW7lp48x3hDYCvYIDGZbOYdwnpbmyHSQjxsdZ0D0zsx7ZU84eN9n0g2T9w/exec',
                json={"component": "notes_generation", **error_info},
                timeout=10
            )
        except Exception as e:
            logger.error(f"Failed to send error report: {e}")

    @staticmethod
    def check_api_errors(error_message: str) -> str:
        """Identify specific API error types"""
        error_lower = error_message.lower()

        if any(keyword in error_lower for keyword in ['api key', 'invalid key', 'authentication failed']):
            return "API_KEY_ERROR"
        elif any(keyword in error_lower for keyword in ['quota exceeded', 'rate limit', 'too many requests']):
            return "API_QUOTA_ERROR"
        elif any(keyword in error_lower for keyword in ['network', 'connection', 'timeout', 'unreachable']):
            return "NETWORK_ERROR"
        elif any(keyword in error_lower for keyword in ['model not found', 'permission denied']):
            return "API_PERMISSION_ERROR"
        else:
            return "API_UNKNOWN_ERROR"


def safe_get_text(response):
    """Extract text from Gemini response with enhanced error handling"""
    try:
        if not response:
            logger.warning("No response object received")
            return None

        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    text_content = "".join([getattr(p, "text", "") for p in candidate.content.parts])
                    logger.debug(f"Extracted text length: {len(text_content)}")
                    return text_content

        logger.warning("No valid text content found in response")
        return None

    except Exception as e:
        NotesGenerationError.log_debug_error("TEXT_EXTRACTION_ERROR", str(e), "Extracting text from Gemini response")
        return None


def validate_and_fix_json(ai_output: str):
    """
    Validates and fixes AI JSON output with enhanced error handling
    """
    try:
        logger.info(f"Validating JSON output (length: {len(ai_output)})")

        if not ai_output or ai_output.strip() == "":
            NotesGenerationError.log_debug_error("EMPTY_JSON_OUTPUT", "AI returned empty output", "JSON validation")
            return {"error": "Empty AI output", "original_output": ai_output}

        # Step 1: Try parsing directly
        try:
            parsed = json.loads(ai_output)
            logger.info("JSON parsed successfully on first attempt")

            # Ensure it's always a list of objects
            if isinstance(parsed, dict):
                return [parsed]
            elif isinstance(parsed, list):
                return parsed
            else:
                NotesGenerationError.log_debug_error("INVALID_JSON_TYPE",
                                                     f"Parsed JSON is not dict or list: {type(parsed)}",
                                                     "JSON validation")
                return {"error": "Invalid JSON structure", "original_output": ai_output}

        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parsing failed: {e}")
            # Continue to cleanup and regex repair

        # Step 2: Cleanup obvious issues
        cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)
        cleaned = cleaned.strip()

        logger.debug(f"Cleaned JSON (length: {len(cleaned)})")

        # Step 3: Try parsing cleaned version
        try:
            parsed = json.loads(cleaned)
            logger.info("JSON parsed successfully after cleanup")

            if isinstance(parsed, dict):
                return [parsed]
            elif isinstance(parsed, list):
                return parsed

        except json.JSONDecodeError:
            logger.warning("JSON parsing failed even after cleanup, trying regex repair")

        # Step 4: Regex to capture "type" and "text" pairs
        pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
        matches = re.findall(pattern, cleaned)

        if not matches:
            NotesGenerationError.log_debug_error("NO_VALID_JSON_OBJECTS", "No valid type/text pairs found",
                                                 "JSON validation", {"output_sample": ai_output[:500]})
            return {
                "error": "No valid objects found. AI output too malformed.",
                "original_output": ai_output
            }

        # Step 5: Build list of dicts
        result = []
        for typ, text in matches:
            if typ.strip() and text.strip():  # Only add non-empty entries
                result.append({"type": typ.strip(), "text": text.strip()})

        logger.info(f"Successfully extracted {len(result)} objects using regex repair")
        return result

    except Exception as e:
        NotesGenerationError.log_debug_error("JSON_VALIDATION_CRITICAL_ERROR", str(e), "JSON validation",
                                             {"output_sample": ai_output[:500] if ai_output else ""})
        return {
            "error": f"Critical JSON validation error: {str(e)}",
            "original_output": ai_output
        }


def clean_raw_json(raw_data):
    """Clean raw JSON response from LLM"""
    try:
        if not raw_data:
            return ""

        cleaned = raw_data.replace("```json", '').replace("```", '').replace("'", "").replace('[', '').replace(']', '')
        logger.debug(f"Cleaned raw JSON: {cleaned[:200]}...")
        return cleaned

    except Exception as e:
        NotesGenerationError.log_debug_error("JSON_CLEANING_ERROR", str(e), "Cleaning raw JSON")
        return raw_data


def generate_notes_from_content(book_text):
    """
    Generate notes from extracted content with comprehensive error handling
    """
    try:
        logger.info("Starting notes generation process")

        # Check if API key is available
        if not GOOGLE_API_KEY:
            NotesGenerationError.log_debug_error("API_KEY_MISSING", "GOOGLE_API_KEY environment variable not set",
                                                 "Initialization")
            return "API_KEY_ERROR: Missing API key configuration"

        # Validate input
        if not book_text:
            NotesGenerationError.log_debug_error("EMPTY_INPUT", "No content provided for notes generation",
                                                 "Input validation")
            return "INPUT_ERROR: No content provided"

        if not isinstance(book_text, dict):
            NotesGenerationError.log_debug_error("INVALID_INPUT_TYPE", f"Expected dict, got {type(book_text)}",
                                                 "Input validation")
            return "INPUT_ERROR: Invalid content format"

        logger.info(f"Processing {len(book_text)} content sections")

        try:
            genai.configure(api_key=GOOGLE_API_KEY)

            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=for_detail_notes
            )
            logger.info("Gemini model initialized successfully")

        except Exception as e:
            error_type = NotesGenerationError.check_api_errors(str(e))
            NotesGenerationError.log_debug_error(error_type, str(e), "Model initialization")
            return f"{error_type}: Failed to initialize AI model"

        collect_response = []
        cleaned_response = []
        total_tokens_used = 0
        total_input_tokens_used = 0
        total_output_tokens_used = 0

        # Process each content section
        for number, (topic, content) in enumerate(book_text.items(), start=1):
            try:
                logger.info(f"Processing section {number}/{len(book_text)}: {topic[:50]}...")

                if not content or content.strip() == "":
                    logger.warning(f"Skipping empty content for topic: {topic}")
                    continue

                response = model.generate_content(f"{topic} {content}")

                if not response:
                    NotesGenerationError.log_debug_error("EMPTY_API_RESPONSE", f"No response for section {number}",
                                                         f"Processing section {number}")
                    continue

                response_validated = safe_get_text(response)

                if not response_validated:
                    NotesGenerationError.log_debug_error("EMPTY_TEXT_EXTRACTION",
                                                         f"No text extracted for section {number}",
                                                         f"Processing section {number}")
                    continue

                collect_response.append(response_validated)

                # Track token usage
                if hasattr(response, 'usage_metadata'):
                    input_tokens = response.usage_metadata.prompt_token_count
                    output_tokens = response.usage_metadata.candidates_token_count
                    total_tokens = response.usage_metadata.total_token_count

                    logger.info(
                        f"Section {number} tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")

                    total_input_tokens_used += input_tokens
                    total_output_tokens_used += output_tokens
                    total_tokens_used += total_tokens

            except Exception as e:
                error_type = NotesGenerationError.check_api_errors(str(e))
                NotesGenerationError.log_debug_error(error_type, str(e), f"Processing section {number}: {topic}")

                # For critical API errors, stop processing
                if error_type in ["API_KEY_ERROR", "API_PERMISSION_ERROR"]:
                    return f"{error_type}: Critical API error during processing"

                # For other errors, continue with next section
                logger.warning(f"Skipping section {number} due to error: {e}")
                continue

        if not collect_response:
            NotesGenerationError.log_debug_error("NO_VALID_RESPONSES", "No valid responses generated from any section",
                                                 "Response collection")
            return "PROCESSING_ERROR: No content could be processed"

        logger.info(f"Successfully processed {len(collect_response)} sections")

        # Clean and combine responses
        try:
            for each in collect_response:
                cleaned = clean_raw_json(each)
                if cleaned:  # Only add non-empty cleaned responses
                    cleaned_response.append(cleaned)

            if not cleaned_response:
                NotesGenerationError.log_debug_error("NO_CLEANED_RESPONSES", "All responses were empty after cleaning",
                                                     "Response cleaning")
                return "PROCESSING_ERROR: No valid content after cleaning"

            # Combine all JSON responses
            connect_all_json = ",".join(cleaned_response)
            full_json_array = "[" + connect_all_json + "]"

            logger.info(
                f"Token usage summary - Total: {total_tokens_used}, Input: {total_input_tokens_used}, Output: {total_output_tokens_used}")
            logger.debug(f"Generated raw notes (length: {len(full_json_array)})")

            # Validate and fix JSON
            final_json_array = validate_and_fix_json(full_json_array)

            if isinstance(final_json_array, dict) and "error" in final_json_array:
                NotesGenerationError.log_debug_error("JSON_VALIDATION_FAILED", final_json_array["error"],
                                                     "Final JSON validation")
                return "PROCESSING_ERROR: Generated content format is invalid"

            # Convert to final format
            json_str = json.dumps(final_json_array)
            generated_json_for_word = json.loads(json_str)

            logger.info(f"Notes generation completed successfully with {len(generated_json_for_word)} note sections")
            return generated_json_for_word

        except Exception as e:
            NotesGenerationError.log_debug_error("RESPONSE_PROCESSING_ERROR", str(e), "Processing collected responses")
            return "PROCESSING_ERROR: Failed to process generated content"

    except Exception as e:
        NotesGenerationError.log_debug_error("CRITICAL_GENERATION_ERROR", str(e), "Notes generation main function")
        return "CRITICAL_ERROR: Unexpected error during notes generation"