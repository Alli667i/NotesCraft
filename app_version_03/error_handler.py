import re
from datetime import datetime


class ErrorHandler:
    """
    Centralized error handling for the AI Notes app.
    Returns both user-friendly messages and technical details.
    """

    def __init__(self):
        # Error type mappings with professional, friendly messages
        self.error_types = {
            # API Related Errors
            "API_KEY_ERROR": "We're experiencing an issue with our AI service. Please try again in a few minutes.",
            "API_RATE_LIMIT": "Our service is currently busy. Please wait a moment and try again.",
            "API_QUOTA_EXCEEDED": "We've reached our daily processing limit. Service will resume tomorrow.",
            "API_TIMEOUT": "The processing is taking longer than expected. Please try again.",
            "API_CONNECTION_ERROR": "We're having trouble connecting to our AI service. Please try again.",

            # File Processing Errors
            "FILE_EXTRACTION_ERROR": "We couldn't read your file properly. Please try uploading a different PDF or DOCX.",
            "FILE_CORRUPTED": "This file appears to be corrupted. Please try uploading it again.",
            "FILE_TOO_COMPLEX": "This document is too complex to process. Try splitting it into smaller sections.",
            "FILE_UNSUPPORTED": "This file type is not supported. Please upload a PDF or DOCX file.",

            # Content Generation Errors
            "NOTES_GENERATION_ERROR": "We encountered an issue while generating your notes. Please try again.",
            "CONTENT_TOO_LARGE": "This document is too large to process. Please try splitting it into smaller parts.",
            "INVALID_CONTENT": "The document content appears incomplete. Please check your file and try again.",

            # JSON/Parsing Errors
            "JSON_PARSE_ERROR": "We encountered a processing error. Please try again.",
            "RESPONSE_VALIDATION_ERROR": "There was an issue with the response format. Please try again.",

            # General System Errors
            "UNEXPECTED_ERROR": "An unexpected error occurred. Our team has been notified.",
            "PROCESSING_ERROR": "We encountered an issue during processing. Please try again.",
            "WORD_FILE_ERROR": "There was an issue creating your Word file. Please try again.",

            # Default fallback
            "UNKNOWN_ERROR": "Something went wrong. Please try again or contact support if the issue persists."
        }

    def classify_error(self, technical_error: str) -> str:
        """
        Automatically classify errors based on technical error messages.
        Returns the appropriate error type.
        """
        error_lower = technical_error.lower()

        # API Key issues - check for environment variables specifically
        if any(keyword in error_lower for keyword in
               ["api key", "authentication", "unauthorized", "401", "environment variables",
                "google_api_key not found"]):
            return "API_KEY_ERROR"

        # Rate limiting
        if any(keyword in error_lower for keyword in ["rate limit", "429", "too many requests"]):
            return "API_RATE_LIMIT"

        # Quota exceeded
        if any(keyword in error_lower for keyword in ["quota", "limit exceeded", "403"]):
            return "API_QUOTA_EXCEEDED"

        # Timeout issues
        if any(keyword in error_lower for keyword in ["timeout", "timed out", "504", "502"]):
            return "API_TIMEOUT"

        # Connection problems
        if any(keyword in error_lower for keyword in ["connection", "network", "503", "500"]):
            return "API_CONNECTION_ERROR"

        # JSON parsing issues
        if any(keyword in error_lower for keyword in ["json", "parsing", "decode", "invalid json"]):
            return "JSON_PARSE_ERROR"

        # File extraction problems
        if any(keyword in error_lower for keyword in ["extraction", "pdf", "docx", "file"]):
            return "FILE_EXTRACTION_ERROR"

        # Notes generation issues
        if any(keyword in error_lower for keyword in ["notes generation", "generate content"]):
            return "NOTES_GENERATION_ERROR"

        # Word file creation
        if any(keyword in error_lower for keyword in ["word file", "docx creation"]):
            return "WORD_FILE_ERROR"

        # Default to unknown
        return "UNKNOWN_ERROR"

    def handle_error(self, error_type: str = None, technical_error: str = "", context: str = ""):
        """
        Main error handling function.

        Args:
            error_type: Specific error type (optional - will auto-classify if not provided)
            technical_error: The actual technical error message
            context: Additional context (like which function failed)

        Returns:
            dict: Contains user_message, technical_error, error_type, and timestamp
        """

        # Auto-classify if no error type provided
        if not error_type and technical_error:
            error_type = self.classify_error(technical_error)
        elif not error_type:
            error_type = "UNKNOWN_ERROR"

        # Get user-friendly message
        user_message = self.error_types.get(error_type, self.error_types["UNKNOWN_ERROR"])

        # Add context to technical error if provided
        full_technical_error = f"{context}: {technical_error}" if context else technical_error

        # Create error response
        error_response = {
            "user_message": user_message,
            "technical_error": full_technical_error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }

        return error_response

    def is_retryable_error(self, error_type: str) -> bool:
        """
        Check if an error type is typically retryable.
        Useful for determining if we should show 'Try Again' button.
        """
        retryable_errors = {
            "API_TIMEOUT", "API_CONNECTION_ERROR", "API_RATE_LIMIT",
            "PROCESSING_ERROR", "NOTES_GENERATION_ERROR", "WORD_FILE_ERROR"
        }
        return error_type in retryable_errors


# Create a global instance for easy importing
error_handler = ErrorHandler()


# Convenience function for quick use
def handle_error(error_type: str = None, technical_error: str = "", context: str = ""):
    """
    Quick function to handle errors.
    Usage: handle_error("API_KEY_ERROR", "Invalid API key", "extraction")
    """
    return error_handler.handle_error(error_type, technical_error, context)


# Additional helper functions
def handle_api_error(technical_error: str, context: str = ""):
    """Handle API-related errors specifically"""
    return error_handler.handle_error(None, technical_error, f"API Error - {context}")


def handle_file_error(technical_error: str, context: str = ""):
    """Handle file processing errors specifically"""
    return error_handler.handle_error(None, technical_error, f"File Processing - {context}")


def handle_generation_error(technical_error: str, context: str = ""):
    """Handle notes generation errors specifically"""
    return error_handler.handle_error(None, technical_error, f"Notes Generation - {context}")