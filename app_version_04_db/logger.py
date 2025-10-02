import json
import os
from datetime import datetime
from pathlib import Path


class SimpleFileLogger:
    """
    Simple logging system - One log entry per file processing.
    Tracks the entire journey of each file from upload to completion/failure.
    """

    def __init__(self, logs_folder="logs"):
        # Create logs folder if it doesn't exist
        self.logs_folder = Path(logs_folder)
        self.logs_folder.mkdir(exist_ok=True)

        # Store active processing sessions
        self.active_sessions = {}  # filename -> session data

        print(f"Logger initialized. Logs will be saved in: {self.logs_folder}")

    def get_current_log_file(self):
        """Get current month's log file name"""
        now = datetime.now()
        filename = f"processing_{now.year}_{now.month:02d}.log"
        return self.logs_folder / filename

    def write_log(self, log_data):
        """Write a complete log entry to file"""
        try:
            log_file = self.get_current_log_file()

            # Add timestamp to log
            log_data["logged_at"] = datetime.now().isoformat()

            # Write as one JSON object per line
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data) + "\n")

        except Exception as e:
            print(f"Failed to write log: {e}")

    def start_processing(self, filename, file_size_mb, page_count,user_email = None):
        """
        Start tracking a new file processing session.
        Returns a session_id to track this processing.
        """
        session_id = f"{filename}_{datetime.now().isoformat()}"

        # Initialize session data
        session_data = {
            "session_id": session_id,
            "user_email": user_email,
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2),
            "page_count": page_count,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_duration": None,
            "status": "processing",  # processing, success, failed
            "extraction": {
                "start_time": None,
                "end_time": None,
                "duration": None,
                "tokens": {"input": 0, "output": 0, "total": 0}
            },
            "generation": {
                "start_time": None,
                "end_time": None,
                "duration": None,
                "tokens": {"input": 0, "output": 0, "total": 0}
            },
            "error": None,
            "downloaded": False
        }

        # Store in active sessions
        self.active_sessions[session_id] = session_data

        print(f"Started processing session: {session_id}")
        return session_id

    def start_extraction(self, session_id):
        """Mark extraction phase as started"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["extraction"]["start_time"] = datetime.now().isoformat()
            print(f"Started extraction for session: {session_id}")

    def complete_extraction(self, session_id, input_tokens, output_tokens, total_tokens):
        """Mark extraction phase as completed with token usage"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            extraction_end = datetime.now()
            session["extraction"]["end_time"] = extraction_end.isoformat()

            # Calculate extraction duration
            if session["extraction"]["start_time"]:
                start_time = datetime.fromisoformat(session["extraction"]["start_time"])
                duration = (extraction_end - start_time).total_seconds()
                session["extraction"]["duration"] = round(duration, 2)

            # Store token usage
            session["extraction"]["tokens"] = {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens
            }

            print(f"Completed extraction for session: {session_id} ({total_tokens} tokens)")

    def start_generation(self, session_id, content_sections_count):
        """Mark notes generation phase as started"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["generation"]["start_time"] = datetime.now().isoformat()
            self.active_sessions[session_id]["content_sections"] = content_sections_count
            print(f"Started generation for session: {session_id}")

    def complete_generation(self, session_id, input_tokens, output_tokens, total_tokens):
        """Mark notes generation phase as completed with token usage"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            generation_end = datetime.now()
            session["generation"]["end_time"] = generation_end.isoformat()

            # Calculate generation duration
            if session["generation"]["start_time"]:
                start_time = datetime.fromisoformat(session["generation"]["start_time"])
                duration = (generation_end - start_time).total_seconds()
                session["generation"]["duration"] = round(duration, 2)

            # Store token usage
            session["generation"]["tokens"] = {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens
            }

            print(f"Completed generation for session: {session_id} ({total_tokens} tokens)")

    def mark_download(self, session_id):
        """Mark that the user downloaded the generated notes"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["downloaded"] = True
            print(f"Marked download for session: {session_id}")

    def update_download_status(self, session_id):
        """Update download status for an already completed session"""
        try:
            log_file = self.get_current_log_file()
            if not log_file.exists():
                return

            # Read all logs
            logs = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))

            # Find and update the matching session
            for log in logs:
                if log.get('session_id') == session_id:
                    log['downloaded'] = True
                    break

            # Rewrite the file
            with open(log_file, "w", encoding="utf-8") as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")

        except Exception as e:
            print(f"Failed to update download status: {e}")

    def complete_processing(self, session_id, success=True):
        """
        Mark processing as completed (success or failure).
        This writes the final log entry and cleans up the session.
        """
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return

        session = self.active_sessions[session_id]

        # Set completion time and status
        end_time = datetime.now()
        session["end_time"] = end_time.isoformat()
        session["status"] = "success" if success else "failed"

        # Calculate total duration
        if session["start_time"]:
            start_time = datetime.fromisoformat(session["start_time"])
            total_duration = (end_time - start_time).total_seconds()
            session["total_duration"] = round(total_duration, 2)

        # Write the complete log entry
        self.write_log(session)

        # Clean up active session
        del self.active_sessions[session_id]

        print(f"Completed processing session: {session_id} (Status: {session['status']})")

    def fail_processing(self, session_id, error_type, error_message, processing_step):
        """
        Mark processing as failed due to an error.
        This writes the final log entry with error details.
        """
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return

        session = self.active_sessions[session_id]

        # Set error details
        session["error"] = {
            "error_type": error_type,
            "error_message": error_message,
            "processing_step": processing_step,
            "error_time": datetime.now().isoformat()
        }

        # Complete the processing as failed
        self.complete_processing(session_id, success=False)

        print(f"Failed processing session: {session_id} (Error: {error_type})")

    def read_logs(self, month=None, year=None):
        """Read logs from a specific month/year"""
        try:
            if month is None or year is None:
                log_file = self.get_current_log_file()
            else:
                filename = f"processing_{year}_{month:02d}.log"
                log_file = self.logs_folder / filename

            if not log_file.exists():
                return []

            logs = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            return logs

        except Exception as e:
            print(f"Failed to read logs: {e}")
            return []

    def get_available_months(self):
        """Get list of all months that have log files"""
        months = []

        for log_file in self.logs_folder.glob("processing_*.log"):
            try:
                # Extract year and month from filename like "processing_2025_01.log"
                parts = log_file.stem.split("_")
                if len(parts) == 3:
                    year = int(parts[1])
                    month = int(parts[2])
                    months.append((year, month))
            except (ValueError, IndexError):
                continue

        months.sort(reverse=True)  # Newest first
        return months

    def get_stats_summary(self):
        """Get statistics summary from current month logs"""
        logs = self.read_logs()

        stats = {
            "total_processed": len(logs),
            "successful": len([l for l in logs if l.get("status") == "success"]),
            "failed": len([l for l in logs if l.get("status") == "failed"]),
            "downloaded": len([l for l in logs if l.get("downloaded", False)]),
            "total_extraction_tokens": sum(l.get("extraction", {}).get("tokens", {}).get("total", 0) for l in logs),
            "total_generation_tokens": sum(l.get("generation", {}).get("tokens", {}).get("total", 0) for l in logs),
            "average_processing_time": 0
        }

        # Calculate average processing time
        processing_times = [l.get("total_duration", 0) for l in logs if l.get("total_duration")]
        if processing_times:
            stats["average_processing_time"] = round(sum(processing_times) / len(processing_times), 1)

        return stats


# Create global logger instance
file_logger = SimpleFileLogger()


# Convenience functions for easy use
def start_file_processing(filename, file_size_mb, page_count,user_email=None):
    """Start tracking a new file processing session"""
    return file_logger.start_processing(filename, file_size_mb, page_count,user_email)


def log_extraction_start(session_id):
    """Mark extraction as started"""
    file_logger.start_extraction(session_id)


def log_extraction_complete(session_id, input_tokens, output_tokens, total_tokens):
    """Mark extraction as completed"""
    file_logger.complete_extraction(session_id, input_tokens, output_tokens, total_tokens)


def log_generation_start(session_id, content_sections):
    """Mark generation as started"""
    file_logger.start_generation(session_id, content_sections)


def log_generation_complete(session_id, input_tokens, output_tokens, total_tokens):
    """Mark generation as completed"""
    file_logger.complete_generation(session_id, input_tokens, output_tokens, total_tokens)


def log_file_download(session_id):
    """Mark file as downloaded"""
    file_logger.mark_download(session_id)


def log_processing_success(session_id):
    """Mark processing as successfully completed"""
    file_logger.complete_processing(session_id, success=True)


def log_processing_failure(session_id, error_type, error_message, processing_step):
    """Mark processing as failed with error details"""
    file_logger.fail_processing(session_id, error_type, error_message, processing_step)

