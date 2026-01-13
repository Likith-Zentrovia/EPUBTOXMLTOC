"""
Book Fixer module for processing entire EPUB/book zip files.

Handles:
- Extracting zip files
- Finding and fixing TOC XML files
- Finding and fixing content XML files (citations)
- Repackaging into output zip
"""

import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .toc_fixer import TOCFixer
from .citation_fixer import CitationFixer
from .reference_fixer import ReferenceFixer


class BookFixer:
    """
    Processes entire book/EPUB zip files to fix TOC and citation issues.
    """
    
    # File patterns to process
    TOC_PATTERNS = [
        r'toc\..*\.xml$',
        r'toc\.xml$',
        r'toc\.ncx$',
        r'nav\.xhtml$',
        r'navigation\.xml$',
    ]
    
    CONTENT_PATTERNS = [
        r'ch\d+.*\.xml$',
        r'chapter\d+.*\.xml$',
        r'part\d+.*\.xml$',
        r'.*\.xhtml$',
        r'.*content.*\.xml$',
    ]
    
    # Files/directories to skip
    SKIP_PATTERNS = [
        r'__MACOSX',
        r'\.DS_Store',
        r'Thumbs\.db',
        r'\.git',
    ]
    
    def __init__(self, fix_toc: bool = True, fix_citations: bool = True, fix_references: bool = True):
        """
        Initialize the Book Fixer.
        
        Args:
            fix_toc: Whether to fix TOC XML files.
            fix_citations: Whether to fix citation tags in content files.
            fix_references: Whether to fix bibliography reference IDs.
        """
        self.fix_toc = fix_toc
        self.fix_citations = fix_citations
        self.fix_references = fix_references
        self.toc_fixer = TOCFixer()
        self.citation_fixer = CitationFixer()
        self.reference_fixer = ReferenceFixer()
        
        # Compile patterns
        self.toc_re = [re.compile(p, re.IGNORECASE) for p in self.TOC_PATTERNS]
        self.content_re = [re.compile(p, re.IGNORECASE) for p in self.CONTENT_PATTERNS]
        self.skip_re = [re.compile(p, re.IGNORECASE) for p in self.SKIP_PATTERNS]
    
    def process_zip(self, input_zip: str, output_zip: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a zip file containing book content.
        
        Args:
            input_zip: Path to input zip file.
            output_zip: Path to output zip file. If None, creates input_fixed.zip.
            
        Returns:
            Report dictionary with processing results.
        """
        if not output_zip:
            base = os.path.splitext(input_zip)[0]
            output_zip = f"{base}_fixed.zip"
        
        report = {
            'input': input_zip,
            'output': output_zip,
            'toc_files': [],
            'content_files': [],
            'reference_files': [],
            'errors': [],
            'total_citations_fixed': 0,
            'total_nesting_issues_fixed': 0,
            'total_references_fixed': 0,
        }
        
        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = os.path.join(temp_dir, 'extracted')
            output_dir = os.path.join(temp_dir, 'output')
            
            try:
                # Extract zip
                self._extract_zip(input_zip, extract_dir)
                
                # Copy to output directory
                shutil.copytree(extract_dir, output_dir)
                
                # Process files
                self._process_directory(output_dir, report)
                
                # Create output zip
                self._create_zip(output_dir, output_zip)
                
            except Exception as e:
                report['errors'].append(f"Processing error: {str(e)}")
                raise
        
        return report
    
    def process_directory(self, input_dir: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a directory containing book content.
        
        Args:
            input_dir: Path to input directory.
            output_dir: Path to output directory. If None, modifies in place.
            
        Returns:
            Report dictionary with processing results.
        """
        report = {
            'input': input_dir,
            'output': output_dir or input_dir,
            'toc_files': [],
            'content_files': [],
            'reference_files': [],
            'errors': [],
            'total_citations_fixed': 0,
            'total_nesting_issues_fixed': 0,
            'total_references_fixed': 0,
        }
        
        # If output_dir is different, copy first
        if output_dir and output_dir != input_dir:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            shutil.copytree(input_dir, output_dir)
            process_dir = output_dir
        else:
            process_dir = input_dir
        
        # Process files
        self._process_directory(process_dir, report)
        
        return report
    
    def _extract_zip(self, zip_path: str, extract_to: str):
        """Extract a zip file."""
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_to)
    
    def _create_zip(self, source_dir: str, output_path: str):
        """Create a zip file from a directory."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                # Filter out skip patterns from dirs to avoid descending
                dirs[:] = [d for d in dirs if not self._should_skip(d)]
                
                for file in files:
                    if self._should_skip(file):
                        continue
                    
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arc_name)
    
    def _should_skip(self, name: str) -> bool:
        """Check if a file/directory should be skipped."""
        for pattern in self.skip_re:
            if pattern.search(name):
                return True
        return False
    
    def _is_toc_file(self, filename: str) -> bool:
        """Check if a file is a TOC file."""
        for pattern in self.toc_re:
            if pattern.search(filename):
                return True
        return False
    
    def _is_content_file(self, filename: str) -> bool:
        """Check if a file is a content file that may have citations."""
        for pattern in self.content_re:
            if pattern.search(filename):
                return True
        return False
    
    def _process_directory(self, directory: str, report: Dict[str, Any]):
        """Process all files in a directory recursively."""
        for root, dirs, files in os.walk(directory):
            # Filter out skip patterns
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            
            for filename in files:
                if self._should_skip(filename):
                    continue
                
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, directory)
                
                try:
                    # Check if it's a TOC file
                    if self.fix_toc and self._is_toc_file(filename):
                        self._process_toc_file(file_path, rel_path, report)
                    
                    # Check if it's a content file (may have citations)
                    elif self.fix_citations and self._is_content_file(filename):
                        self._process_content_file(file_path, rel_path, report)
                    
                    # Also check XML files that might have citations
                    elif self.fix_citations and filename.endswith('.xml'):
                        self._process_content_file(file_path, rel_path, report)
                        
                except Exception as e:
                    report['errors'].append(f"Error processing {rel_path}: {str(e)}")
    
    def _process_toc_file(self, file_path: str, rel_path: str, report: Dict[str, Any]):
        """Process a TOC file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get analysis before fixing
            analysis = self.toc_fixer.get_report(content)
            nesting_issues = len(analysis.get('nesting_issues', []))
            link_issues = len(analysis.get('link_issues', []))
            
            # Fix the TOC
            fixed_content = self.toc_fixer.fix(content)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            report['toc_files'].append({
                'file': rel_path,
                'format': analysis.get('format', 'unknown'),
                'nesting_issues_fixed': nesting_issues,
                'link_issues_fixed': link_issues,
            })
            report['total_nesting_issues_fixed'] += nesting_issues
            
        except Exception as e:
            report['errors'].append(f"TOC error in {rel_path}: {str(e)}")
    
    def _process_content_file(self, file_path: str, rel_path: str, report: Dict[str, Any]):
        """Process a content file to fix citations and references."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified = False
            citations_fixed = 0
            references_fixed = 0
            
            # Fix citations if present
            if self.fix_citations and '<citation>' in content.lower():
                content, changes = self.citation_fixer.fix_citations_in_content(content, file_path)
                if changes:
                    citations_fixed = len(changes)
                    modified = True
            
            # Fix bibliography/reference IDs if present
            if self.fix_references and ('<bibliomixed' in content.lower() or '<biblioentry' in content.lower()):
                content, ref_changes = self.reference_fixer.fix_references_in_content(content, file_path)
                if ref_changes:
                    references_fixed = len(ref_changes)
                    modified = True
                    report['reference_files'].append({
                        'file': rel_path,
                        'references_fixed': references_fixed,
                    })
                    report['total_references_fixed'] += references_fixed
            
            if modified:
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                if citations_fixed > 0:
                    report['content_files'].append({
                        'file': rel_path,
                        'citations_fixed': citations_fixed,
                    })
                    report['total_citations_fixed'] += citations_fixed
                
        except Exception as e:
            report['errors'].append(f"Content error in {rel_path}: {str(e)}")
    
    def analyze_zip(self, zip_path: str) -> Dict[str, Any]:
        """
        Analyze a zip file without modifying it.
        
        Args:
            zip_path: Path to the zip file.
            
        Returns:
            Analysis report.
        """
        report = {
            'input': zip_path,
            'toc_files': [],
            'content_files': [],
            'total_citations': 0,
            'total_nesting_issues': 0,
            'total_link_issues': 0,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract zip
            self._extract_zip(zip_path, temp_dir)
            
            # Analyze files
            for root, dirs, files in os.walk(temp_dir):
                dirs[:] = [d for d in dirs if not self._should_skip(d)]
                
                for filename in files:
                    if self._should_skip(filename):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except:
                        continue
                    
                    # Analyze TOC files
                    if self._is_toc_file(filename):
                        try:
                            analysis = self.toc_fixer.get_report(content)
                            report['toc_files'].append({
                                'file': rel_path,
                                'format': analysis.get('format', 'unknown'),
                                'nesting_issues': analysis.get('nesting_issues', []),
                                'link_issues': analysis.get('link_issues', []),
                            })
                            report['total_nesting_issues'] += len(analysis.get('nesting_issues', []))
                            report['total_link_issues'] += len(analysis.get('link_issues', []))
                        except:
                            pass
                    
                    # Analyze content files for citations
                    if self._is_content_file(filename) or filename.endswith('.xml'):
                        citations = self.citation_fixer.analyze_citations(content)
                        if citations:
                            report['content_files'].append({
                                'file': rel_path,
                                'citations': len(citations),
                                'sample': citations[:3] if len(citations) > 3 else citations,
                            })
                            report['total_citations'] += len(citations)
        
        return report


def print_report(report: Dict[str, Any]):
    """Print a processing report in human-readable format."""
    print("=" * 70)
    print("Book Processing Report")
    print("=" * 70)
    print()
    
    print(f"Input:  {report.get('input', 'N/A')}")
    print(f"Output: {report.get('output', 'N/A')}")
    print()
    
    # TOC files
    toc_files = report.get('toc_files', [])
    print(f"TOC Files Processed: {len(toc_files)}")
    print("-" * 50)
    for toc in toc_files:
        print(f"  {toc['file']}")
        print(f"    Format: {toc.get('format', 'unknown')}")
        print(f"    Nesting issues fixed: {toc.get('nesting_issues_fixed', 0)}")
        print(f"    Link issues fixed: {toc.get('link_issues_fixed', 0)}")
    print()
    
    # Content files
    content_files = report.get('content_files', [])
    print(f"Content Files with Citations Fixed: {len(content_files)}")
    print("-" * 50)
    for cf in content_files:
        print(f"  {cf['file']}: {cf.get('citations_fixed', 0)} citations fixed")
    print()
    
    # Reference files
    reference_files = report.get('reference_files', [])
    print(f"Reference/Bibliography Files Fixed: {len(reference_files)}")
    print("-" * 50)
    for rf in reference_files:
        print(f"  {rf['file']}: {rf.get('references_fixed', 0)} reference IDs fixed")
    print()
    
    # Summary
    print("Summary")
    print("-" * 50)
    print(f"  Total nesting issues fixed: {report.get('total_nesting_issues_fixed', 0)}")
    print(f"  Total citations fixed: {report.get('total_citations_fixed', 0)}")
    print(f"  Total reference IDs fixed: {report.get('total_references_fixed', 0)}")
    
    # Errors
    errors = report.get('errors', [])
    if errors:
        print()
        print(f"Errors: {len(errors)}")
        print("-" * 50)
        for err in errors:
            print(f"  - {err}")
    
    print()
    print("=" * 70)
