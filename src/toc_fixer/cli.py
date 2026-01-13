#!/usr/bin/env python3
"""
Command-line interface for TOC XML Fixer.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from .toc_fixer import TOCFixer


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='toc-fixer',
        description='Fix nesting and link issues in TOC XML files (EPUB NCX, Nav, or generic)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix a TOC file and save to new file
  toc-fixer input.ncx -o output.ncx

  # Fix a TOC file in place
  toc-fixer input.ncx --in-place

  # Analyze issues without fixing
  toc-fixer input.ncx --analyze

  # Fix with content validation
  toc-fixer toc.ncx -o fixed.ncx --content-path ./OEBPS

Supported formats:
  - EPUB 2 NCX (Navigation Control for XML)
  - EPUB 3 Navigation Document (XHTML)
  - Generic TOC XML structures
"""
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input TOC XML file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path for the fixed TOC'
    )
    
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Fix the file in place (overwrite input file)'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze and report issues without fixing'
    )
    
    parser.add_argument(
        '--content-path',
        type=str,
        help='Base path to EPUB content for link validation'
    )
    
    parser.add_argument(
        '--format',
        choices=['ncx', 'nav', 'generic', 'auto'],
        default='auto',
        help='Force a specific format (default: auto-detect)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output analysis results as JSON'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.analyze and not args.output and not args.in_place:
        parser.error("Please specify --output, --in-place, or --analyze")
    
    if args.output and args.in_place:
        parser.error("Cannot use both --output and --in-place")
    
    # Check input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Determine content base path
    content_base_path = args.content_path
    if not content_base_path:
        content_base_path = str(input_path.parent)
    
    # Create fixer
    fixer = TOCFixer(content_base_path=content_base_path)
    
    try:
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        if args.analyze:
            # Analyze mode
            report = fixer.get_report(xml_content)
            
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print_report(report, args.verbose)
            
            # Exit with error code if issues found
            if report.get('nesting_issues') or report.get('link_issues'):
                sys.exit(1)
        else:
            # Fix mode
            if args.verbose:
                print(f"Processing: {args.input}")
                print(f"Detected format: {fixer.detect_format(xml_content)}")
            
            # Fix the TOC
            fixed_content = fixer.fix(xml_content)
            
            # Determine output path
            output_path = args.output if args.output else str(input_path)
            
            # Write output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            if args.verbose:
                print(f"Fixed TOC written to: {output_path}")
            else:
                print(f"Successfully fixed: {output_path}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def print_report(report: dict, verbose: bool = False):
    """Print analysis report in human-readable format."""
    print("=" * 60)
    print("TOC Analysis Report")
    print("=" * 60)
    print()
    
    print(f"Format detected: {report.get('format', 'unknown')}")
    print(f"Total items: {report.get('total_items', 0)}")
    print(f"Overall severity: {report.get('severity', 'unknown')}")
    print()
    
    # Nesting issues
    nesting_issues = report.get('nesting_issues', [])
    print(f"Nesting Issues: {len(nesting_issues)}")
    print("-" * 40)
    
    if nesting_issues:
        for i, issue in enumerate(nesting_issues, 1):
            print(f"  {i}. {issue.get('title', 'Unknown')}")
            print(f"     Type: {issue.get('type', 'unknown')}")
            print(f"     {issue.get('description', '')}")
            if verbose:
                print(f"     Current level: {issue.get('current_level', 'N/A')}")
                print(f"     Suggested level: {issue.get('suggested_level', 'N/A')}")
            print()
    else:
        print("  No nesting issues found.")
        print()
    
    # Link issues
    link_issues = report.get('link_issues', [])
    print(f"Link Issues: {len(link_issues)}")
    print("-" * 40)
    
    if link_issues:
        for i, issue in enumerate(link_issues, 1):
            print(f"  {i}. {issue.get('title', 'Unknown')}")
            print(f"     Type: {issue.get('type', 'unknown')}")
            print(f"     {issue.get('description', '')}")
            if verbose:
                print(f"     Current href: {issue.get('href', 'N/A')}")
                suggested = issue.get('suggested_href')
                if suggested:
                    print(f"     Suggested href: {suggested}")
            print()
    else:
        print("  No link issues found.")
        print()
    
    print("=" * 60)


def fix_file():
    """Convenience function to fix a single file."""
    main()


if __name__ == '__main__':
    main()
