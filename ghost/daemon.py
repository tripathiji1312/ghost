"""
Ghost Daemon - Project-scoped background process for file watching.

Manages a persistent file watcher per project that survives terminal disconnection.
Communicates with the CLI via PID file (.ghost/pid) and logs (.ghost/logs/ghost.log).

Usage (called by CLI, not directly):
    python -m ghost.daemon /path/to/project
"""

import logging
import os
import signal
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Global shutdown coordination
# ──────────────────────────────────────────────────────────────────────────────

_shutdown = threading.Event()


def _signal_handler(signum: int, frame) -> None:
    """Signal handler: set shutdown event to trigger graceful stop.

    Must be async-signal-safe — only sets a flag, never allocates or logs.
    """
    _shutdown.set()


# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────


def setup_daemon_logging(log_dir: Path) -> logging.Logger:
    """Configure rotating file logging for the daemon process.

    Args:
        log_dir: Directory to store log files (e.g. .ghost/logs).

    Returns:
        Configured logger instance.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ghost.log"

    logger = logging.getLogger("ghost.daemon")
    logger.setLevel(logging.DEBUG)

    # Rotating file handler: 10 MB per file, keep 5 backups
    handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        delay=True,  # Don't open until first write
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also mirror WARNING+ to stderr so errors surface in terminal
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    return logger


# ──────────────────────────────────────────────────────────────────────────────
# PID file management
# ──────────────────────────────────────────────────────────────────────────────


def _write_pid(pid_file: Path) -> None:
    """Write the current process PID to the PID file atomically."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    # Write and fsync atomically — keep fd open during sync
    fd = os.open(str(pid_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
    try:
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_pid(pid_file: Path) -> None:
    """Remove the PID file only if it belongs to this process."""
    try:
        if pid_file.exists() and pid_file.read_text().strip() == str(os.getpid()):
            pid_file.unlink()
    except (OSError, ValueError):
        pass


def check_pid(pid_file: Path) -> Optional[int]:
    """Check if a daemon is running via PID file + os.kill(pid, 0).

    Args:
        pid_file: Path to the PID file.

    Returns:
        The PID if running, or None if not running / stale.
    """
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # No-op if alive, raises OSError if dead
        return pid
    except (OSError, ValueError):
        # Stale PID file — clean it up
        try:
            pid_file.unlink(missing_ok=True)
        except OSError:
            pass
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Daemon runner (core logic)
# ──────────────────────────────────────────────────────────────────────────────


def _load_env(project_root: Path) -> None:
    """Load .env from the project root if it exists."""
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)
        except ImportError:
            pass  # dotenv is optional for daemon


def _build_watcher(project_root: Path, logger: logging.Logger):
    """Build and start the watchdog file observer.

    This replicates the watcher logic from main.start_watching() but
    adapted for daemon use (no console output, all goes to log).

    Args:
        project_root: Root directory to watch.
        logger: Logger instance for daemon.

    Returns:
        The started Observer instance.
    """
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    from ghost.config import get_config
    from ghost.job_queue import JobQueue

    config = get_config(project_root)
    queue = JobQueue(
        debounce_seconds=config.watcher.debounce_seconds,
        max_workers=1,
    )
    queue.start()

    class DaemonEventHandler(FileSystemEventHandler):
        """Watchdog event handler that logs all activity and triggers test gen."""

        def _get_file(self, event: FileSystemEvent) -> Optional[str]:
            path = str(event.src_path)
            if path.endswith("~"):
                path = path[:-1]
            return path

        def _check_path(self, file_path: str) -> bool:
            normalized = file_path.replace("\\", "/")
            if "/tests/" in normalized or normalized.endswith("/tests"):
                return False
            if "/__pycache__/" in normalized or normalized.endswith(".pyc"):
                return False
            file = normalized.split("/")[-1] if "/" in normalized else file_path
            if "test" in file.lower() or "tmp" in file.lower():
                return False
            if file.startswith(".git") or file.endswith(".log"):
                return False
            if not file.endswith(".py"):
                return False
            return True

        def _process_file(self, file_path: str) -> None:
            file_name = file_path.split("/")[-1]
            logger.info(f"File modified: {file_name}")

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning(f"Cannot read file {file_path}: {e}")
                return

            try:
                from ghost import init as ghost_init_module

                result = ghost_init_module.walk_and_modify_json(
                    str(project_root), file_path, file_name
                )
                if result is None:
                    logger.warning(f"Skipping {file_name}: syntax errors")
                    return
            except Exception as e:
                logger.error(f"Failed to update context for {file_name}: {e}")
                return

            try:
                from ghost.chat import TestGenerator
                from ghost.runner import classify_error, run_test

                generator = TestGenerator(config=config)
                code = generator.get_test_code(content, str(project_root), file_name)

                test_path = project_root / config.tests.output_dir / f"test_{file_name}"
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(code)
                logger.info(f"Tests generated: test_{file_name}")

                max_attempts = config.tests.max_heal_attempts if config.tests.auto_heal else 0
                for attempt in range(max_attempts):
                    return_code, stdout, stderr = run_test(str(test_path), str(project_root))
                    error_type = classify_error(stderr, stdout)

                    if return_code == 0:
                        logger.info(f"Tests passed: test_{file_name}")
                        break

                    if error_type == "LOGIC":
                        if config.tests.use_judge:
                            judge = TestGenerator(config=config)
                            result = judge.consult_the_judge(
                                content,
                                str(project_root),
                                file_name,
                                str(test_path),
                                {"return_code": return_code, "stderr": stderr, "stdout": stdout},
                            )
                            if result == "BUG_IN_CODE":
                                logger.warning(
                                    f"Bug detected in source code, test left unchanged: test_{file_name}"
                                )
                                break
                        else:
                            logger.warning(f"Assertion failed in test_{file_name}, judge disabled")
                            break

                    logger.info(
                        f"Healing attempt {attempt + 1}/{max_attempts} for test_{file_name}"
                    )
                    code = generator.get_test_code(
                        content,
                        str(project_root),
                        file_name,
                        testing=True,
                        test_file_path=str(test_path),
                        errors={"return_code": return_code, "stderr": stderr, "stdout": stdout},
                    )
                    test_path.write_text(code)
                else:
                    logger.warning(f"Max healing attempts reached for test_{file_name}")

            except Exception as e:
                logger.error(f"Test generation/healing failed for {file_name}: {e}")

        def on_modified(self, event: FileSystemEvent) -> None:
            file_path = self._get_file(event)
            if not file_path or not self._check_path(file_path):
                return
            queue.submit(file_path, self._process_file)

        def on_created(self, event: FileSystemEvent) -> None:
            file_path = self._get_file(event)
            if file_path and self._check_path(file_path):
                logger.info(f"File created: {file_path.split('/')[-1]}")

        def on_deleted(self, event: FileSystemEvent) -> None:
            file_path = self._get_file(event)
            if file_path and self._check_path(file_path):
                file_name = file_path.split("/")[-1]
                logger.info(f"File deleted: {file_name}")
                try:
                    from ghost import init as ghost_init_module

                    ghost_init_module.walk_and_delete_json(str(project_root), file_name)
                except Exception as e:
                    logger.error(f"Failed to remove {file_name} from context: {e}")

    event_handler = DaemonEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=str(project_root), recursive=True)
    observer.start()
    return observer


def run_daemon(project_root_str: str) -> None:
    """Main entry point for the daemon process.

    Called from subprocess via `python -m ghost.daemon <project_root>`.

    Args:
        project_root_str: Absolute path to the project root directory.
    """
    project_root = Path(project_root_str).resolve()
    ghost_dir = project_root / ".ghost"
    log_dir = ghost_dir / "logs"
    pid_file = ghost_dir / "pid"

    # ── Signal handling ──────────────────────────────────────────────────
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)  # Terminal HUP → ignore
    except ValueError:
        # Not in main thread; signals can't be set. This is fine when
        # running in a subprocess (the child's main thread handles signals).
        pass

    # ── Write PID file ───────────────────────────────────────────────────
    _write_pid(pid_file)

    # ── Logging ──────────────────────────────────────────────────────────
    logger = setup_daemon_logging(log_dir)
    logger.info(f"Ghost daemon starting (PID: {os.getpid()})")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Log file: {log_dir / 'ghost.log'}")

    # ── Load environment ─────────────────────────────────────────────────
    _load_env(project_root)

    # Redirect stdout/stderr to prevent accidental usage in daemon mode
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115

    observer = None
    last_error: Optional[str] = None

    try:
        # ── Start watcher ────────────────────────────────────────────────
        observer = _build_watcher(project_root, logger)
        logger.info("File watcher started successfully")

        # ── Block until shutdown signal ──────────────────────────────────
        _shutdown.wait()

    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        logger.exception(f"Daemon error: {last_error}")
    finally:
        logger.info("Daemon shutting down...")

        if observer is not None:
            try:
                observer.stop()
                observer.join(timeout=10)
            except Exception as e:
                logger.warning(f"Observer shutdown warning: {e}")

        _remove_pid(pid_file)
        logger.info("Daemon stopped")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point (python -m ghost.daemon <project_root>)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ghost.daemon <project_root>", file=sys.stderr)
        sys.exit(1)

    run_daemon(sys.argv[1])
