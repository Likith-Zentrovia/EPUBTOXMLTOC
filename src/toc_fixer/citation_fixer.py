"""
Citation Fixer module for converting citation tags to proper ulink format.

Converts:
    <citation>ch0011-c1-bib-0001</citation>
To:
    <ulink url="ch0011#ch0011s009000-5">1</ulink>

The link points to the References section of the chapter, not individual entries.
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class CitationFixer:
    """
    Fixes citation tags in XML content files by converting them to proper ulink format.
    """
    
    def __init__(self):
        # Pattern to match citation tags
        self.citation_pattern = re.compile(
            r'<citation>([^<]+)</citation>',
            re.IGNORECASE
        )
        
        # Pattern to extract chapter and bib number from citation ID
        # e.g., ch0011-c1-bib-0001 -> chapter=ch0011, bib_num=0001
        self.citation_id_pattern = re.compile(
            r'^(ch\d+)-.*?-bib-(\d+)$',
            re.IGNORECASE
        )
        
        # Alternative patterns for different citation ID formats
        self.alt_patterns = [
            # ch0011-c1-bib-0001
            re.compile(r'^(ch\d+).*?bib.*?(\d+)$', re.IGNORECASE),
            # bib0001, bib-0001
            re.compile(r'^bib-?(\d+)$', re.IGNORECASE),
            # ref0001, ref-0001
            re.compile(r'^ref-?(\d+)$', re.IGNORECASE),
            # Just a number
            re.compile(r'^(\d+)$'),
        ]
    
    def fix_citations_in_content(self, content: str, filename: str = "") -> Tuple[str, List[Dict]]:
        """
        Fix all citation tags in the content.
        
        Args:
            content: The XML content as a string.
            filename: Optional filename for context (used to determine chapter).
            
        Returns:
            Tuple of (fixed_content, list_of_changes)
        """
        changes = []
        
        # Extract chapter from filename if available
        default_chapter = self._extract_chapter_from_filename(filename)
        
        # Find the References section ID in this content
        references_section_id = self._find_references_section_id(content, default_chapter)
        
        def replace_citation(match):
            citation_id = match.group(1).strip()
            original = match.group(0)
            
            # Parse the citation ID to extract chapter and bib number
            chapter, bib_num = self._parse_citation_id(citation_id, default_chapter)
            
            # Use the References section ID for the link target
            # All citations in a chapter link to that chapter's References section
            if references_section_id:
                ref_target = references_section_id
            else:
                # Fallback: construct a default references section ID
                ref_target = f"{chapter}s009000-5" if chapter else citation_id
            
            # Create the ulink - URL points to chapter's References section
            if chapter:
                url = f"{chapter}#{ref_target}"
            else:
                url = f"#{ref_target}"
            
            # Display number (strip leading zeros for display)
            display_num = str(int(bib_num)) if bib_num and bib_num.isdigit() else bib_num or citation_id
            
            replacement = f'<ulink url="{url}">{display_num}</ulink>'
            
            changes.append({
                'original': original,
                'replacement': replacement,
                'citation_id': citation_id,
                'ref_target': ref_target,
                'chapter': chapter,
                'bib_num': bib_num
            })
            
            return replacement
        
        fixed_content = self.citation_pattern.sub(replace_citation, content)
        
        return fixed_content, changes
    
    def _find_references_section_id(self, content: str, chapter: Optional[str]) -> Optional[str]:
        """
        Find the References section ID in the content.
        
        Looks for patterns like:
        - <sect2 id="ch0011s009000-5"><title>References</title>
        - <section id="..."><title>References</title>
        - <bibliography id="...">
        
        Returns the section ID if found.
        """
        # Pattern to find section with References title
        patterns = [
            # sect1, sect2, sect3, etc. with References title
            re.compile(
                r'<sect\d[^>]*\s+id\s*=\s*["\']([^"\']+)["\'][^>]*>[\s\S]*?<title[^>]*>\s*References\s*</title>',
                re.IGNORECASE
            ),
            # Generic section with References title
            re.compile(
                r'<section[^>]*\s+id\s*=\s*["\']([^"\']+)["\'][^>]*>[\s\S]*?<title[^>]*>\s*References\s*</title>',
                re.IGNORECASE
            ),
            # bibliography element
            re.compile(
                r'<bibliography[^>]*\s+id\s*=\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),
            # div with References title
            re.compile(
                r'<div[^>]*\s+id\s*=\s*["\']([^"\']+)["\'][^>]*>[\s\S]*?<[^>]*>\s*References\s*</',
                re.IGNORECASE
            ),
        ]
        
        for pattern in patterns:
            match = pattern.search(content)
            if match:
                return match.group(1)
        
        # Try to find by looking for "References" heading and backtracking to find ID
        ref_title_match = re.search(
            r'<(sect\d|section|div)[^>]*id\s*=\s*["\']([^"\']+)["\'][^>]*>[\s\S]{0,500}?References',
            content,
            re.IGNORECASE
        )
        if ref_title_match:
            return ref_title_match.group(2)
        
        return None
    
    def _extract_chapter_from_filename(self, filename: str) -> Optional[str]:
        """Extract chapter identifier from filename."""
        if not filename:
            return None
        
        # Try to match ch0011.xml, chapter11.xml, etc.
        basename = os.path.basename(filename)
        
        patterns = [
            re.compile(r'^(ch\d+)', re.IGNORECASE),
            re.compile(r'^(chapter\d+)', re.IGNORECASE),
            re.compile(r'^(c\d+)', re.IGNORECASE),
        ]
        
        for pattern in patterns:
            match = pattern.match(basename)
            if match:
                return match.group(1).lower()
        
        return None
    
    def _parse_citation_id(self, citation_id: str, default_chapter: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse a citation ID to extract chapter and bibliography number.
        
        Args:
            citation_id: The citation ID string (e.g., "ch0011-c1-bib-0001")
            default_chapter: Default chapter to use if not found in ID
            
        Returns:
            Tuple of (chapter, bib_number)
        """
        # Try main pattern first
        match = self.citation_id_pattern.match(citation_id)
        if match:
            return match.group(1).lower(), match.group(2)
        
        # Try alternative patterns
        for pattern in self.alt_patterns:
            match = pattern.match(citation_id)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return groups[0].lower() if groups[0] else default_chapter, groups[1]
                elif len(groups) == 1:
                    # Check if it looks like a chapter or a number
                    val = groups[0]
                    if val.lower().startswith('ch'):
                        return val.lower(), None
                    else:
                        return default_chapter, val
        
        # Try to extract any chapter reference
        ch_match = re.search(r'(ch\d+)', citation_id, re.IGNORECASE)
        chapter = ch_match.group(1).lower() if ch_match else default_chapter
        
        # Try to extract any number at the end
        num_match = re.search(r'(\d+)$', citation_id)
        bib_num = num_match.group(1) if num_match else None
        
        return chapter, bib_num
    
    def fix_file(self, input_path: str, output_path: Optional[str] = None) -> Tuple[str, List[Dict]]:
        """
        Fix citations in a file.
        
        Args:
            input_path: Path to the input file.
            output_path: Optional path to save fixed content.
            
        Returns:
            Tuple of (fixed_content, list_of_changes)
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed_content, changes = self.fix_citations_in_content(content, input_path)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
        
        return fixed_content, changes
    
    def analyze_citations(self, content: str) -> List[Dict]:
        """
        Analyze citations in content without fixing them.
        
        Args:
            content: The XML content.
            
        Returns:
            List of citation info dictionaries.
        """
        citations = []
        
        for match in self.citation_pattern.finditer(content):
            citation_id = match.group(1).strip()
            chapter, bib_num = self._parse_citation_id(citation_id)
            
            citations.append({
                'original': match.group(0),
                'citation_id': citation_id,
                'chapter': chapter,
                'bib_num': bib_num,
                'position': match.start()
            })
        
        return citations
