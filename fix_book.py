#!/usr/bin/env python3
"""
Book Fixer - Process entire book zip files to fix TOC and citation issues.

Usage:
    python fix_book.py input.zip -o output.zip
    python fix_book.py input.zip --analyze
    python fix_book.py book_folder/ -o fixed_folder/
"""

import sys
import os
import argparse
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from toc_fixer.book_fixer import BookFixer, print_report


def main():
    parser = argparse.ArgumentParser(
        prog='fix_book',
        description='Fix TOC nesting and citation issues in book/EPUB files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix a zip file
  python fix_book.py book.zip -o book_fixed.zip

  # Fix a directory
  python fix_book.py ./book_folder/ -o ./book_fixed/

  # Analyze without fixing
  python fix_book.py book.zip --analyze

  # Fix only TOC (skip citations)
  python fix_book.py book.zip -o fixed.zip --no-citations

  # Fix only citations (skip TOC)
  python fix_book.py book.zip -o fixed.zip --no-toc

What it fixes:
  1. TOC XML files:
     - Nesting structure (chapters > sections > subsections)
     - Broken links and URL encoding

  2. Content XML files:
     - <citation>ch0011-c1-bib-0001</citation>
       becomes:
       <ulink url="ch0011#ch0011-c1-bib-0001">1</ulink>
"""
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input zip file or directory'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output zip file or directory (default: input_fixed.zip)'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze issues without fixing'
    )
    
    parser.add_argument(
        '--no-toc',
        action='store_true',
        help='Skip TOC fixing'
    )
    
    parser.add_argument(
        '--no-citations',
        action='store_true',
        help='Skip citation fixing'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output report as JSON'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Check input exists
    if not os.path.exists(args.input):
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Create fixer
    fixer = BookFixer(
        fix_toc=not args.no_toc,
        fix_citations=not args.no_citations
    )
    
    try:
        is_zip = args.input.lower().endswith('.zip') or zipfile.is_zipfile(args.input) if os.path.isfile(args.input) else False
        
        if args.analyze:
            # Analyze mode
            if is_zip:
                report = fixer.analyze_zip(args.input)
            else:
                # For directories, we need to analyze differently
                report = fixer.analyze_zip(args.input) if is_zip else analyze_directory(fixer, args.input)
            
            if args.json:
                print(json.dumps(report, indent=2, default=str))
            else:
                print_analysis_report(report)
        else:
            # Fix mode
            if is_zip:
                report = fixer.process_zip(args.input, args.output)
            else:
                report = fixer.process_directory(args.input, args.output)
            
            if args.json:
                # Clean up report for JSON (remove large change lists)
                clean_report = {k: v for k, v in report.items() if k != 'content_files'}
                clean_report['content_files_count'] = len(report.get('content_files', []))
                print(json.dumps(clean_report, indent=2, default=str))
            else:
                print_report(report)
                
            if args.verbose:
                print(f"\nOutput written to: {report.get('output', args.output)}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def analyze_directory(fixer, directory):
    """Analyze a directory without modifying it."""
    import tempfile
    import shutil
    
    report = {
        'input': directory,
        'toc_files': [],
        'content_files': [],
        'total_citations': 0,
        'total_nesting_issues': 0,
        'total_link_issues': 0,
    }
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden and system directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__MACOSX']
        
        for filename in files:
            if filename.startswith('.'):
                continue
                
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, directory)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                continue
            
            # Check TOC files
            if fixer._is_toc_file(filename):
                try:
                    analysis = fixer.toc_fixer.get_report(content)
                    report['toc_files'].append({
                        'file': rel_path,
                        'format': analysis.get('format', 'unknown'),
                        'nesting_issues': len(analysis.get('nesting_issues', [])),
                        'link_issues': len(analysis.get('link_issues', [])),
                    })
                    report['total_nesting_issues'] += len(analysis.get('nesting_issues', []))
                    report['total_link_issues'] += len(analysis.get('link_issues', []))
                except:
                    pass
            
            # Check content files
            if fixer._is_content_file(filename) or filename.endswith('.xml'):
                citations = fixer.citation_fixer.analyze_citations(content)
                if citations:
                    report['content_files'].append({
                        'file': rel_path,
                        'citations': len(citations),
                    })
                    report['total_citations'] += len(citations)
    
    return report


def print_analysis_report(report):
    """Print analysis report."""
    print("=" * 70)
    print("Book Analysis Report")
    print("=" * 70)
    print()
    
    print(f"Input: {report.get('input', 'N/A')}")
    print()
    
    # TOC files
    toc_files = report.get('toc_files', [])
    print(f"TOC Files Found: {len(toc_files)}")
    print("-" * 50)
    for toc in toc_files:
        nesting = toc.get('nesting_issues', 0)
        if isinstance(nesting, list):
            nesting = len(nesting)
        links = toc.get('link_issues', 0)
        if isinstance(links, list):
            links = len(links)
        print(f"  {toc['file']}")
        print(f"    Format: {toc.get('format', 'unknown')}")
        print(f"    Nesting issues: {nesting}")
        print(f"    Link issues: {links}")
    print()
    
    # Content files with citations
    content_files = report.get('content_files', [])
    print(f"Content Files with Citations: {len(content_files)}")
    print("-" * 50)
    for cf in content_files:
        citations = cf.get('citations', 0)
        print(f"  {cf['file']}: {citations} citations")
    print()
    
    # Summary
    print("Summary")
    print("-" * 50)
    print(f"  Total nesting issues: {report.get('total_nesting_issues', 0)}")
    print(f"  Total link issues: {report.get('total_link_issues', 0)}")
    print(f"  Total citations to fix: {report.get('total_citations', 0)}")
    print()
    print("=" * 70)


# For importing zipfile
import zipfile

if __name__ == '__main__':
    main()
