"""
Bibliography Structure Fixer module.

Converts wrong reference structures like:
    <sect2 id="ch0011s009000-5">
      <title>References</title>
      <orderedlist>
        <listitem id="ch0011-c1-bib-0001">
          <para><emphasis role="strong">1</emphasis> Content...</para>
        </listitem>
      </orderedlist>
    </sect2>

To correct structure:
    <bibliography id="ch0011">
      <title>References</title>
      <bibliodiv>
        <title>Primary Sources</title>
        <bibliomixed id="ch0011-c1-bib-0001">Content...</bibliomixed>
      </bibliodiv>
    </bibliography>

This fixes the duplicate numbering issue where numbers appear twice.
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from lxml import etree


class BibliographyFixer:
    """
    Fixes bibliography/reference section structure to prevent duplicate numbering.
    """
    
    def __init__(self):
        # Pattern to find reference sections with orderedlist structure
        self.ref_section_pattern = re.compile(
            r'(<sect\d[^>]*>[\s\S]*?<title[^>]*>\s*References\s*</title>[\s\S]*?</sect\d>)',
            re.IGNORECASE
        )
        
        # Pattern to find orderedlist with bibliographyEntry listitems
        self.orderedlist_pattern = re.compile(
            r'<orderedlist[^>]*>[\s\S]*?</orderedlist>',
            re.IGNORECASE
        )
    
    def fix_bibliography_structure(self, content: str, filename: str = "") -> Tuple[str, List[Dict]]:
        """
        Fix bibliography structure in the content.
        
        Args:
            content: The XML content as a string.
            filename: Optional filename for context.
            
        Returns:
            Tuple of (fixed_content, list_of_changes)
        """
        changes = []
        chapter = self._extract_chapter_from_filename(filename)
        
        # Find and fix reference sections
        def fix_section(match):
            section_content = match.group(1)
            fixed_section, section_changes = self._fix_reference_section(section_content, chapter)
            changes.extend(section_changes)
            return fixed_section
        
        fixed_content = self.ref_section_pattern.sub(fix_section, content)
        
        return fixed_content, changes
    
    def _fix_reference_section(self, section_content: str, chapter: Optional[str]) -> Tuple[str, List[Dict]]:
        """Fix a single reference section."""
        changes = []
        
        # Check if it contains orderedlist with listitems
        if '<orderedlist' not in section_content.lower():
            return section_content, changes
        
        # Extract the section ID
        section_id_match = re.search(r'<sect\d[^>]*id\s*=\s*["\']([^"\']+)["\']', section_content, re.IGNORECASE)
        section_id = section_id_match.group(1) if section_id_match else None
        
        # Extract chapter from section ID if not provided
        if not chapter and section_id:
            ch_match = re.match(r'(ch\d+)', section_id, re.IGNORECASE)
            if ch_match:
                chapter = ch_match.group(1).lower()
        
        # Parse the section to extract listitems
        entries = self._extract_list_entries(section_content)
        
        if not entries:
            return section_content, changes
        
        # Build new bibliography structure
        new_bibliography = self._build_bibliography(entries, chapter, section_id)
        
        changes.append({
            'type': 'structure_conversion',
            'original_section_id': section_id,
            'entries_converted': len(entries)
        })
        
        return new_bibliography, changes
    
    def _extract_list_entries(self, section_content: str) -> List[Dict]:
        """Extract entries from orderedlist/listitem structure."""
        entries = []
        
        # Pattern to match listitem elements
        listitem_pattern = re.compile(
            r'<listitem([^>]*)>([\s\S]*?)</listitem>',
            re.IGNORECASE
        )
        
        for match in listitem_pattern.finditer(section_content):
            attrs = match.group(1)
            content = match.group(2)
            
            # Extract ID
            id_match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            entry_id = id_match.group(1) if id_match else None
            
            # Extract role if present
            role_match = re.search(r'role\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            role = role_match.group(1) if role_match else None
            
            # Clean up the content - remove the duplicate number
            cleaned_content = self._clean_entry_content(content)
            
            entries.append({
                'id': entry_id,
                'role': role,
                'content': cleaned_content,
                'original_content': content
            })
        
        return entries
    
    def _clean_entry_content(self, content: str) -> str:
        """
        Clean entry content by removing duplicate numbering.
        
        Removes patterns like:
        - <para><emphasis role="strong">1</emphasis> Content
        - <para>1. Content
        - <para><strong>1</strong> Content
        """
        # Remove <para> wrapper temporarily
        para_match = re.match(r'^\s*<para[^>]*>([\s\S]*)</para>\s*$', content, re.IGNORECASE)
        if para_match:
            inner_content = para_match.group(1)
        else:
            inner_content = content
        
        # Remove emphasis/strong number at start
        # Pattern: <emphasis role="strong">1</emphasis> or <emphasis>1</emphasis>
        inner_content = re.sub(
            r'^\s*<emphasis[^>]*>\s*\d+\s*</emphasis>\s*',
            '',
            inner_content,
            flags=re.IGNORECASE
        )
        
        # Remove <strong>1</strong> pattern
        inner_content = re.sub(
            r'^\s*<strong[^>]*>\s*\d+\s*</strong>\s*',
            '',
            inner_content,
            flags=re.IGNORECASE
        )
        
        # Remove plain number at start like "1. " or "1 "
        inner_content = re.sub(
            r'^\s*\d+\.?\s+',
            '',
            inner_content
        )
        
        return inner_content.strip()
    
    def _build_bibliography(self, entries: List[Dict], chapter: Optional[str], original_section_id: Optional[str]) -> str:
        """Build the correct bibliography structure."""
        # Determine bibliography ID
        if chapter:
            bib_id = chapter
        elif original_section_id:
            # Extract chapter from section ID
            ch_match = re.match(r'(ch\d+)', original_section_id, re.IGNORECASE)
            bib_id = ch_match.group(1).lower() if ch_match else original_section_id
        else:
            bib_id = "references"
        
        lines = []
        lines.append(f'<bibliography id="{bib_id}">')
        lines.append('  <title>References</title>')
        lines.append('  <bibliodiv>')
        lines.append('    <title>Primary Sources</title>')
        
        for entry in entries:
            entry_id = entry['id'] if entry['id'] else ''
            content = entry['content']
            
            if entry_id:
                lines.append(f'    <bibliomixed id="{entry_id}">{content}</bibliomixed>')
            else:
                lines.append(f'    <bibliomixed>{content}</bibliomixed>')
        
        lines.append('  </bibliodiv>')
        lines.append('</bibliography>')
        
        return '\n'.join(lines)
    
    def _extract_chapter_from_filename(self, filename: str) -> Optional[str]:
        """Extract chapter identifier from filename."""
        if not filename:
            return None
        
        basename = os.path.basename(filename)
        
        match = re.search(r'(ch\d+)', basename, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        
        return None
    
    def analyze_bibliography_issues(self, content: str) -> List[Dict]:
        """
        Analyze content for bibliography structure issues.
        
        Returns list of issues found.
        """
        issues = []
        
        # Check for orderedlist in reference sections
        ref_sections = self.ref_section_pattern.findall(content)
        
        for section in ref_sections:
            if '<orderedlist' in section.lower():
                # Count listitems
                listitem_count = len(re.findall(r'<listitem', section, re.IGNORECASE))
                
                # Check for duplicate numbering
                has_emphasis_numbers = bool(re.search(
                    r'<emphasis[^>]*>\s*\d+\s*</emphasis>',
                    section,
                    re.IGNORECASE
                ))
                
                issues.append({
                    'type': 'wrong_structure',
                    'description': 'Reference section uses orderedlist instead of bibliography',
                    'entries': listitem_count,
                    'has_duplicate_numbers': has_emphasis_numbers
                })
        
        return issues
