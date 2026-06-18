import json
import logging
import re
import tomllib
from datetime import datetime
from typing import Optional

from ghost.config import GhostConfig, get_api_key, get_config
from ghost.providers import BaseProvider, get_provider
from ghost.rate_limiter import RateLimiter
from ghost.runner import get_project_tree


class TestGenerator:
    """AI-powered test generator supporting multiple providers.

    Supports: Groq, OpenAI, Anthropic, Ollama, OpenRouter, LM Studio, and custom endpoints.
    """

    __test__ = False

    def __init__(self, api_key: Optional[str] = None, config: Optional[GhostConfig] = None):
        """
        Initialize the test generator.

        Args:
            api_key: Optional API key (overrides config/environment)
            config: Optional GhostConfig instance
        """
        self.config = config or get_config()
        self._provider: Optional[BaseProvider] = None
        self._api_key = api_key

        # Set rate limit based on config
        RateLimiter.set_interval(60.0 / max(self.config.ai.rate_limit_rpm, 1))

    @property
    def provider(self) -> BaseProvider:
        """Lazy-load the AI provider."""
        if self._provider is None:
            provider_name = self.config.ai.provider.lower()
            api_key = self._api_key or self.config.ai.api_key or get_api_key(provider_name)

            kwargs = {}
            if api_key:
                kwargs["api_key"] = api_key
            if self.config.ai.base_url:
                kwargs["base_url"] = self.config.ai.base_url

            self._provider = get_provider(provider_name, **kwargs)

        return self._provider

    def _call_api(self, messages: list, temperature: float = 0.1) -> str:
        """
        Call the AI API with automatic provider detection.
        """
        model = self.config.ai.model
        return self.provider.chat(messages, model=model, temperature=temperature)

    def get_test_code(
        self,
        source_code,
        source_path=".",
        filename="",
        testing=False,
        test_file_path="",
        errors=None,
    ):
        if testing:
            prompt = self.create_prompt_test(
                source_code, source_path, filename, test_file_path, errors
            )
        else:
            prompt = self.create_prompt(source_code, source_path, filename)
        logging.debug("Prompt generated!")

        response = self._call_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are a code generator. Output only valid Python code. No markdown, no explanations.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        cleaned_code = self.clean_llm_response(response)
        return cleaned_code

    def create_prompt(self, source_code, source_path, filename):
        try:
            logging.debug("Creating prompt...")
            ghost_path = f"{source_path}/ghost.toml"
            conf = tomllib.load(open(ghost_path, "rb"))
            framework = conf.get("tests", {}).get("framework", "pytest")
            context_source = f"{source_path}/.ghost/context.json"
            with open(context_source, "r") as f:
                global_context = json.load(f)
            now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            project_structure = get_project_tree(source_path)
            return f"""
            ROLE:
            You are a deterministic, automated QA agent specialized in Python test generation.
            This code you generate will reside in the {source_path}/tests/test_{filename}.
            THis is from the source file {filename}.
            PRIMARY OBJECTIVE:
            Generate a COMPLETE, EXECUTABLE Python test file using the specified testing framework: {framework}.
            CONTEXT:
                - You are working in a specific project structure.
                - You must verify imports based on the PROJECT MAP provided.
                
                {project_structure}
            The output must be immediately runnable without modification.
            1. You MUST include this code block at the very top of the test file, before any other imports:

                import sys
                import os
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                
                2. After that block, import the module normally (e.g., 'from app import main').
                3. Do NOT use relative imports (like 'from ..app import').
            ABSOLUTE OUTPUT CONSTRAINTS (NON-NEGOTIABLE):
            1. Output ONLY valid Python source code.
            2. Do NOT include Markdown, backticks, explanations, annotations, or conversational text.
            3. The output MUST be directly saveable as a .py file.
            4. The output MUST contain an explicit import of the testing framework:
               import {framework}
            5. Do NOT emit placeholder code, TODOs, or pseudocode.
            6. Do NOT modify, rewrite, or inline the source code under test.
            7. Do NOT reference files, modules, or symbols not present in GLOBAL CONTEXT.
            8. Tests MUST be deterministic, repeatable, and isolated.
    
            FILE HEADER (MANDATORY):
            The very first lines of the file MUST be a Python comment in EXACTLY this format:
            # Generated at: {now} | Source: {source_path}
    
            TEST CONSTRUCTION RULES:
            - Use the idiomatic style required by {framework}.
            - If {framework} supports fixtures, setup/teardown, or parameterization, use them where appropriate.
            - If {framework} requires class-based tests, use them correctly.
            - Follow naming conventions required for automatic test discovery by {framework}.
            - Assert behavior explicitly; never rely on implicit truthiness.
            - Validate return values, side effects, and raised exceptions.
            - Cover:
              • Standard / expected behavior
              • Edge cases
              • Error or failure paths (invalid input, exceptions)
            - Write separate tests for each public function or class.
    
            MOCKING & ISOLATION REQUIREMENTS:
            - Mock ALL external dependencies, including but not limited to:
              • File system access
              • Network or HTTP calls
              • Environment variables
              • Time, randomness, UUIDs
              • Subprocesses or OS interactions
            - Use the most appropriate mocking mechanism compatible with {framework}
              (e.g., monkeypatch, unittest.mock, fixtures, stubs).
    
            IMPORT RULES:
            - Import ONLY from:
              • Python standard library
              • {framework}
              • Modules listed in GLOBAL CONTEXT
            - Avoid wildcard imports.
    
            GLOBAL CONTEXT (AVAILABLE MODULES / FILES):
            {json.dumps(global_context, indent=2)}
    
            SOURCE CODE UNDER TEST:
            {source_code}
    
            FINAL ENFORCEMENT:
            Return ONLY raw Python code.
            Any additional text, formatting, or explanation makes the response invalid.
            """
        except Exception as e:
            logging.error("Error creating prompt: %s", e)
            raise

    def create_prompt_test(self, source_code, source_path, filename, test_file_path, errors):
        ghost_path = f"{source_path}/ghost.toml"
        conf = tomllib.load(open(ghost_path, "rb"))
        framework = conf.get("tests", {}).get("framework", "pytest")
        context_source = f"{source_path}/.ghost/context.json"
        with open(context_source, "r") as f:
            global_context = json.load(f)
        with open(test_file_path, "r") as f:
            existing_code = f.read()
        project_structure = get_project_tree(source_path)
        return f"""
                    You are an expert Python test engineer. Your task is to fix errors in a previously generated test file.
                    1. You MUST include this code block at the very top of the test file, before any other imports:

                    import sys
                    import os
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                    
                    2. After that block, import the module normally (e.g., 'from app import main').
                    3. Do NOT use relative imports (like 'from ..app import').
                CRITICAL: Output ONLY valid Python code. No markdown, no backticks, no explanations.
                
                ## Context
                - Test file: {test_file_path}
                - Source file: {filename}
                - Framework: {framework}
                
                ## Project Structure
                {project_structure}
                
                ## Available Modules
                {json.dumps(global_context, indent=2)}
                
                ## Previous Code (with errors)
                {existing_code}
                
                ## Errors to Fix
                {errors}
                
                ## Requirements
                
                ### Code Quality
                - Fix ALL syntax errors, import errors, and runtime issues
                - Ensure all imports are valid based on project structure
                - Use correct {framework} syntax and conventions
                - Follow {framework}'s test discovery naming patterns
                
                ### Import Rules
                - Import {framework} explicitly at the top
                - Only import from: standard library, {framework}, or modules in project structure
                - Verify all imports against the project structure above
                - No wildcard imports
                
                ### Test Structure
                - Keep all existing test logic unless it's the source of errors
                - Maintain test coverage for: normal cases, edge cases, error conditions
                - Use {framework}-idiomatic patterns (fixtures, parametrization, etc.)
                - Each test must be independent and deterministic
                
                ### Mocking
                - Mock external dependencies: filesystem, network, time, random, environment
                - Use {framework}-compatible mocking (monkeypatch, unittest.mock, etc.)
                
                OUTPUT: Return only the corrected Python code, ready to save as {test_file_path}
                """

    def clean_llm_response(self, raw_text):
        """
        Removes markdown backticks, conversational filler, and extracts just the Python code.
        """
        # Pattern to find code inside ```python ... ``` blocks
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_text, re.DOTALL)

        if match:
            # Return the content inside the backticks
            return match.group(1).strip()

        # Fallback: If no backticks, it might be raw code already.
        # Just strip whitespace and return.
        return raw_text.strip()

    def consult_the_judge(self, source_code, source_path, filename, test_file_path, errors):
        context_source = f"{source_path}/.ghost/context.json"
        with open(context_source, "r") as f:
            global_context = json.load(f)
        project_structure = get_project_tree(source_path)
        with open(test_file_path, "r") as f:
            test_code = f.read()
        prompt = f"""
        You are a code defect analyzer. A unit test failed with an assertion error.
        Determine the root cause: is the source code buggy, or is the test incorrect?
        
        ## Context
        - Test file: {test_file_path}
        - Source file: {filename}
        
        ## Project Structure
        {project_structure}
        
        ## Available Modules
        {json.dumps(global_context, indent=2)}
        
        ## Source Code Being Tested
        {source_code}
        
        ## Failed Test Code
        {test_code}
        
        ## Error Output
        {errors}
        
        ## Analysis Task
        
        Compare the source code logic against the test expectations:
        
        **If source code has a defect** (wrong logic, incorrect calculation, bug in implementation):
        → Output: BUG_IN_CODE
        
        **If source code is correct** but test has wrong expectations or flawed assertions:
        → Output: FIX_TEST
        
        ## Critical Rules
        1. Analyze the actual logic and expected behavior carefully
        2. Consider edge cases and business logic intent
        3. Check if error stems from code implementation vs test assumptions
        4. Output EXACTLY one of these strings: "BUG_IN_CODE" or "FIX_TEST"
        5. NO explanations, NO additional text, NO punctuation
        
        OUTPUT: OUTPUT ONLY ONE OF THESE TWO STRINGS. NO EXPLANATION.
        """
        response = self._call_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are a code defect analyzer. Output only one of these two strings: 'BUG_IN_CODE' or 'FIX_TEST'. No other text.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        # Clean and validate response
        ans = response.strip().upper()
        if "BUG_IN_CODE" in ans:
            return "BUG_IN_CODE"
        elif "FIX_TEST" in ans:
            return "FIX_TEST"
        return ans
