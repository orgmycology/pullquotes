# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run script: `python pull_quotes.py input_markdown_file.md`
- No formal tests implemented - manual verification required

## Code Style Guidelines
- PEP 8 style conventions
- Imports: standard library first, followed by third-party, then local modules
- DocStrings: use triple-quoted """strings""" for function documentation
- Error handling: Use try/except blocks with specific exception types
- Naming: snake_case for variables/functions, CamelCase for classes
- Function parameters: document with clear docstrings
- Type hints: not currently used but could be added for improved code clarity
- String formatting: Use f-strings for string interpolation
- Dependencies: pandoc required for .docx conversion