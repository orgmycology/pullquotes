# Pull Quotes

A command-line tool for extracting and personalizing quotes from markdown documents.

## Overview

Pull Quotes extracts attributed quotes from markdown documents and creates personalized versions where only quotes from a specific person are visible while others are redacted. This is useful for reviewing interview transcripts or creating personalized document versions for document approvals.

## Installation

### Requirements
- Python 3.6+
- pandoc (optional, for DOCX output)

### Installation from GitHub

```bash
pip install git+https://github.com/orgmycology/pullquotes.git
```

After installation, you can use the `pullquotes` command:

```bash
pullquotes input_file.md [options]
```

### Manual Installation

Alternatively, you can clone the repository and run the script directly:

```bash
git clone https://github.com/orgmycology/pullquotes.git
cd pullquotes
python pull_quotes.py input_file.md [options]
```

## Usage

After installation:
```
pullquotes INPUT_FILE [OPTIONS]
```

Or run the script directly:
```
python pull_quotes.py INPUT_FILE [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `INPUT_FILE` | The markdown file to process (required) |

### Options

| Option | Description |
|--------|-------------|
| `--fix` | Automatically fix suspected quotes with improper formatting |
| `--keep-names` | Keep quotee names in redacted quotes (default is to drop names) |
| `--test` | Test mode: only check for quotes and report findings without creating output files |
| `--help` or `-h` | Display help information |

### Examples

Basic usage:
```
pullquotes interview.md
```

Fix improperly formatted quotes:
```
pullquotes interview.md --fix
```

Keep attribution names in redacted quotes:
```
pullquotes interview.md --keep-names
```

Use multiple options:
```
pullquotes interview.md --fix --keep-names
```

Test mode (validate quotes without creating files):
```
pullquotes interview.md --test
```

The test mode will exit with:
- Code 0 (success) if all quotes are properly formatted
- Code 1 (error) if quotes need formatting

Fix and test mode (fix quotes and validate without creating files):
```
pullquotes interview.md --test --fix
```

## Quote Format

Quotes must be in the format: `"quote text" (Person)` or with a dash: `"quote text" - (Person)`.

The script also supports various fancy/curly quotes from word processors and single quotes:
- `"quote text" (Person)`
- `'quote text' (Person)`
- `"quote text" - (Person)`
- `"quote text" — (Person)`

## Output

For each unique attribution (person), the script creates:
1. A markdown file with the person's quotes preserved and others redacted
2. A docx version of that file (if pandoc is installed)

### Redacted Quote Format

By default, quotes from other people are redacted and their names are removed:
```
"[QUOTE REDACTED]"
```

With the `--keep-names` option, quotes are redacted but names are preserved:
```
"[QUOTE REDACTED FOR REVIEW]" (Person)
```

## Features

### Quote Detection

- Extracts quotes with attributions in standard format
- Handles both single and double quotes
- Normalizes various fancy/curly quotes from word processors
- Supports standalone quotes on their own lines
- Processes multi-line blockquotes with attributions

### Quote Formatting Detection

The script can detect quotes that aren't properly formatted and suggest fixes:
- Quotes without proper attribution format
- Quotes spread across multiple lines
- Blockquote-style quotes
- Quotes with attribution on the following line

### Auto-Fix Mode

With the `--fix` option, the script attempts to automatically correct improperly formatted quotes:
- Combines quotes and attributions on separate lines
- Reformats attribution to proper format
- Reanalyzes the file after fixing

### Test Mode

The `--test` option allows validating documents without generating output files:
- Only checks for quotes and reports findings
- Does not create personalized markdown or docx files
- Returns exit code 0 if all quotes are properly formatted
- Returns exit code 1 if quotes need formatting

This is especially useful for:
- CI/CD pipelines to validate document formatting
- Batch processing multiple files to identify which need attention
- Pre-commit hooks to ensure proper quote formatting

## Examples of Supported Quote Formats

1. Standard quotes: `"This is a quote" (Person)`
2. Quotes with dashes: `"This is a quote" - (Person)`
3. Quotes with em dashes: `"This is a quote" — (Person)`
4. Single quotes: `'This is a quote' (Person)`
5. Curly quotes from word processors: `"This is a quote" (Person)`
6. Standalone quotes (with attribution on next line - auto-fixed with `--fix`):
   ```
   "This is a quote"
   (Person)
   ```
7. Blockquotes (with attribution after - auto-fixed with `--fix`):
   ```
   > This is a blockquote
   > with multiple lines
   Person
   ```

## License

MIT