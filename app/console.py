"""
Ghost Console - Beautiful CLI output with animations and styling.

A professional console output system inspired by tools like Vercel, Cargo, and npm.
"""

import sys
import time
import threading
import itertools
from datetime import datetime
from enum import Enum
from typing import Optional
import shutil


# ═══════════════════════════════════════════════════════════════════════════════
# ANSI COLOR CODES & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """ANSI color codes for terminal styling."""
    # Reset
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    
    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class Icons:
    """Beautiful Unicode icons for different states."""
    # Status icons
    SUCCESS = "✔"
    ERROR = "✖"
    WARNING = "⚠"
    INFO = "ℹ"
    DEBUG = "⚙"
    
    # Action icons
    ARROW = "→"
    ROCKET = "🚀"
    SPARKLES = "✨"
    FIRE = "🔥"
    GHOST = "👻"
    BRAIN = "🧠"
    MAGIC = "🪄"
    TARGET = "🎯"
    LIGHTNING = "⚡"
    PACKAGE = "📦"
    FILE = "📄"
    FOLDER = "📁"
    CLOCK = "⏱"
    HOURGLASS = "⏳"
    CHECK = "✓"
    CROSS = "✗"
    DOT = "●"
    CIRCLE = "○"
    STAR = "★"
    DIAMOND = "◆"
    TRIANGLE = "▸"
    PLAY = "▶"
    PAUSE = "⏸"
    STOP = "⏹"
    REFRESH = "↻"
    LINK = "🔗"
    LOCK = "🔒"
    KEY = "🔑"
    BUG = "🐛"
    HAMMER = "🔨"
    WRENCH = "🔧"
    MICROSCOPE = "🔬"
    SHIELD = "🛡"
    JUDGE = "⚖️"


# ═══════════════════════════════════════════════════════════════════════════════
# SPINNER ANIMATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SpinnerStyle(Enum):
    """Different spinner animation styles."""
    DOTS = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    DOTS2 = ("⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷")
    DOTS3 = ("⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈")
    LINE = ("─", "\\", "│", "/")
    CIRCLE = ("◐", "◓", "◑", "◒")
    SQUARE = ("◰", "◳", "◲", "◱")
    ARROW = ("←", "↖", "↑", "↗", "→", "↘", "↓", "↙")
    BOUNCE = ("⠁", "⠂", "⠄", "⠂")
    PULSE = ("█", "▓", "▒", "░", "▒", "▓")
    MOON = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
    CLOCK = ("🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛")
    GHOST = ("👻", "  ", "👻", "  ", "👻")
    GROW = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂")
    AESTHETIC = ("░░░░░", "█░░░░", "██░░░", "███░░", "████░", "█████", "████░", "███░░", "██░░░", "█░░░░")


class GhostSpinner:
    """
    Beautiful animated spinner with multiple styles and colors.
    """
    def __init__(
        self, 
        message: str = "Processing", 
        style: SpinnerStyle = SpinnerStyle.DOTS,
        color: str = Colors.CYAN,
        success_message: Optional[str] = None,
        show_elapsed: bool = True
    ):
        self.message = message
        self.frames = itertools.cycle(style.value)
        self.color = color
        self.success_message = success_message
        self.show_elapsed = show_elapsed
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        self._lock = threading.Lock()

    def _get_elapsed(self) -> str:
        """Get formatted elapsed time."""
        if not self.start_time:
            return ""
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        return f"{minutes}m {seconds:.0f}s"

    def _animate(self):
        """Animation loop running in separate thread."""
        while self.running:
            with self._lock:
                frame = next(self.frames)
                elapsed = f" {Colors.DIM}({self._get_elapsed()}){Colors.RESET}" if self.show_elapsed else ""
                line = f"\r{self.color}{frame}{Colors.RESET} {self.message}{elapsed}"
                sys.stdout.write(f"\033[K{line}")  # Clear line then write
                sys.stdout.flush()
            time.sleep(0.08)

    def start(self):
        """Start the spinner animation."""
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
        return self

    def stop(self, success: bool = True, message: Optional[str] = None):
        """Stop the spinner and show final status."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        
        elapsed = f" {Colors.DIM}({self._get_elapsed()}){Colors.RESET}" if self.show_elapsed else ""
        final_message = message or self.success_message or self.message
        
        if success:
            icon = f"{Colors.BRIGHT_GREEN}{Icons.SUCCESS}{Colors.RESET}"
        else:
            icon = f"{Colors.BRIGHT_RED}{Icons.ERROR}{Colors.RESET}"
        
        sys.stdout.write(f"\r\033[K{icon} {final_message}{elapsed}\n")
        sys.stdout.flush()

    def fail(self, message: Optional[str] = None):
        """Stop spinner with failure status."""
        self.stop(success=False, message=message)

    def update(self, message: str):
        """Update the spinner message."""
        with self._lock:
            self.message = message

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(success=exc_type is None)


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════════════════

class ProgressBar:
    """Beautiful progress bar with percentage and ETA."""
    
    def __init__(
        self, 
        total: int, 
        description: str = "",
        width: int = 40,
        fill_char: str = "█",
        empty_char: str = "░",
        color: str = Colors.CYAN
    ):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.color = color
        self.start_time = time.time()

    def update(self, amount: int = 1):
        """Update progress by amount."""
        self.current = min(self.current + amount, self.total)
        self._render()

    def set(self, value: int):
        """Set progress to specific value."""
        self.current = min(value, self.total)
        self._render()

    def _render(self):
        """Render the progress bar."""
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        empty = self.width - filled
        
        bar = f"{self.color}{self.fill_char * filled}{Colors.DIM}{self.empty_char * empty}{Colors.RESET}"
        percentage = f"{percent * 100:>5.1f}%"
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if self.current > 0 and percent < 1:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {eta:.0f}s"
        elif percent >= 1:
            eta_str = f"Done in {elapsed:.1f}s"
        else:
            eta_str = "ETA: --"
        
        desc = f"{self.description} " if self.description else ""
        line = f"\r{desc}│{bar}│ {percentage} {Colors.DIM}{eta_str}{Colors.RESET}"
        sys.stdout.write(f"\033[K{line}")
        sys.stdout.flush()
        
        if percent >= 1:
            sys.stdout.write("\n")

    def finish(self):
        """Complete the progress bar."""
        self.set(self.total)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSOLE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

class Console:
    """
    Professional console output with beautiful formatting.
    """
    
    _terminal_width: Optional[int] = None
    
    @classmethod
    def get_width(cls) -> int:
        """Get terminal width."""
        if cls._terminal_width is None:
            cls._terminal_width = shutil.get_terminal_size().columns
        return cls._terminal_width

    @staticmethod
    def _timestamp() -> str:
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")

    # ─────────────────────────────────────────────────────────────────────────
    # Basic Output Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    @classmethod
    def print(cls, message: str, end: str = "\n"):
        """Print a simple message."""
        sys.stdout.write(f"{message}{end}")
        sys.stdout.flush()

    @classmethod
    def newline(cls, count: int = 1):
        """Print empty lines."""
        sys.stdout.write("\n" * count)
        sys.stdout.flush()

    @classmethod
    def clear_line(cls):
        """Clear the current line."""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    # ─────────────────────────────────────────────────────────────────────────
    # Status Messages
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def success(cls, message: str, prefix: str = ""):
        """Print success message."""
        icon = f"{Colors.BRIGHT_GREEN}{Icons.SUCCESS}{Colors.RESET}"
        pre = f"{Colors.DIM}{prefix}{Colors.RESET} " if prefix else ""
        print(f"{icon} {pre}{message}")

    @classmethod
    def error(cls, message: str, prefix: str = ""):
        """Print error message."""
        icon = f"{Colors.BRIGHT_RED}{Icons.ERROR}{Colors.RESET}"
        pre = f"{Colors.DIM}{prefix}{Colors.RESET} " if prefix else ""
        print(f"{icon} {pre}{Colors.RED}{message}{Colors.RESET}")

    @classmethod
    def warning(cls, message: str, prefix: str = ""):
        """Print warning message."""
        icon = f"{Colors.BRIGHT_YELLOW}{Icons.WARNING}{Colors.RESET}"
        pre = f"{Colors.DIM}{prefix}{Colors.RESET} " if prefix else ""
        print(f"{icon} {pre}{Colors.YELLOW}{message}{Colors.RESET}")

    @classmethod
    def info(cls, message: str, prefix: str = ""):
        """Print info message."""
        icon = f"{Colors.BRIGHT_BLUE}{Icons.INFO}{Colors.RESET}"
        pre = f"{Colors.DIM}{prefix}{Colors.RESET} " if prefix else ""
        print(f"{icon} {pre}{message}")

    @classmethod
    def debug(cls, message: str):
        """Print debug message."""
        icon = f"{Colors.DIM}{Icons.DEBUG}{Colors.RESET}"
        ts = f"{Colors.DIM}[{cls._timestamp()}]{Colors.RESET}"
        print(f"{icon} {ts} {Colors.DIM}{message}{Colors.RESET}")

    # ─────────────────────────────────────────────────────────────────────────
    # Action Messages (for Ghost-specific operations)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def ghost(cls, message: str):
        """Print Ghost-branded message."""
        icon = f"{Colors.BRIGHT_MAGENTA}{Icons.GHOST}{Colors.RESET}"
        print(f"{icon} {Colors.BRIGHT_WHITE}{message}{Colors.RESET}")

    @classmethod
    def generating(cls, filename: str):
        """Print test generation start message."""
        icon = f"{Colors.BRIGHT_CYAN}{Icons.MAGIC}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        print(f"{icon} Generating tests for {file}")

    @classmethod
    def file_changed(cls, filename: str, action: str = "modified"):
        """Print file change detection message."""
        icon = f"{Colors.BRIGHT_YELLOW}{Icons.FILE}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        act = f"{Colors.DIM}{action}{Colors.RESET}"
        print(f"{icon} File {act}: {file}")

    @classmethod
    def test_passed(cls, filename: str, duration: Optional[float] = None):
        """Print test passed message."""
        icon = f"{Colors.BRIGHT_GREEN}{Icons.SUCCESS}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        dur = f" {Colors.DIM}({duration:.2f}s){Colors.RESET}" if duration else ""
        print(f"{icon} Tests passed: {file}{dur}")

    @classmethod
    def test_failed(cls, filename: str, error_count: int = 0):
        """Print test failed message."""
        icon = f"{Colors.BRIGHT_RED}{Icons.ERROR}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        errors = f" {Colors.RED}({error_count} errors){Colors.RESET}" if error_count else ""
        print(f"{icon} Tests failed: {file}{errors}")

    @classmethod
    def healing(cls, filename: str, attempt: int = 1):
        """Print healing attempt message."""
        icon = f"{Colors.BRIGHT_MAGENTA}{Icons.WRENCH}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        att = f" {Colors.DIM}(attempt {attempt}){Colors.RESET}"
        print(f"{icon} Healing tests: {file}{att}")

    @classmethod
    def judging(cls, filename: str):
        """Print judge consultation message."""
        icon = f"{Colors.BRIGHT_YELLOW}{Icons.JUDGE}{Colors.RESET}"
        file = f"{Colors.BRIGHT_WHITE}{filename}{Colors.RESET}"
        print(f"{icon} Consulting judge for: {file}")

    @classmethod  
    def verdict(cls, is_bug_in_code: bool):
        """Print judge verdict."""
        if is_bug_in_code:
            icon = f"{Colors.BRIGHT_RED}{Icons.BUG}{Colors.RESET}"
            print(f"{icon} {Colors.RED}Verdict: Bug detected in source code!{Colors.RESET}")
        else:
            icon = f"{Colors.BRIGHT_YELLOW}{Icons.HAMMER}{Colors.RESET}"
            print(f"{icon} {Colors.YELLOW}Verdict: Test needs fixing{Colors.RESET}")

    @classmethod
    def rate_limited(cls, wait_seconds: float, attempt: int = 1, max_attempts: int = 5):
        """Print rate limit message with countdown style."""
        icon = f"{Colors.BRIGHT_YELLOW}{Icons.HOURGLASS}{Colors.RESET}"
        print(f"{icon} {Colors.YELLOW}Rate limited{Colors.RESET} - waiting {Colors.BRIGHT_WHITE}{wait_seconds:.1f}s{Colors.RESET} {Colors.DIM}(attempt {attempt}/{max_attempts}){Colors.RESET}")

    @classmethod
    def waiting(cls, seconds: float, reason: str = ""):
        """Print waiting message."""
        icon = f"{Colors.BRIGHT_BLUE}{Icons.CLOCK}{Colors.RESET}"
        rsn = f" {Colors.DIM}({reason}){Colors.RESET}" if reason else ""
        print(f"{icon} Waiting {Colors.BRIGHT_WHITE}{seconds:.1f}s{Colors.RESET}{rsn}")

    # ─────────────────────────────────────────────────────────────────────────
    # Decorative Elements
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def header(cls, title: str, subtitle: str = ""):
        """Print a beautiful header."""
        width = cls.get_width()
        
        print()
        print(f"{Colors.BRIGHT_MAGENTA}{'━' * width}{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  {Icons.GHOST} {title}{Colors.RESET}")
        if subtitle:
            print(f"{Colors.DIM}  {subtitle}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{'━' * width}{Colors.RESET}")
        print()

    @classmethod
    def section(cls, title: str):
        """Print a section header."""
        print()
        print(f"{Colors.BRIGHT_CYAN}{Icons.TRIANGLE} {Colors.BOLD}{title}{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * (len(title) + 4)}{Colors.RESET}")

    @classmethod
    def divider(cls, char: str = "─", color: str = Colors.DIM):
        """Print a divider line."""
        width = min(cls.get_width(), 60)
        print(f"{color}{char * width}{Colors.RESET}")

    @classmethod
    def banner(cls):
        """Print the Ghost banner."""
        banner_text = f"""
{Colors.BRIGHT_MAGENTA}   ▄████  ██░ ██  ▒█████    ██████ ▄▄▄█████▓
  ██▒ ▀█▒▓██░ ██▒▒██▒  ██▒▒██    ▒ ▓  ██▒ ▓▒
 ▒██░▄▄▄░▒██▀▀██░▒██░  ██▒░ ▓██▄   ▒ ▓██░ ▒░
 ░▓█  ██▓░▓█ ░██ ▒██   ██░  ▒   ██▒░ ▓██▓ ░ 
 ░▒▓███▀▒░▓█▒░██▓░ ████▓▒░▒██████▒▒  ▒██▒ ░ 
  ░▒   ▒  ▒ ░░▒░▒░ ▒░▒░▒░ ▒ ▒▓▒ ▒ ░  ▒ ░░   
   ░   ░  ▒ ░▒░ ░  ░ ▒ ▒░ ░ ░▒  ░ ░    ░    
 ░ ░   ░  ░  ░░ ░░ ░ ░ ▒  ░  ░  ░    ░      
       ░  ░  ░  ░    ░ ░        ░           {Colors.RESET}
{Colors.DIM}  AI-Powered Test Generation & Healing{Colors.RESET}
"""
        print(banner_text)

    @classmethod
    def mini_banner(cls):
        """Print a minimal Ghost banner."""
        print()
        print(f"  {Colors.BRIGHT_MAGENTA}{Icons.GHOST} {Colors.BOLD}GHOST{Colors.RESET} {Colors.DIM}│ AI Test Generator{Colors.RESET}")
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # Summary & Stats
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def stats(cls, **kwargs):
        """Print statistics in a nice format."""
        print()
        for key, value in kwargs.items():
            label = key.replace("_", " ").title()
            print(f"  {Colors.DIM}{Icons.DOT}{Colors.RESET} {label}: {Colors.BRIGHT_WHITE}{value}{Colors.RESET}")
        print()

    @classmethod
    def summary(cls, tests_generated: int = 0, tests_passed: int = 0, tests_failed: int = 0, healed: int = 0, duration: float = 0):
        """Print a test run summary."""
        cls.divider("═")
        print(f"  {Colors.BOLD}Summary{Colors.RESET}")
        cls.divider()
        
        # Stats
        print(f"  {Colors.BRIGHT_GREEN}{Icons.SUCCESS}{Colors.RESET} Generated: {Colors.BRIGHT_WHITE}{tests_generated}{Colors.RESET}")
        print(f"  {Colors.BRIGHT_GREEN}{Icons.CHECK}{Colors.RESET} Passed:    {Colors.BRIGHT_WHITE}{tests_passed}{Colors.RESET}")
        if tests_failed > 0:
            print(f"  {Colors.BRIGHT_RED}{Icons.CROSS}{Colors.RESET} Failed:    {Colors.BRIGHT_WHITE}{tests_failed}{Colors.RESET}")
        if healed > 0:
            print(f"  {Colors.BRIGHT_MAGENTA}{Icons.WRENCH}{Colors.RESET} Healed:    {Colors.BRIGHT_WHITE}{healed}{Colors.RESET}")
        print(f"  {Colors.DIM}{Icons.CLOCK}{Colors.RESET} Duration:  {Colors.BRIGHT_WHITE}{duration:.2f}s{Colors.RESET}")
        
        cls.divider("═")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# COUNTDOWN ANIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def countdown(seconds: float, message: str = "Waiting"):
    """Display an animated countdown."""
    start = time.time()
    while True:
        remaining = seconds - (time.time() - start)
        if remaining <= 0:
            break
        
        bar_width = 20
        progress = 1 - (remaining / seconds)
        filled = int(bar_width * progress)
        empty = bar_width - filled
        bar = f"{Colors.CYAN}{'█' * filled}{Colors.DIM}{'░' * empty}{Colors.RESET}"
        
        sys.stdout.write(f"\r{Colors.BRIGHT_BLUE}{Icons.HOURGLASS}{Colors.RESET} {message} │{bar}│ {Colors.BRIGHT_WHITE}{remaining:.1f}s{Colors.RESET} ")
        sys.stdout.flush()
        time.sleep(0.1)
    
    sys.stdout.write(f"\r\033[K")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════════
# TYPING ANIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def type_text(text: str, delay: float = 0.03, color: str = ""):
    """Print text with typewriter effect."""
    for char in text:
        sys.stdout.write(f"{color}{char}{Colors.RESET if color else ''}")
        sys.stdout.flush()
        time.sleep(delay)
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

# Create module-level shortcuts
console = Console()
spinner = GhostSpinner


# Demo function
def demo():
    """Demonstrate all console features."""
    Console.banner()
    
    Console.header("Ghost Demo", "Showcasing beautiful console output")
    
    Console.section("Status Messages")
    Console.success("Operation completed successfully")
    Console.error("Something went wrong")
    Console.warning("Proceed with caution")
    Console.info("Here's some information")
    Console.debug("Debug details here")
    
    Console.section("Ghost Actions")
    Console.ghost("Starting Ghost engine...")
    Console.file_changed("example.py", "modified")
    Console.generating("example.py")
    
    with GhostSpinner("Processing files", style=SpinnerStyle.DOTS, color=Colors.CYAN) as s:
        time.sleep(2)
        s.update("Almost done...")
        time.sleep(1)
    
    Console.test_passed("test_example.py", duration=1.234)
    Console.healing("test_example.py", attempt=1)
    Console.judging("example.py")
    Console.verdict(is_bug_in_code=False)
    
    Console.section("Progress Bar")
    bar = ProgressBar(100, "Generating")
    for i in range(100):
        bar.update(1)
        time.sleep(0.02)
    
    Console.section("Countdown")
    countdown(3, "Rate limit cooldown")
    
    Console.summary(
        tests_generated=5,
        tests_passed=4,
        tests_failed=1,
        healed=1,
        duration=12.34
    )


if __name__ == "__main__":
    demo()
