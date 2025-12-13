"""
Ghost CLI - The main entry point for the Ghost test generator.

Usage:
    ghost init [PATH]           Initialize Ghost in a directory
    ghost watch [PATH]          Watch for file changes and generate tests
    ghost generate <FILE>       Generate tests for a specific file
    ghost config                Configure Ghost settings
    ghost providers             List available AI providers
    ghost version               Show version info
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

import click

# Add app directory to path for imports
APP_DIR = Path(__file__).parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from console import (
    Console, GhostSpinner, SpinnerStyle, Colors, Icons, 
    countdown, ProgressBar
)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI VERSION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

__version__ = "0.2.0"
GHOST_CONFIG_FILE = "ghost.toml"
GHOST_DIR = ".ghost"


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _save_api_key_to_env(env_file: Path, key_name: str, key_value: str):
    """Save an API key to a .env file."""
    # Read existing content
    existing_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_lines = f.readlines()
    
    # Check if key already exists and update it
    key_found = False
    new_lines = []
    for line in existing_lines:
        if line.startswith(f"{key_name}="):
            new_lines.append(f'{key_name}="{key_value}"\n')
            key_found = True
        else:
            new_lines.append(line)
    
    # Add new key if not found
    if not key_found:
        new_lines.append(f'{key_name}="{key_value}"\n')
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    # Add .env to .gitignore if not already there
    gitignore = env_file.parent / ".gitignore"
    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()
        if '.env' not in content:
            with open(gitignore, 'a') as f:
                f.write('\n# Environment variables\n.env\n')
    else:
        with open(gitignore, 'w') as f:
            f.write('# Environment variables\n.env\n')


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLI GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Show version info')
@click.pass_context
def cli(ctx, version):
    """
    👻 Ghost - AI-Powered Test Generation & Healing
    
    Generate, run, and automatically fix your Python tests using AI.
    
    \b
    Quick Start:
      $ ghost init              # Initialize in current directory
      $ ghost watch             # Start watching for changes
      $ ghost generate app.py   # Generate tests for a file
    
    \b
    Configuration:
      $ ghost config            # Interactive configuration
      $ ghost providers         # List available AI providers
    """
    if version:
        show_version()
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        # Show help if no command provided
        Console.mini_banner()
        click.echo(ctx.get_help())


# ═══════════════════════════════════════════════════════════════════════════════
# INIT COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.argument('path', type=click.Path(), default='.')
@click.option('--provider', '-p', type=click.Choice(['groq', 'openai', 'ollama', 'anthropic', 'openrouter', 'auto']), 
              default='auto', help='AI provider to use')
@click.option('--model', '-m', help='Specific model to use')
@click.option('--framework', '-f', type=click.Choice(['pytest', 'unittest']), default='pytest',
              help='Testing framework')
def init(path: str, provider: str, model: Optional[str], framework: str):
    """
    Initialize Ghost in a directory.
    
    Creates ghost.toml configuration and .ghost directory.
    
    \b
    Examples:
      ghost init                    # Initialize in current directory
      ghost init ./myproject        # Initialize in specific directory
      ghost init -p ollama          # Use Ollama (local)
      ghost init -p openai -m gpt-4o-mini
    """
    Console.banner()
    
    target_path = Path(path).resolve()
    
    if not target_path.exists():
        Console.error(f"Path does not exist: {target_path}")
        raise SystemExit(1)
    
    Console.section("Initializing Ghost")
    Console.info(f"Target directory: {target_path}")
    
    # Check for existing installation
    ghost_file = target_path / GHOST_CONFIG_FILE
    if ghost_file.exists():
        if not click.confirm(f"  {Icons.WARNING} ghost.toml already exists. Overwrite?", default=False):
            Console.info("Initialization cancelled")
            return
    
    # Provider selection
    from providers import auto_detect_provider, list_available_providers, PROVIDER_MODELS
    
    if provider == 'auto':
        Console.info("Auto-detecting AI provider...")
        detected = auto_detect_provider()
        
        if detected:
            provider = detected.__class__.__name__.replace('Provider', '').lower()
            Console.success(f"Detected: {provider}")
        else:
            Console.warning("No AI provider detected automatically")
    
    # Always offer to choose provider interactively
    Console.newline()
    Console.section("Provider Setup")
    
    providers_list = ['groq', 'openai', 'ollama', 'anthropic', 'openrouter', 'lmstudio']
    Console.print(f"  {Colors.DIM}Available providers:{Colors.RESET}")
    for i, p in enumerate(providers_list, 1):
        marker = f"{Colors.GREEN}●{Colors.RESET}" if p == provider else f"{Colors.DIM}○{Colors.RESET}"
        desc = {
            'groq': 'Fast & free tier available',
            'openai': 'GPT-4, GPT-4o models',
            'ollama': 'Local models (free, private)',
            'anthropic': 'Claude models',
            'openrouter': 'Multiple providers, one API',
            'lmstudio': 'Local LM Studio server',
        }.get(p, '')
        Console.print(f"    {marker} {i}. {Colors.CYAN}{p}{Colors.RESET} {Colors.DIM}- {desc}{Colors.RESET}")
    
    Console.newline()
    provider = click.prompt(
        f"  {Icons.ARROW} Select provider",
        type=click.Choice(providers_list),
        default=provider if provider != 'auto' else 'groq'
    )
    
    # API Key setup (not needed for local providers)
    api_key = None
    env_var_name = {
        'groq': 'GROQ_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
    }.get(provider)
    
    if env_var_name:
        existing_key = os.environ.get(env_var_name)
        if existing_key:
            masked = existing_key[:8] + "..." + existing_key[-4:] if len(existing_key) > 12 else "***"
            Console.success(f"Found {env_var_name}: {masked}")
            if not click.confirm(f"  {Icons.ARROW} Use existing key?", default=True):
                api_key = click.prompt(
                    f"  {Icons.ARROW} Enter your {provider.upper()} API key",
                    hide_input=True
                )
        else:
            Console.warning(f"{env_var_name} not found in environment")
            api_key = click.prompt(
                f"  {Icons.ARROW} Enter your {provider.upper()} API key",
                hide_input=True
            )
            
            # Offer to save to .env
            if api_key:
                Console.info(f"Your API key will be saved to .env file")
                env_file = target_path / ".env"
                _save_api_key_to_env(env_file, env_var_name, api_key)
                Console.success(f"Saved to {env_file}")
    elif provider in ['ollama', 'lmstudio']:
        Console.info(f"{provider.title()} runs locally - no API key needed")
    
    # Model selection
    Console.newline()
    Console.section("Model Selection")
    
    default_models = {
        'groq': 'llama-3.3-70b-versatile',
        'openai': 'gpt-4o-mini',
        'ollama': 'llama3.2',
        'anthropic': 'claude-3-5-sonnet-20241022',
        'openrouter': 'openrouter/auto',
        'lmstudio': 'local-model',
    }
    
    # Show available models for the provider
    available_models = PROVIDER_MODELS.get(provider, [])
    if available_models:
        Console.print(f"  {Colors.DIM}Popular models for {provider}:{Colors.RESET}")
        for m in available_models[:6]:  # Show top 6
            marker = f"{Colors.GREEN}●{Colors.RESET}" if m == default_models.get(provider) else f"{Colors.DIM}○{Colors.RESET}"
            Console.print(f"    {marker} {Colors.WHITE}{m}{Colors.RESET}")
        Console.newline()
    
    # Ensure model is set (either from CLI arg or prompt)
    if not model:
        model = click.prompt(
            f"  {Icons.ARROW} Enter model name",
            default=default_models.get(provider, 'auto')
        )
    
    # Fallback to ensure model is never None
    model = model or default_models.get(provider, 'auto')
    
    # Create configuration
    with GhostSpinner("Creating configuration", style=SpinnerStyle.DOTS, color=Colors.CYAN) as spinner:
        try:
            _create_ghost_config(target_path, provider, model, framework)
            spinner.stop(message="Configuration created")
        except Exception as e:
            spinner.fail(f"Failed to create config: {e}")
            raise SystemExit(1)
    
    # Create .ghost directory
    ghost_dir = target_path / GHOST_DIR
    if not ghost_dir.exists():
        ghost_dir.mkdir()
        Console.success(f"Created {GHOST_DIR}/ directory")
    
    # Scan project and generate context
    with GhostSpinner("Scanning project files", style=SpinnerStyle.DOTS2, color=Colors.MAGENTA) as spinner:
        try:
            import init as ghost_init_module
            context = ghost_init_module.walk_and_generate_json(str(target_path))
            file_count = len(context)
            spinner.stop(message=f"Scanned {file_count} Python files")
        except Exception as e:
            spinner.fail(f"Failed to scan: {e}")
            raise SystemExit(1)
    
    # Summary
    Console.newline()
    Console.divider("═")
    Console.success("Ghost initialized successfully!", prefix="")
    Console.divider()
    Console.print(f"  {Colors.DIM}Provider:{Colors.RESET}  {Colors.BRIGHT_WHITE}{provider}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}Model:{Colors.RESET}     {Colors.BRIGHT_WHITE}{model}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}Framework:{Colors.RESET} {Colors.BRIGHT_WHITE}{framework}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}Files:{Colors.RESET}     {Colors.BRIGHT_WHITE}{file_count}{Colors.RESET}")
    Console.divider("═")
    Console.newline()
    
    Console.info("Next steps:")
    Console.print(f"  {Colors.CYAN}ghost watch{Colors.RESET}    Start watching for file changes")
    Console.print(f"  {Colors.CYAN}ghost generate <file>{Colors.RESET}  Generate tests for a specific file")
    Console.newline()


def _create_ghost_config(path: Path, provider: str, model: str, framework: str):
    """Create the ghost.toml configuration file."""
    config_content = f'''# Ghost Configuration
# Generated by Ghost v{__version__}

[project]
name = "{path.name}"
language = "python"

[ai]
# AI provider: groq, openai, ollama, anthropic, openrouter, lmstudio, custom
provider = "{provider}"
model = "{model}"

# Optional: Custom API endpoint (for self-hosted or alternative endpoints)
# base_url = "http://localhost:11434/v1"

# Rate limiting (requests per minute) - adjust based on your API tier
rate_limit_rpm = {30 if provider in ['groq', 'anthropic'] else 60 if provider == 'openrouter' else 500}

[scanner]
# Directories to ignore when scanning for Python files
ignore_dirs = [
    ".venv", 
    "venv",
    "node_modules", 
    ".git", 
    "__pycache__", 
    "dist", 
    "build",
    ".ghost", 
    "tests",
    ".tox",
    ".pytest_cache",
    ".mypy_cache"
]

# Specific files to ignore
ignore_files = [
    "setup.py",
    "conftest.py",
    "__init__.py"
]

[tests]
framework = "{framework}"
output_dir = "tests"

# Healing: automatically fix failing tests
auto_heal = true
max_heal_attempts = 3

# Judge: consult AI to determine if bug is in code or test
use_judge = true

[watcher]
# Debounce time in seconds (ignore rapid consecutive saves)
debounce_seconds = 15

# File patterns to watch
patterns = ["*.py"]
'''
    
    config_path = path / GHOST_CONFIG_FILE
    with open(config_path, 'w') as f:
        f.write(config_content)


# ═══════════════════════════════════════════════════════════════════════════════
# WATCH COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
def watch(path: str, verbose: bool):
    """
    Watch for file changes and generate tests automatically.
    
    Monitors the specified directory for Python file changes and
    automatically generates/updates tests.
    
    \b
    Examples:
      ghost watch              # Watch current directory
      ghost watch ./src        # Watch specific directory
      ghost watch -V           # Verbose mode
    """
    Console.banner()
    
    target_path = Path(path).resolve()
    
    # Check for ghost.toml
    ghost_file = target_path / GHOST_CONFIG_FILE
    if not ghost_file.exists():
        Console.warning("ghost.toml not found. Running 'ghost init' first...")
        Console.newline()
        ctx = click.get_current_context()
        ctx.invoke(init, path=str(target_path))
    
    Console.section("Starting File Watcher")
    
    # Import and start watcher from main module
    try:
        import main as ghost_main
        
        # Setup logging
        if verbose:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            ghost_main.logging_setup()
        
        ghost_main.start_watching(target_path)
        
    except KeyboardInterrupt:
        Console.newline()
        Console.info("Stopping watcher...")
        Console.success("Ghost stopped. Goodbye! 👻")
    except Exception as e:
        Console.error(f"Watcher error: {e}")
        raise SystemExit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATE COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output test file path')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing test file')
def generate(file: str, output: Optional[str], force: bool):
    """
    Generate tests for a specific file.
    
    \b
    Examples:
      ghost generate app.py
      ghost generate src/utils.py -o tests/test_utils.py
      ghost generate app.py --force
    """
    Console.mini_banner()
    
    file_path = Path(file).resolve()
    
    if not file_path.suffix == '.py':
        Console.error("Only Python files are supported")
        raise SystemExit(1)
    
    # Find project root (where ghost.toml is)
    project_root = _find_project_root(file_path)
    if not project_root:
        Console.error("Could not find ghost.toml. Run 'ghost init' first.")
        raise SystemExit(1)
    
    Console.generating(file_path.name)
    
    # Determine output path
    if output:
        test_path = Path(output).resolve()
    else:
        tests_dir = project_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        test_path = tests_dir / f"test_{file_path.name}"
    
    # Check if test file exists
    if test_path.exists() and not force:
        if not click.confirm(f"  {Icons.WARNING} Test file exists. Overwrite?", default=False):
            Console.info("Generation cancelled")
            return
    
    # Read source file
    with open(file_path, 'r') as f:
        source_code = f.read()
    
    # Generate tests
    with GhostSpinner("Generating tests with AI", style=SpinnerStyle.DOTS, color=Colors.CYAN) as spinner:
        try:
            from chat import TestGenerator
            from config import get_config
            
            config = get_config(project_root)
            generator = TestGenerator(config=config)
            
            test_code = generator.get_test_code(
                source_code=source_code,
                source_path=str(project_root),
                filename=file_path.name
            )
            
            # Write test file
            with open(test_path, 'w') as f:
                f.write(test_code)
            
            spinner.stop(message=f"Tests written to {test_path.name}")
            
        except Exception as e:
            spinner.fail(f"Generation failed: {e}")
            raise SystemExit(1)
    
    # Run the tests
    Console.info("Running generated tests...")
    with GhostSpinner("Running pytest", style=SpinnerStyle.DOTS2, color=Colors.YELLOW) as spinner:
        try:
            from runner import run_test
            return_code, stdout, stderr = run_test(str(test_path))
            
            if return_code == 0:
                spinner.stop(message="All tests passed!")
                Console.test_passed(test_path.name)
            else:
                spinner.fail("Some tests failed")
                Console.test_failed(test_path.name)
                Console.info("Run with --force to regenerate")
                
        except Exception as e:
            spinner.fail(f"Test run failed: {e}")
    
    Console.newline()
    Console.success(f"Test file: {test_path}")


def _find_project_root(start_path: Path) -> Optional[Path]:
    """Find the project root by looking for ghost.toml."""
    current = start_path if start_path.is_dir() else start_path.parent
    
    while current != current.parent:
        if (current / GHOST_CONFIG_FILE).exists():
            return current
        current = current.parent
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.option('--show', '-s', is_flag=True, help='Show current configuration')
@click.option('--set-provider', type=click.Choice(['groq', 'openai', 'ollama', 'anthropic', 'openrouter']),
              help='Set AI provider')
@click.option('--set-model', help='Set AI model')
@click.option('--set-api-key', help='Set API key (stored in environment)')
def config(show: bool, set_provider: Optional[str], set_model: Optional[str], set_api_key: Optional[str]):
    """
    Configure Ghost settings.
    
    \b
    Examples:
      ghost config --show
      ghost config --set-provider openai
      ghost config --set-model gpt-4o-mini
    """
    Console.mini_banner()
    
    project_root = _find_project_root(Path.cwd())
    
    if show or (not set_provider and not set_model and not set_api_key):
        _show_config(project_root)
        return
    
    if not project_root:
        Console.error("No ghost.toml found. Run 'ghost init' first.")
        raise SystemExit(1)
    
    # Update configuration
    if set_provider or set_model:
        Console.info("Updating configuration...")
        _update_config(project_root, provider=set_provider, model=set_model)
        Console.success("Configuration updated")
    
    if set_api_key:
        Console.warning("API keys should be set as environment variables:")
        Console.print(f"  export GROQ_API_KEY='{set_api_key}'")
        Console.print(f"  export OPENAI_API_KEY='{set_api_key}'")
        Console.info("Add to your .bashrc or .zshrc for persistence")


def _show_config(project_root: Optional[Path]):
    """Display current configuration."""
    Console.section("Current Configuration")
    
    if not project_root:
        Console.warning("No project found in current directory")
        Console.info("Run 'ghost init' to create a new project")
        return
    
    import tomllib
    
    config_path = project_root / GHOST_CONFIG_FILE
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
    
    Console.print(f"  {Colors.DIM}Project:{Colors.RESET}    {Colors.BRIGHT_WHITE}{project_root.name}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}Config:{Colors.RESET}     {Colors.BRIGHT_WHITE}{config_path}{Colors.RESET}")
    Console.newline()
    
    ai_config = config.get('ai', {})
    Console.print(f"  {Colors.CYAN}AI Settings:{Colors.RESET}")
    Console.print(f"    Provider:   {ai_config.get('provider', 'not set')}")
    Console.print(f"    Model:      {ai_config.get('model', 'not set')}")
    Console.print(f"    Rate Limit: {ai_config.get('rate_limit_rpm', 30)} RPM")
    Console.newline()
    
    test_config = config.get('tests', {})
    Console.print(f"  {Colors.CYAN}Test Settings:{Colors.RESET}")
    Console.print(f"    Framework:  {test_config.get('framework', 'pytest')}")
    Console.print(f"    Output Dir: {test_config.get('output_dir', 'tests')}")
    Console.print(f"    Auto Heal:  {test_config.get('auto_heal', True)}")


def _update_config(project_root: Path, provider: Optional[str] = None, model: Optional[str] = None):
    """Update the ghost.toml configuration."""
    config_path = project_root / GHOST_CONFIG_FILE
    
    # Read current config
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Update provider
    if provider:
        import re
        content = re.sub(
            r'provider\s*=\s*"[^"]*"',
            f'provider = "{provider}"',
            content
        )
    
    # Update model
    if model:
        import re
        content = re.sub(
            r'model\s*=\s*"[^"]*"',
            f'model = "{model}"',
            content
        )
    
    # Write back
    with open(config_path, 'w') as f:
        f.write(content)


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDERS COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.option('--check', '-c', is_flag=True, help='Check connectivity to providers')
def providers(check: bool):
    """
    List available AI providers and their status.
    
    \b
    Examples:
      ghost providers           # List all providers
      ghost providers --check   # Check connectivity
    """
    Console.mini_banner()
    Console.section("Available AI Providers")
    
    from providers import list_available_providers, POPULAR_MODELS
    
    status = list_available_providers()
    
    # Local providers
    Console.print(f"\n  {Colors.BOLD}Local (Free){Colors.RESET}")
    _print_provider_status("Ollama", status.get("ollama", False), "ollama serve", "http://localhost:11434")
    _print_provider_status("LM Studio", status.get("lmstudio", False), "Start LM Studio", "http://localhost:1234")
    
    # Cloud providers
    Console.print(f"\n  {Colors.BOLD}Cloud APIs{Colors.RESET}")
    _print_provider_status("Groq", status.get("groq", False), "GROQ_API_KEY", "Free tier: 30 RPM")
    _print_provider_status("OpenAI", status.get("openai", False), "OPENAI_API_KEY", "Paid")
    _print_provider_status("Anthropic", status.get("anthropic", False), "ANTHROPIC_API_KEY", "Paid")
    _print_provider_status("OpenRouter", status.get("openrouter", False), "OPENROUTER_API_KEY", "Pay per use")
    
    Console.newline()
    Console.section("Popular Models")
    
    Console.print(f"\n  {Colors.DIM}{'Model':<25} {'Provider':<12} {'Description'}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}{'─' * 70}{Colors.RESET}")
    
    for name, model in list(POPULAR_MODELS.items())[:10]:
        provider = model.provider.value
        Console.print(f"  {Colors.BRIGHT_WHITE}{name:<25}{Colors.RESET} {provider:<12} {Colors.DIM}{model.description}{Colors.RESET}")
    
    Console.newline()
    Console.info("Set up a provider:")
    Console.print(f"  {Colors.CYAN}# For Groq (recommended - free & fast):{Colors.RESET}")
    Console.print(f"  export GROQ_API_KEY='your-key-here'")
    Console.print(f"\n  {Colors.CYAN}# For local Ollama:{Colors.RESET}")
    Console.print(f"  ollama serve  # Start server")
    Console.print(f"  ollama pull llama3.2  # Download model")
    Console.newline()


def _print_provider_status(name: str, available: bool, setup_hint: str, note: str):
    """Print provider status line."""
    if available:
        status = f"{Colors.BRIGHT_GREEN}{Icons.SUCCESS}{Colors.RESET}"
        status_text = f"{Colors.GREEN}Available{Colors.RESET}"
    else:
        status = f"{Colors.DIM}{Icons.CIRCLE}{Colors.RESET}"
        status_text = f"{Colors.DIM}Not configured{Colors.RESET}"
    
    Console.print(f"    {status} {name:<12} {status_text:<20} {Colors.DIM}{note}{Colors.RESET}")


# ═══════════════════════════════════════════════════════════════════════════════
# VERSION COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
def version():
    """Show version information."""
    show_version()


def show_version():
    """Display version info."""
    Console.print(f"\n  {Colors.BRIGHT_MAGENTA}{Icons.GHOST} Ghost{Colors.RESET} {Colors.BRIGHT_WHITE}v{__version__}{Colors.RESET}")
    Console.print(f"  {Colors.DIM}AI-Powered Test Generation & Healing{Colors.RESET}")
    Console.print(f"  {Colors.DIM}Python {sys.version.split()[0]}{Colors.RESET}")
    Console.newline()


# ═══════════════════════════════════════════════════════════════════════════════
# DOCTOR COMMAND (Health Check)
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
def doctor():
    """
    Check Ghost installation and dependencies.
    
    Verifies that all required components are properly installed and configured.
    """
    Console.mini_banner()
    Console.section("Health Check")
    
    all_ok = True
    
    # Check Python version
    import sys
    py_version = sys.version_info
    if py_version >= (3, 10):
        Console.success(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        Console.error(f"Python {py_version.major}.{py_version.minor} (3.10+ required)")
        all_ok = False
    
    # Check required packages
    packages = ['groq', 'openai', 'watchdog', 'pytest', 'click']
    for pkg in packages:
        try:
            __import__(pkg)
            Console.success(f"{pkg} installed")
        except ImportError:
            Console.error(f"{pkg} not installed")
            all_ok = False
    
    # Check for ghost.toml
    project_root = _find_project_root(Path.cwd())
    if project_root:
        Console.success(f"Project found: {project_root.name}")
    else:
        Console.warning("No ghost.toml in current directory")
    
    # Check AI providers
    from providers import list_available_providers
    status = list_available_providers()
    
    available_providers = [k for k, v in status.items() if v]
    if available_providers:
        Console.success(f"AI providers: {', '.join(available_providers)}")
    else:
        Console.warning("No AI providers configured")
        all_ok = False
    
    Console.newline()
    if all_ok:
        Console.success("All checks passed! Ghost is ready to use.", prefix="")
    else:
        Console.warning("Some issues found. Run 'ghost init' to set up.")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        Console.newline()
        Console.info("Interrupted. Goodbye! 👻")
        sys.exit(0)
    except Exception as e:
        Console.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
