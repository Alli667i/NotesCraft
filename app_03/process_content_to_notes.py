import google.generativeai as genai
import json
import logging
import os
from dotenv import load_dotenv
from Instructions_for_Notes_genearation import for_detail_notes

load_dotenv()

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def generate_notes_from_content(book_text):
    """
    Generate notes from extracted content - simplified and robust version
    """
    # Basic validation only
    if not GOOGLE_API_KEY:
        logger.error("Missing Google API key")
        return "API_KEY_ERROR: Missing API key configuration"

    if not book_text or not isinstance(book_text, dict):
        logger.error("Invalid input content")
        return "INPUT_ERROR: No valid content provided"

    try:
        # Initialize model
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=for_detail_notes
        )
        logger.info("Model initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        return f"API_ERROR: {str(e)}"

    all_notes = []
    processed_sections = 0

    # Process each section
    for topic, content in book_text.items():
        try:
            # Skip truly empty content
            if not content or len(content.strip()) < 10:
                continue

            logger.info(f"Processing: {topic[:50]}...")

            # Generate content
            response = model.generate_content(f"{topic} {content}")

            # Extract text - simple approach
            if response and hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content.parts:
                        text_content = "".join([part.text for part in candidate.content.parts if hasattr(part, 'text')])

                        if text_content and len(text_content.strip()) > 20:
                            # Try to parse as JSON, but don't be strict
                            try:
                                # Clean common formatting issues
                                cleaned = text_content.replace("```json", "").replace("```", "").strip()

                                # Try direct parsing first
                                parsed = json.loads(cleaned)

                                # Handle different response formats
                                if isinstance(parsed, list):
                                    all_notes.extend(parsed)
                                elif isinstance(parsed, dict):
                                    all_notes.append(parsed)

                                processed_sections += 1
                                break

                            except json.JSONDecodeError:
                                # If JSON parsing fails, create a simple text note
                                all_notes.append({
                                    "type": "note",
                                    "text": text_content.strip()
                                })
                                processed_sections += 1
                                break

        except Exception as e:
            logger.warning(f"Error processing section '{topic}': {e}")
            # Continue processing other sections instead of failing
            continue

    # Check if we got any results
    if not all_notes:
        logger.error("No notes were generated from any section")
        return "PROCESSING_ERROR: No content could be processed"

    if processed_sections == 0:
        logger.error("No sections were successfully processed")
        return "PROCESSING_ERROR: Failed to process content"

    logger.info(f"Successfully generated {len(all_notes)} notes from {processed_sections} sections")
    return all_notes