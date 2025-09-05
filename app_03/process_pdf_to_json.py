import os
import json
import requests
import logging
import traceback
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from Instructions_for_extraction import instructions

# Load the .env file to get API key
load_dotenv()

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class ExtractionError:
    """Centralized error handling for text extraction"""

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

        logger.error(f"EXTRACTION ERROR: {error_type} | {error_details} | Context: {context}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Send to external error reporting
        try:
            requests.post(
                'https://script.google.com/macros/s/AKfycbz6Gbht0iZ4tW7lp48x3hDYCvYIDGZbOYdwnpbmyHSQjxsdZ0D0zsx7ZU84eN9n0g2T9w/exec',
                json={"component": "extraction", **error_info},
                timeout=10
            )
        except Exception as e:
            logger.error(f"Failed to send error report: {e}")

    @staticmethod
    def check_api_errors(error_message: str) -> str:
        """Identify specific API error types for user-friendly handling"""
        error_lower = error_message.lower()

        if any(keyword in error_lower for keyword in
               ['api key', 'invalid key', 'authentication failed', 'unauthorized']):
            return "API_KEY_ERROR"
        elif any(keyword in error_lower for keyword in ['quota exceeded', 'rate limit', 'too many requests', 'quota']):
            return "API_QUOTA_ERROR"
        elif any(keyword in error_lower for keyword in ['network', 'connection', 'timeout', 'unreachable', 'dns']):
            return "NETWORK_ERROR"
        elif any(keyword in error_lower for keyword in ['model not found', 'permission denied', 'access denied']):
            return "API_PERMISSION_ERROR"
        elif any(keyword in error_lower for keyword in ['file too large', 'size limit', 'content too long']):
            return "FILE_SIZE_ERROR"
        elif any(
                keyword in error_lower for keyword in ['unsupported format', 'invalid format', 'format not supported']):
            return "FILE_FORMAT_ERROR"
        else:
            return "API_UNKNOWN_ERROR"


def clean_raw_response_from_ai(ai_response: str) -> str:
    """Remove Markdown formatting from AI response with error handling"""
    try:
        if not ai_response:
            logger.warning("Empty AI response received for cleaning")
            return ""

        cleaned = ai_response.replace("```json", "").replace("```", "").strip()
        logger.debug(f"Cleaned response length: {len(cleaned)}")
        return cleaned

    except Exception as e:
        ExtractionError.log_debug_error("RESPONSE_CLEANING_ERROR", str(e), "Cleaning AI response")
        return ai_response  # Return original if cleaning fails


def finalize_extracted_content(json_string: str) -> dict | str | None:
    """Parse JSON safely with comprehensive error handling"""
    try:
        if not json_string or json_string.strip() == "":
            ExtractionError.log_debug_error("EMPTY_JSON_STRING", "Received empty JSON string", "JSON parsing")
            return "Extraction Failed: AI returned empty content"

        logger.debug(f"Attempting to parse JSON (length: {len(json_string)})")

        parsed_data = json.loads(json_string)

        # Validate the structure
        if not isinstance(parsed_data, dict):
            ExtractionError.log_debug_error("INVALID_JSON_STRUCTURE", f"Expected dict, got {type(parsed_data)}",
                                            "JSON structure validation")
            return "Extraction Failed: Invalid content structure from AI"

        if len(parsed_data) == 0:
            ExtractionError.log_debug_error("EMPTY_PARSED_CONTENT", "Parsed JSON is empty", "JSON content validation")
            return "Extraction Failed: No content extracted from document"

        logger.info(f"Successfully parsed JSON with {len(parsed_data)} sections")
        return parsed_data

    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing error: {str(e)} | Raw response sample: {json_string[:300]}..."
        ExtractionError.log_debug_error("JSON_DECODE_ERROR", error_msg, "JSON parsing", {"full_response": json_string})
        return "Extraction Failed: AI response format is invalid"

    except Exception as e:
        ExtractionError.log_debug_error("JSON_PARSING_UNEXPECTED_ERROR", str(e), "JSON parsing",
                                        {"response_sample": json_string[:300] if json_string else ""})
        return "Extraction Failed: Unexpected error processing AI response"


def safe_get_text(response):
    """Extract plain text from Gemini response object with enhanced error handling"""
    try:
        if not response:
            logger.warning("No response object provided")
            return None

        if not hasattr(response, "candidates"):
            ExtractionError.log_debug_error("INVALID_RESPONSE_STRUCTURE", "Response missing candidates attribute",
                                            "Response structure validation")
            return None

        if not response.candidates:
            ExtractionError.log_debug_error("EMPTY_CANDIDATES", "Response has empty candidates list",
                                            "Response validation")
            return None

        for candidate_idx, candidate in enumerate(response.candidates):
            try:
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    text_parts = []
                    for part_idx, part in enumerate(candidate.content.parts):
                        part_text = getattr(part, "text", "")
                        if part_text:
                            text_parts.append(part_text)
                        else:
                            logger.debug(f"Empty text in part {part_idx} of candidate {candidate_idx}")

                    if text_parts:
                        full_text = "".join(text_parts)
                        logger.info(f"Successfully extracted {len(full_text)} characters from response")
                        return full_text

            except Exception as e:
                ExtractionError.log_debug_error("CANDIDATE_PROCESSING_ERROR", str(e),
                                                f"Processing candidate {candidate_idx}")
                continue

        ExtractionError.log_debug_error("NO_VALID_TEXT_FOUND", "No valid text found in any candidate",
                                        "Text extraction")
        return None

    except Exception as e:
        ExtractionError.log_debug_error("TEXT_EXTRACTION_CRITICAL_ERROR", str(e), "Safe text extraction")
        return None


def send_msg_to_ai(uploaded_file, instructions_by_user="Extract everything as per instructions"):
    """
    Send file to Gemini and return structured JSON or error string with comprehensive error handling
    """
    try:
        logger.info(f"Starting extraction for file: {uploaded_file}")

        # Check if API key is available
        if not GOOGLE_API_KEY:
            ExtractionError.log_debug_error("API_KEY_MISSING", "GOOGLE_API_KEY environment variable not set",
                                            "Initialization")
            return "API_KEY_ERROR: Missing API key configuration"

        # Validate file exists and is readable
        if not uploaded_file.exists():
            ExtractionError.log_debug_error("FILE_NOT_FOUND", f"File does not exist: {uploaded_file}",
                                            "File validation")
            return "FILE_ERROR: Uploaded file not found"

        try:
            file_size = uploaded_file.stat().st_size
            logger.info(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

            if file_size == 0:
                ExtractionError.log_debug_error("EMPTY_FILE", f"File is empty: {uploaded_file}", "File validation")
                return "FILE_ERROR: Uploaded file is empty"

        except Exception as e:
            ExtractionError.log_debug_error("FILE_ACCESS_ERROR", str(e), f"Accessing file {uploaded_file}")
            return "FILE_ERROR: Cannot access uploaded file"

        # Detect MIME type
        try:
            suffix = uploaded_file.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix == ".docx":
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                ExtractionError.log_debug_error("UNSUPPORTED_FILE_TYPE", f"Unsupported file extension: {suffix}",
                                                "File type detection")
                return "FILE_FORMAT_ERROR: Unsupported file format"

            logger.info(f"Detected MIME type: {mime_type}")

        except Exception as e:
            ExtractionError.log_debug_error("MIME_TYPE_DETECTION_ERROR", str(e), "MIME type detection")
            return "FILE_ERROR: Cannot determine file type"

        # Initialize Gemini client
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            logger.info("Gemini client initialized successfully")

        except Exception as e:
            error_type = ExtractionError.check_api_errors(str(e))
            ExtractionError.log_debug_error(error_type, str(e), "Client initialization")
            return f"{error_type}: Failed to initialize AI service"

        # Read file content
        try:
            file_content = uploaded_file.read_bytes()
            logger.info(f"Successfully read {len(file_content)} bytes from file")

        except Exception as e:
            ExtractionError.log_debug_error("FILE_READ_ERROR", str(e), f"Reading file {uploaded_file}")
            return "FILE_ERROR: Cannot read uploaded file"

        # Send to Gemini API
        try:
            logger.info("Sending request to Gemini API")

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=instructions),
                contents=[
                    types.Part.from_bytes(
                        data=file_content,
                        mime_type=mime_type
                    )
                ]
            )

            if not response:
                ExtractionError.log_debug_error("EMPTY_API_RESPONSE", "Gemini API returned no response", "API call")
                return "API_ERROR: No response from AI service"

            logger.info("Received response from Gemini API")

        except Exception as e:
            error_type = ExtractionError.check_api_errors(str(e))
            ExtractionError.log_debug_error(error_type, str(e), "Gemini API call")
            return f"{error_type}: AI service error during processing"

        # Extract text from response
        try:
            raw_text = safe_get_text(response)

            if not raw_text:
                ExtractionError.log_debug_error("EMPTY_TEXT_EXTRACTION", "No text extracted from API response",
                                                "Text extraction")
                return "EXTRACTION_ERROR: No content extracted from document"

            # Log token usage if available
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                total_tokens = response.usage_metadata.total_token_count

                logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")

            logger.debug(f"Raw extracted text length: {len(raw_text)}")

        except Exception as e:
            ExtractionError.log_debug_error("TEXT_EXTRACTION_ERROR", str(e), "Extracting text from response")
            return "EXTRACTION_ERROR: Failed to extract text from AI response"

        # Clean and parse response
        try:
            cleaned = clean_raw_response_from_ai(raw_text)

            if not cleaned:
                ExtractionError.log_debug_error("EMPTY_CLEANED_RESPONSE", "Cleaned response is empty",
                                                "Response cleaning")
                return "EXTRACTION_ERROR: AI response is empty after cleaning"

            logger.debug(f"Cleaned response length: {len(cleaned)}")

            # Parse JSON
            parsed = finalize_extracted_content(cleaned)

            if isinstance(parsed, str):
                # Error occurred during parsing
                return parsed

            if parsed is None:
                ExtractionError.log_debug_error("PARSING_RETURNED_NONE", "JSON parsing returned None", "JSON parsing")
                return "EXTRACTION_ERROR: Failed to parse AI response"

            logger.info(f"Successfully extracted and parsed content with {len(parsed)} sections")
            return parsed

        except Exception as e:
            ExtractionError.log_debug_error("RESPONSE_PROCESSING_ERROR", str(e), "Processing AI response")
            return "EXTRACTION_ERROR: Failed to process AI response"

    except Exception as e:
        ExtractionError.log_debug_error("CRITICAL_EXTRACTION_ERROR", str(e), "Main extraction function")
        return "CRITICAL_ERROR: Unexpected error during extraction"