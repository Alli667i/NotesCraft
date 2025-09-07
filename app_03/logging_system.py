import json
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import gzip
from threading import Lock
import queue
import threading
import time


class ProductionLogger:
    """Production-ready logging system with web viewer"""

    def __init__(self, log_dir: str = "logs", max_file_size_mb: int = 10, max_files: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.max_files = max_files
        self.current_date = datetime.now().date()
        self.lock = Lock()

        # Async logging queue
        self.log_queue = queue.Queue()
        self.logger_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.logger_thread.start()

        # Initialize current log file
        self._setup_current_log_file()

    def _setup_current_log_file(self):
        """Setup the current log file for today"""
        self.current_log_file = self.log_dir / f"app_{self.current_date.strftime('%Y%m%d')}.log"

    def _log_worker(self):
        """Background worker to write logs asynchronously"""
        while True:
            try:
                log_entry = self.log_queue.get(timeout=1)
                if log_entry is None:  # Shutdown signal
                    break
                self._write_log_to_file(log_entry)
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                # Fallback - write to console if logging fails
                print(f"Logging error: {e}")

    def _write_log_to_file(self, log_entry: dict):
        """Write log entry to file with rotation"""
        with self.lock:
            # Check if we need a new file (new day or size limit)
            current_date = datetime.now().date()
            if current_date != self.current_date:
                self.current_date = current_date
                self._setup_current_log_file()

            # Check file size and rotate if needed
            if self.current_log_file.exists() and self.current_log_file.stat().st_size > self.max_file_size:
                self._rotate_current_file()

            # Write log entry
            try:
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                print(f"Failed to write log: {e}")

    def _rotate_current_file(self):
        """Rotate current log file when it gets too large"""
        if not self.current_log_file.exists():
            return

        # Find next rotation number
        rotation_num = 1
        while True:
            rotated_name = f"app_{self.current_date.strftime('%Y%m%d')}_{rotation_num:03d}.log"
            rotated_path = self.log_dir / rotated_name
            if not rotated_path.exists():
                break
            rotation_num += 1

        # Rename current file
        self.current_log_file.rename(rotated_path)

        # Compress old file to save space
        self._compress_log_file(rotated_path)

    def _compress_log_file(self, file_path: Path):
        """Compress log file to save disk space"""
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                    f_out.writelines(f_in)
            file_path.unlink()  # Delete original
        except Exception as e:
            print(f"Failed to compress log file: {e}")

    def cleanup_old_logs(self):
        """Remove old log files beyond retention limit"""
        try:
            log_files = list(self.log_dir.glob("app_*.log*"))
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(log_files) > self.max_files:
                for old_file in log_files[self.max_files:]:
                    old_file.unlink()
        except Exception as e:
            print(f"Failed to cleanup old logs: {e}")

    def log(self, level: str, component: str, message: str, user_action: str = "",
            additional_data: dict = None, error_details: str = ""):
        """Main logging method - adds to queue for async processing"""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "component": component,
            "message": message,
            "user_action": user_action,
            "error_details": error_details,
            "additional_data": additional_data or {},
            "traceback": traceback.format_exc() if level.upper() == "ERROR" and traceback.format_exc() != "NoneType: None\n" else "",
            "app_version": "1.0"
        }

        # Add to queue for async processing
        try:
            self.log_queue.put_nowait(log_entry)
        except queue.Full:
            # If queue is full, write directly (shouldn't happen often)
            self._write_log_to_file(log_entry)

        # Also print to console for development
        print(f"[{level.upper()}] {component}: {message}")

    def info(self, component: str, message: str, **kwargs):
        """Log info level message"""
        self.log("INFO", component, message, **kwargs)

    def warning(self, component: str, message: str, **kwargs):
        """Log warning level message"""
        self.log("WARNING", component, message, **kwargs)

    def error(self, component: str, message: str, **kwargs):
        """Log error level message"""
        self.log("ERROR", component, message, **kwargs)

    def get_logs(self, date: str = None, level: str = None, component: str = None,
                 limit: int = 100) -> List[dict]:
        """Retrieve logs with filtering"""
        logs = []

        try:
            if date:
                # Get logs for specific date
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                log_files = list(self.log_dir.glob(f"app_{date_obj.strftime('%Y%m%d')}*.log*"))
            else:
                # Get recent logs
                log_files = list(self.log_dir.glob("app_*.log*"))
                log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                log_files = log_files[:5]  # Last 5 files

            for log_file in log_files:
                try:
                    if log_file.suffix == '.gz':
                        with gzip.open(log_file, 'rt', encoding='utf-8') as f:
                            lines = f.readlines()
                    else:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                    for line in lines:
                        try:
                            log_entry = json.loads(line.strip())

                            # Apply filters
                            if level and log_entry.get('level', '').upper() != level.upper():
                                continue
                            if component and component.lower() not in log_entry.get('component', '').lower():
                                continue

                            logs.append(log_entry)

                        except json.JSONDecodeError:
                            continue

                except Exception as e:
                    print(f"Error reading log file {log_file}: {e}")

        except Exception as e:
            print(f"Error retrieving logs: {e}")

        # Sort by timestamp and limit
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return logs[:limit]

    def get_log_stats(self) -> dict:
        """Get logging statistics"""
        try:
            log_files = list(self.log_dir.glob("app_*.log*"))
            total_size = sum(f.stat().st_size for f in log_files)

            # Count logs by level for today
            today_logs = self.get_logs(date=datetime.now().strftime('%Y-%m-%d'), limit=1000)
            level_counts = {}
            for log in today_logs:
                level = log.get('level', 'UNKNOWN')
                level_counts[level] = level_counts.get(level, 0) + 1

            return {
                "total_log_files": len(log_files),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "todays_log_count": len(today_logs),
                "level_breakdown": level_counts,
                "oldest_log": min((f.stat().st_mtime for f in log_files), default=0),
                "newest_log": max((f.stat().st_mtime for f in log_files), default=0)
            }
        except Exception as e:
            return {"error": str(e)}


# Initialize global logger
production_logger = ProductionLogger()


# Convenience functions for easy use
def log_info(component: str, message: str, **kwargs):
    production_logger.info(component, message, **kwargs)


def log_warning(component: str, message: str, **kwargs):
    production_logger.warning(component, message, **kwargs)


def log_error(component: str, message: str, **kwargs):
    production_logger.error(component, message, **kwargs)