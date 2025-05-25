#!/usr/bin/env python3
"""
Pull Quotes - A tool for extracting and personalizing quotes from markdown documents.

Usage:
  python pull_quotes.py input_markdown_file.md [--fix] [--keep-names] [--test]

Arguments:
  input_markdown_file.md  - The markdown file to process
  --fix                   - Optional flag to automatically fix suspected quotes
  --keep-names            - Optional flag to keep quotee names in redacted quotes
                           (default is to drop the name from redacted quotes)
  --test                  - Test mode: Only check for quotes and report findings
                           without generating output files

Description:
  This script extracts quotes with attributions from a markdown file and creates
  personalized versions where only quotes from a specific person are visible.
  
  For each unique attribution, it creates:
  1. A markdown file with other quotes redacted
  2. A docx version of that file (requires pandoc)
  
  By default, quotes from other people are redacted and their names are removed.
  If --keep-names is specified, the names are kept in the redacted quotes.
  
  The --test option allows checking files for proper quote formatting without
  generating any output files, which is useful for batch validation.
  
  Quotes must be in the format: "quote text" (Person)
  The script can detect and suggest fixes for quotes that don't match this format.
"""
import re
import os
import subprocess
import sys
from collections import defaultdict

def normalize_quotes(text):
    """Replace various quote styles with straight ASCII quotes.
    
    Handles:
    - Curly/smart quotes (", ", ", ")
    - Single curly quotes (', ', ', ')
    - Various Unicode quote characters
    - Word processor "fancy" quotes
    """
    # Replace double curly/smart quotes with straight quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('″', '"')  # Unicode double prime
    text = text.replace('❝', '"').replace('❞', '"')  # Unicode double quotes
    text = text.replace('〝', '"').replace('〞', '"')  # CJK corner quotes
    text = text.replace('„', '"').replace('‟', '"')  # Double low-9/high-rev-9 quotes
    
    # Replace single curly quotes with straight single quotes
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('′', "'")  # Unicode prime
    text = text.replace('‚', "'").replace('‛', "'")  # Single low-9/high-rev-9 quotes
    text = text.replace('❛', "'").replace('❜', "'")  # Unicode single quotes
    
    # Special cases for Word processors
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # Unicode LEFT/RIGHT DOUBLE QUOTATION MARK
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # Unicode LEFT/RIGHT SINGLE QUOTATION MARK
    
    return text

def extract_quotes(markdown_text):
    """Extract quotes and their attributions from the markdown text."""
    # Normalize quotes first
    markdown_text = normalize_quotes(markdown_text)
    
    # Pattern to match quotes with attributions in parentheses
    # Handles various dash formats or no dash at all before the attribution
    # Looks for: opening quote, any text (non-greedy), ending with optional dash and (Name)
    double_quote_pattern = r'"([^"]+)"\s*(?:[-–—]\s*)?\(([^)]+)\)'
    
    # Also handle single quotes
    single_quote_pattern = r'\'([^\']+)\'\s*(?:[-–—]\s*)?\(([^)]+)\)'
    
    quotes = []
    suspected_quotes = []
    
    # Find standard double-quoted quotes
    for match in re.finditer(double_quote_pattern, markdown_text):
        quote_text = match.group(1)
        attribution = match.group(2)
        start_pos = match.start()
        end_pos = match.end()
        quotes.append({
            'text': quote_text,
            'attribution': attribution,
            'start': start_pos,
            'end': end_pos,
            'full_match': match.group(0)
        })
    
    # Find single-quoted quotes
    for match in re.finditer(single_quote_pattern, markdown_text):
        quote_text = match.group(1)
        attribution = match.group(2)
        start_pos = match.start()
        end_pos = match.end()
        quotes.append({
            'text': quote_text,
            'attribution': attribution,
            'start': start_pos,
            'end': end_pos,
            'full_match': match.group(0)
        })
        
    # Process by lines to find standalone quotes and suspected quotes
    lines = markdown_text.split('\n')
    
    # Calculate line positions in the original text
    line_positions = []
    pos = 0
    for line in lines:
        line_positions.append(pos)
        pos += len(line) + 1  # +1 for the newline character
        
    for i, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check for lines that are just quotes without attribution (double or single quotes)
        if ((line.strip().startswith('"') and line.strip().endswith('"')) or 
            (line.strip().startswith("'") and line.strip().endswith("'"))) and '(' not in line:
            line_start = line_positions[i]
            # Check if this line is already part of an identified quote
            already_matched = any(
                q['start'] <= line_start and q['end'] >= line_start + len(line)
                for q in quotes
            )
            
            if not already_matched:
                # Look at the next line for attribution
                if i+1 < len(lines):
                    next_line = lines[i+1].strip()
                    # If next line looks like an attribution
                    if re.match(r'^\s*\(([^)]+)\)', next_line) or re.match(r'^[-–—]?\s*\w+', next_line):
                        attribution = next_line.lstrip('-–— ')
                        if attribution.startswith('(') and attribution.endswith(')'):
                            attribution = attribution[1:-1]  # Remove parentheses
                        else:
                            # For attribution lines that don't have parentheses
                            attribution = attribution
                            
                        suspected_quotes.append({
                            'line_number': i+1, 
                            'quote_text': line.strip(),
                            'attribution_line': next_line,
                            'suggestion': f'{line.strip()} ({attribution})'
                        })
        
        # Look for blockquote-style quotes (>)
        elif line.strip().startswith('>'):
            # If it's the start of a blockquote, check for multiple lines
            blockquote_text = line.lstrip('> ').strip()
            blockquote_lines = [blockquote_text]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('>'):
                blockquote_lines.append(lines[j].lstrip('> ').strip())
                j += 1
                
            # Only process if we have a complete blockquote and we're at the first line of the blockquote
            # This prevents duplicate processing of the same blockquote
            if blockquote_lines and line.strip().startswith('>') and (i == 0 or not lines[i-1].strip().startswith('>')):
                # Combine the blockquote lines into a single quote
                full_quote = ' '.join(blockquote_lines)
                
                # Skip blockquotes that are already properly formatted with quotes and attribution
                skip = False
                if full_quote.startswith('"') and full_quote.endswith('"') and '(' in full_quote:
                    # Check if this is already a properly formatted quote
                    if re.search(r'"[^"]+".*\([^)]+\)', full_quote):
                        skip = True
                
                if not skip:
                    # If there's an attribution after the blockquote
                    if j < len(lines) and not lines[j].strip().startswith('>'):
                        attribution_line = lines[j].strip()
                        if attribution_line and not attribution_line.startswith('#') and not attribution_line.startswith('*'):
                            # Skip if this is a section heading or something structural
                            if len(attribution_line) < 100 and not re.match(r'^#{1,6}\s', attribution_line):
                                # If it doesn't have quotes, add double quotes (our standard format)
                                # Check if it has single quotes - if so, convert to double quotes
                                if full_quote.startswith("'") and full_quote.endswith("'"):
                                    full_quote = f'"{full_quote[1:-1]}"'
                                # If no quotes at all, add double quotes
                                elif not (full_quote.startswith('"') or full_quote.startswith("'")):
                                    full_quote = f'"{full_quote}"'
                                # Ensure it ends with double quotes if it starts with them
                                if full_quote.startswith('"') and not full_quote.endswith('"'):
                                    full_quote = f'{full_quote}"'
                                
                                # Extract attribution - prioritize finding (Name) format
                                attribution = None
                                attribution_match = re.search(r'\(([^)]+)\)', attribution_line)
                                if attribution_match:
                                    attribution = attribution_match.group(1)
                                else:
                                    # Try to use the first word(s) as attribution if no parentheses
                                    words = attribution_line.lstrip('-–— ').split()
                                    if words and not words[0].startswith(('#', '*', '-')):
                                        # Use first word or name as attribution
                                        attribution = words[0]
                                        # If it looks like a proper name (capitalized), include more words
                                        if words[0][0].isupper() and len(words) > 1:
                                            attribution = ' '.join(words[:2])  # Use first two words
                                
                                # Only add as suspected if we could extract an attribution
                                if attribution:
                                    line_pos = line_positions[j]
                                    
                                    # Check if this suspected quote overlaps with any existing quote
                                    overlaps = False
                                    for q in quotes:
                                        if (q['start'] <= line_pos and q['end'] >= line_pos):
                                            overlaps = True
                                            break
                                    
                                    if not overlaps:
                                        suspected_quotes.append({
                                            'line_number': j,
                                            'quote_text': full_quote,
                                            'attribution_line': attribution_line,
                                            'suggestion': f'{full_quote} ({attribution})'
                                        })
    
    return quotes, suspected_quotes

def create_personalized_files(input_file, quotes, keep_names=False):
    """Create personalized markdown files for each unique attribution.
    
    Args:
        input_file: Path to the input markdown file
        quotes: List of extracted quotes
        keep_names: If True, keep the names of quotees in redacted quotes
                   If False (default), remove names from redacted quotes
    """
    # Get the base filename without extension
    base_name = os.path.splitext(input_file)[0]
    
    # Group quotes by attribution
    attributions = set(quote['attribution'] for quote in quotes)
    
    # Read the original file content
    with open(input_file, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # For each attribution, create a personalized file
    for person in attributions:
        content = original_content
        
        # Sort quotes in reverse order by position to avoid position shifts when replacing
        sorted_quotes = sorted(quotes, key=lambda q: q['start'], reverse=True)
        
        # Replace quotes not from this person with redacted message
        for quote in sorted_quotes:
            if quote['attribution'] != person:
                # Preserve the original format (with or without dash) when redacting
                original_quote = quote['full_match']
                dash_part = re.search(r'"\s*([-–—]\s*)?\(', original_quote)
                if dash_part and dash_part.group(1):
                    dash = dash_part.group(1)
                else:
                    dash = " "  # Default space if no dash
                
                # Determine if the original quote used single or double quotes
                original_quote = quote['full_match']
                uses_single_quotes = original_quote.startswith("'") and not original_quote.startswith('"')
                
                if keep_names:
                    # Keep the attribution in the redacted quote
                    if uses_single_quotes:
                        redacted = f"'[QUOTE REDACTED FOR REVIEW]'{dash}({quote['attribution']})"
                    else:
                        redacted = f'"[QUOTE REDACTED FOR REVIEW]"{dash}({quote["attribution"]})'
                else:
                    # Remove the attribution - just show [REDACTED]
                    if uses_single_quotes:
                        redacted = f"'[QUOTE REDACTED]'"
                    else:
                        redacted = f'"[QUOTE REDACTED]"'
                    
                content = content[:quote['start']] + redacted + content[quote['end']:]
        
        # Create the personalized markdown file
        output_md = f"{base_name}_{person}.md"
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Convert to DOCX using pandoc
        output_docx = f"{base_name}_{person}.docx"
        try:
            subprocess.run(['pandoc', output_md, '-o', output_docx], check=True)
            print(f"Created {output_docx} for {person}")
        except subprocess.CalledProcessError as e:
            print(f"Error converting {output_md} to DOCX: {e}")
        except FileNotFoundError:
            print("Error: pandoc not found. Please install pandoc to convert to DOCX.")
            print(f"Created markdown file {output_md} for {person}")

def report_suspected_quotes(suspected_quotes):
    """Report suspected quotes that may need editing to match the required format."""
    if suspected_quotes:
        print("\nSuspected quotes that may need formatting:")
        print("-" * 80)
        for i, sq in enumerate(suspected_quotes):
            print(f"Line {sq['line_number']}:")
            print(f"  Quote: {sq['quote_text']}")
            print(f"  Attribution: {sq['attribution_line']}")
            print(f"  Suggested format: {sq['suggestion']}")
            if i < len(suspected_quotes) - 1:
                print("-" * 40)
        print("-" * 80)
        print("To properly format these quotes, edit them to follow the pattern: \"quote text\" (Person)")
        print("This will ensure all quotes are properly extracted and processed.")

def fix_suspected_quotes(input_file, suspected_quotes):
    """Automatically fix the suspected quotes in the original file."""
    if not suspected_quotes:
        return False
    
    # Read the file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Track if any changes were made
    changes_made = False
    
    # Group by line number to avoid conflicts
    by_line = defaultdict(list)
    for sq in suspected_quotes:
        by_line[sq['line_number']].append(sq)
    
    # Process lines in reverse order to avoid position shifts
    for line_num in sorted(by_line.keys(), reverse=True):
        for sq in by_line[line_num]:
            # Handle different cases based on quote format
            if sq['quote_text'].startswith('"') or sq['quote_text'].startswith("'"):
                # Standard quoted text
                quote_line_num = line_num - 1
                # Find the line that contains the quote text
                while quote_line_num >= 0:
                    if lines[quote_line_num].strip() == sq['quote_text']:
                        # Remove the quote line and attribution line
                        combined_line = sq['suggestion'] + '\n'
                        lines[quote_line_num] = combined_line
                        lines[line_num] = ''  # Remove attribution line
                        changes_made = True
                        break
                    quote_line_num -= 1
            elif '>' in sq['quote_text']:
                # Blockquote handling - more complex case
                # Find the blockquote start and end
                blockquote_text = sq['quote_text'].strip('"')  # Remove surrounding quotes
                blockquote_lines = blockquote_text.split()
                
                # Try to find the blockquote in the file
                start_line = max(0, line_num - 10)  # Look up to 10 lines back
                for i in range(start_line, line_num):
                    if lines[i].strip().startswith('>') and any(term in lines[i] for term in blockquote_lines[:2]):
                        # Found the likely start of the blockquote
                        blockquote_start = i
                        blockquote_end = i
                        
                        # Find the end of the blockquote
                        while blockquote_end < line_num and lines[blockquote_end].strip().startswith('>'):
                            blockquote_end += 1
                            
                        # Extract the blockquote content
                        blockquote_content = []
                        for j in range(blockquote_start, blockquote_end):
                            line_content = lines[j].lstrip('> ').strip()
                            if line_content:
                                blockquote_content.append(line_content)
                                
                        # Replace the blockquote with proper quote format
                        attribution = sq['attribution_line'].strip()
                        if not attribution.startswith('('):
                            attribution = f'({attribution})'
                            
                        # Create the combined quote
                        combined_quote = f'"{" ".join(blockquote_content)}" {attribution}\n'
                        
                        # Replace the first line of the blockquote
                        lines[blockquote_start] = combined_quote
                        
                        # Remove the rest of the blockquote lines and the attribution line
                        for j in range(blockquote_start + 1, blockquote_end):
                            lines[j] = ''
                        lines[line_num] = ''  # Remove the attribution line
                        
                        changes_made = True
                        break
    
    # Write the updated content
    if changes_made:
        # Remove empty lines before writing
        non_empty_lines = [line for line in lines if line.strip() or line == '\n']  # Keep blank lines but remove empty ones
        with open(input_file, 'w', encoding='utf-8') as f:
            f.writelines(non_empty_lines)
        print(f"Updated {input_file} with fixed quote formatting.")
    
    return changes_made

def main(args=None):
    """Entry point for the pullquotes command-line tool.
    
    Args:
        args: Command-line arguments (defaults to sys.argv if None)
    """
    if args is None:
        args = sys.argv[1:]
    
    if not args or args[0] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    
    # Parse command line arguments
    fix_quotes = False
    keep_names = False
    test_mode = False
    
    # Check if first argument is a flag
    if args[0].startswith('--'):
        print("Error: First argument must be a markdown file.")
        print(__doc__)
        sys.exit(1)
    
    input_file = args[0]
    
    # Check for flags
    for arg in args[1:]:
        if arg == '--fix':
            fix_quotes = True
            print("Fix mode enabled - will attempt to auto-fix suspected quotes.")
        elif arg == '--keep-names':
            keep_names = True
            print("Keep names mode enabled - will keep quotee names in redacted quotes.")
        elif arg == '--test':
            test_mode = True
            print("Test mode enabled - will check for quotes without generating output files.")
    
    # Check if file exists
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    # Read the markdown file
    with open(input_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    # Extract quotes and suspected quotes
    quotes, suspected_quotes = extract_quotes(markdown_text)
    
    # Report suspected quotes that need formatting
    report_suspected_quotes(suspected_quotes)
    
    # Fix suspected quotes if requested
    if fix_quotes and suspected_quotes:
        if fix_suspected_quotes(input_file, suspected_quotes):
            print("Quotes have been fixed. Running extraction again with updated file.")
            # Re-read the file and extract quotes again
            with open(input_file, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            quotes, suspected_quotes = extract_quotes(markdown_text)  # Update both quotes and suspected_quotes
            
            # Report the updated state after fixing
            if suspected_quotes:
                print("\nSome quotes still need fixing after auto-fix attempt:")
                report_suspected_quotes(suspected_quotes)
    
    if not quotes:
        print("No quotes found in the document.")
        if suspected_quotes:
            print("Please format the suspected quotes correctly and try again.")
            print("You can run with --fix flag to attempt automatic fixing: pullquotes file.md --fix")
        sys.exit(0)
    
    # Print summary
    attributions = set(quote['attribution'] for quote in quotes)
    print(f"\nSummary: Found {len(quotes)} quotes from {len(attributions)} people.")
    for person in sorted(attributions):
        count = sum(1 for q in quotes if q['attribution'] == person)
        print(f"- {person}: {count} quotes")
    
    # In test mode, we're done after reporting
    if test_mode:
        if suspected_quotes:
            print("\nTest mode: File contains quotes that need formatting. Please fix them or use --fix.")
            sys.exit(1)  # Exit with error code to indicate quotes need fixing
        else:
            print("\nTest mode: All quotes in the file are properly formatted.")
            sys.exit(0)  # Exit with success code
    
    # Create personalized files with the keep_names option (only if not in test mode)
    create_personalized_files(input_file, quotes, keep_names=keep_names)

if __name__ == "__main__":
    main()