import os
from pymongo import MongoClient
from datetime import datetime


class MongoFileLogger:
    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise Exception("MONGODB_URI not set in environment variables")

        self.client = MongoClient(mongo_uri)
        self.db = self.client['notescraft']
        self.logs = self.db['processing_logs']

        # Create index on session_id for faster lookups
        self.logs.create_index("session_id", unique=True)

    def start_file_processing(self, filename, file_size_mb, page_count, user_email):
        """Start logging a new file processing session"""
        session_id = f"{filename}_{datetime.now().isoformat()}"

        log_entry = {
            "session_id": session_id,
            "user_email": user_email,
            "filename": filename,
            "file_size_mb": file_size_mb,
            "page_count": page_count,
            "start_time": datetime.now().isoformat(),
            "status": "processing",
            "downloaded": False,
            "extraction": {},
            "generation": {}
        }

        self.logs.insert_one(log_entry)
        print(f"Started logging session: {session_id}")
        return session_id

    def log_extraction_start(self, session_id):
        """Log extraction start"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "extraction.start_time": datetime.now().isoformat()
            }}
        )
        print(f"Started extraction for session: {session_id}")

    def log_extraction_complete(self, session_id, input_tokens, output_tokens, total_tokens):
        """Log extraction completion"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "extraction.end_time": datetime.now().isoformat(),
                "extraction.tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                }
            }}
        )
        print(f"Completed extraction for session: {session_id} ({total_tokens} tokens)")

    def log_generation_start(self, session_id, content_sections):
        """Log generation start"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "generation.start_time": datetime.now().isoformat(),
                "content_sections": content_sections
            }}
        )
        print(f"Started generation for session: {session_id}")

    def log_generation_complete(self, session_id, input_tokens, output_tokens, total_tokens):
        """Log generation completion"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "generation.end_time": datetime.now().isoformat(),
                "generation.tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                }
            }}
        )
        print(f"Completed generation for session: {session_id} ({total_tokens} tokens)")

    def log_processing_success(self, session_id):
        """Mark processing as successful"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "success",
                "end_time": datetime.now().isoformat()
            }}
        )
        print(f"Completed processing session: {session_id} (Status: success)")

    def log_processing_failure(self, session_id, error_type, technical_error, processing_step):
        """Log processing failure"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "failed",
                "error": {
                    "error_type": error_type,
                    "technical_error": technical_error,
                    "processing_step": processing_step
                },
                "end_time": datetime.now().isoformat()
            }}
        )
        print(f"Failed processing session: {session_id} (Error: {error_type})")

    def update_download_status(self, session_id):
        """Mark file as downloaded"""
        self.logs.update_one(
            {"session_id": session_id},
            {"$set": {"downloaded": True}}
        )

    def read_logs(self):
        """Read all logs"""
        return list(self.logs.find({}, {'_id': 0}).sort("start_time", -1))

    def get_stats_summary(self):
        """Get summary statistics"""
        all_logs = list(self.logs.find({}))

        total = len(all_logs)
        successful = len([l for l in all_logs if l.get('status') == 'success'])
        failed = len([l for l in all_logs if l.get('status') == 'failed'])
        downloaded = len([l for l in all_logs if l.get('downloaded')])

        total_extraction_tokens = sum(
            l.get('extraction', {}).get('tokens', {}).get('total', 0)
            for l in all_logs
        )
        total_generation_tokens = sum(
            l.get('generation', {}).get('tokens', {}).get('total', 0)
            for l in all_logs
        )

        return {
            'total_processed': total,
            'successful': successful,
            'failed': failed,
            'downloaded': downloaded,
            'total_extraction_tokens': total_extraction_tokens,
            'total_generation_tokens': total_generation_tokens,
            'average_processing_time': 0
        }


# Create global instance and wrapper functions for backward compatibility
file_logger = MongoFileLogger()


def start_file_processing(filename, file_size_mb, page_count, user_email):
    return file_logger.start_file_processing(filename, file_size_mb, page_count, user_email)


def log_extraction_start(session_id):
    return file_logger.log_extraction_start(session_id)


def log_extraction_complete(session_id, input_tokens, output_tokens, total_tokens):
    return file_logger.log_extraction_complete(session_id, input_tokens, output_tokens, total_tokens)


def log_generation_start(session_id, content_sections):
    return file_logger.log_generation_start(session_id, content_sections)


def log_generation_complete(session_id, input_tokens, output_tokens, total_tokens):
    return file_logger.log_generation_complete(session_id, input_tokens, output_tokens, total_tokens)


def log_processing_success(session_id):
    return file_logger.log_processing_success(session_id)


def log_processing_failure(session_id, error_type, technical_error, processing_step):
    return file_logger.log_processing_failure(session_id, error_type, technical_error, processing_step)