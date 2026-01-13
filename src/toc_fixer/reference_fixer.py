"""
Reference/Bibliography Fixer module.

Ensures bibliography entries have correct IDs that match citation links.
Also fixes bibliography structure if needed.

Expected structure:
<bibliography id="ch0020">
  <title>References</title>
  <bibliodiv>
    <title>Primary Sources</title>
    <bibliomixed id="ch0020-bib0001">[Entry 1 content]</bibliomixed>
    <bibliomixed id="ch0020-bib0002">[Entry 2 content]</bibliomixed>
  </bibliodiv>
</bibliography>
"""

import re
import os
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path


class ReferenceFixer:
    """
    Fixes bibliography/reference sections to ensure proper ID structure
    that matches citation links.
    """
    
    def __init__(self):
        # Pattern to find bibliography/references sections
        self.bibliography_pattern = re.compile(
            r'<bibliography[^>]*>.*?</bibliography>',
            re.DOTALL | re.IGNORECASE
        )
        
        # Pattern to find bibliomixed/biblioentry elements
        self.bibentry_pattern = re.compile(
            r'<(bibliomixed|biblioentry)([^>]*)>(.*?)</\1>',
            re.DOTALL | re.IGNORECASE
        )
        
        # Pattern to extract ID from attributes
        self.id_pattern = re.compile(r'id\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        
        # Pattern to find citation references in content
        self.citation_pattern = re.compile(
            r'<citation>([^<]+)</citation>',
            re.IGNORECASE
        )
        
        # Pattern to find ulink references (already converted citations)
        self.ulink_ref_pattern = re.compile(
            r'<ulink\s+url="[^#]*#([^"]+)"',
            re.IGNORECASE
        )
    
    def fix_references_in_content(self, content: str, filename: str = "") -> Tuple[str, List[Dict]]:
        """
        Fix bibliography/reference sections in the content.
        
        Args:
            content: The XML content as a string.
            filename: Optional filename for context.
            
        Returns:
            Tuple of (fixed_content, list_of_changes)
        """
        changes = []
        chapter = self._extract_chapter_from_filename(filename)
        
        # Find all bibliography sections
        def fix_bibliography(match):
            bib_content = match.group(0)
            fixed_bib, bib_changes = self._fix_bibliography_section(bib_content, chapter)
            changes.extend(bib_changes)
            return fixed_bib
        
        fixed_content = self.bibliography_pattern.sub(fix_bibliography, content)
        
        # Also fix any standalone bibliomixed/biblioentry elements
        fixed_content = self._fix_standalone_entries(fixed_content, chapter, changes)
        
        return fixed_content, changes
    
    def _fix_bibliography_section(self, bib_content: str, chapter: Optional[str]) -> Tuple[str, List[Dict]]:
        """Fix a single bibliography section."""
        changes = []
        
        # Extract bibliography ID to determine chapter if not provided
        bib_id_match = re.search(r'<bibliography[^>]*id\s*=\s*["\']([^"\']+)["\']', bib_content, re.IGNORECASE)
        if bib_id_match:
            bib_id = bib_id_match.group(1)
            # Extract chapter from bibliography ID (e.g., ch0020)
            ch_match = re.match(r'(ch\d+)', bib_id, re.IGNORECASE)
            if ch_match:
                chapter = ch_match.group(1).lower()
        
        # Counter for entries without proper IDs
        entry_counter = 1
        
        def fix_entry(match):
            nonlocal entry_counter
            tag = match.group(1)
            attrs = match.group(2)
            content = match.group(3)
            original = match.group(0)
            
            # Check if ID exists
            id_match = self.id_pattern.search(attrs)
            
            if id_match:
                current_id = id_match.group(1)
                # Check if ID needs fixing (should be like ch0020-bib0001)
                new_id = self._normalize_bib_id(current_id, chapter, entry_counter)
                
                if new_id != current_id:
                    # Replace ID in attributes
                    new_attrs = self.id_pattern.sub(f'id="{new_id}"', attrs)
                    replacement = f'<{tag}{new_attrs}>{content}</{tag}>'
                    changes.append({
                        'type': 'id_fix',
                        'original_id': current_id,
                        'new_id': new_id,
                        'entry_num': entry_counter
                    })
                    entry_counter += 1
                    return replacement
            else:
                # No ID - add one
                new_id = f"{chapter}-bib{entry_counter:04d}" if chapter else f"bib{entry_counter:04d}"
                new_attrs = f' id="{new_id}"' + attrs
                replacement = f'<{tag}{new_attrs}>{content}</{tag}>'
                changes.append({
                    'type': 'id_add',
                    'new_id': new_id,
                    'entry_num': entry_counter
                })
                entry_counter += 1
                return replacement
            
            entry_counter += 1
            return original
        
        fixed_content = self.bibentry_pattern.sub(fix_entry, bib_content)
        
        return fixed_content, changes
    
    def _fix_standalone_entries(self, content: str, chapter: Optional[str], changes: List[Dict]) -> str:
        """Fix standalone bibliography entries outside of bibliography tags."""
        # This handles cases where entries might be outside main bibliography section
        entry_counter = 1000  # Start high to avoid conflicts
        
        def fix_entry(match):
            nonlocal entry_counter
            tag = match.group(1)
            attrs = match.group(2)
            entry_content = match.group(3)
            
            id_match = self.id_pattern.search(attrs)
            if id_match:
                current_id = id_match.group(1)
                new_id = self._normalize_bib_id(current_id, chapter, entry_counter)
                
                if new_id != current_id:
                    new_attrs = self.id_pattern.sub(f'id="{new_id}"', attrs)
                    entry_counter += 1
                    return f'<{tag}{new_attrs}>{entry_content}</{tag}>'
            
            entry_counter += 1
            return match.group(0)
        
        return self.bibentry_pattern.sub(fix_entry, content)
    
    def _normalize_bib_id(self, current_id: str, chapter: Optional[str], entry_num: int) -> str:
        """
        Normalize a bibliography ID to standard format.
        
        Standard format: ch0020-bib0001
        
        Input variations handled:
        - ch0011-c1-bib-0001 -> ch0011-bib0001
        - bib0001 -> ch0020-bib0001 (if chapter known)
        - ch0011-bib-0001 -> ch0011-bib0001
        - ref0001 -> ch0020-bib0001
        """
        # Extract chapter from ID if present
        ch_match = re.match(r'(ch\d+)', current_id, re.IGNORECASE)
        id_chapter = ch_match.group(1).lower() if ch_match else chapter
        
        # Extract the number
        num_match = re.search(r'(\d+)$', current_id)
        if num_match:
            num = int(num_match.group(1))
        else:
            num = entry_num
        
        # Build normalized ID
        if id_chapter:
            return f"{id_chapter}-bib{num:04d}"
        else:
            return f"bib{num:04d}"
    
    def _extract_chapter_from_filename(self, filename: str) -> Optional[str]:
        """Extract chapter identifier from filename."""
        if not filename:
            return None
        
        basename = os.path.basename(filename)
        
        patterns = [
            re.compile(r'(ch\d+)', re.IGNORECASE),
            re.compile(r'chapter(\d+)', re.IGNORECASE),
        ]
        
        for pattern in patterns:
            match = pattern.search(basename)
            if match:
                if 'chapter' in pattern.pattern.lower():
                    return f"ch{int(match.group(1)):04d}"
                return match.group(1).lower()
        
        return None
    
    def collect_citation_refs(self, content: str) -> Set[str]:
        """
        Collect all citation reference IDs from content.
        
        Returns set of reference IDs that are being linked to.
        """
        refs = set()
        
        # From citation tags
        for match in self.citation_pattern.finditer(content):
            refs.add(match.group(1).strip())
        
        # From ulink tags (already converted)
        for match in self.ulink_ref_pattern.finditer(content):
            refs.add(match.group(1))
        
        return refs
    
    def collect_bib_ids(self, content: str) -> Set[str]:
        """
        Collect all bibliography entry IDs from content.
        
        Returns set of IDs defined in bibliography entries.
        """
        ids = set()
        
        for match in self.bibentry_pattern.finditer(content):
            attrs = match.group(2)
            id_match = self.id_pattern.search(attrs)
            if id_match:
                ids.add(id_match.group(1))
        
        return ids
    
    def create_id_mapping(self, citation_refs: Set[str], bib_ids: Set[str]) -> Dict[str, str]:
        """
        Create a mapping from citation reference IDs to bibliography IDs.
        
        This helps match citations like 'ch0011-c1-bib-0001' to 
        bibliography entries like 'ch0011-bib0001'.
        """
        mapping = {}
        
        for ref in citation_refs:
            # Normalize the reference ID
            normalized = self._normalize_bib_id(ref, None, 0)
            
            # Check if normalized version exists in bib_ids
            if normalized in bib_ids:
                mapping[ref] = normalized
            elif ref in bib_ids:
                mapping[ref] = ref
            else:
                # Try to find a matching bib ID
                ref_num_match = re.search(r'(\d+)$', ref)
                if ref_num_match:
                    ref_num = ref_num_match.group(1).lstrip('0') or '0'
                    for bib_id in bib_ids:
                        bib_num_match = re.search(r'(\d+)$', bib_id)
                        if bib_num_match:
                            bib_num = bib_num_match.group(1).lstrip('0') or '0'
                            if ref_num == bib_num:
                                # Check chapter match
                                ref_ch = re.match(r'(ch\d+)', ref, re.IGNORECASE)
                                bib_ch = re.match(r'(ch\d+)', bib_id, re.IGNORECASE)
                                if ref_ch and bib_ch and ref_ch.group(1).lower() == bib_ch.group(1).lower():
                                    mapping[ref] = bib_id
                                    break
        
        return mapping


class CitationReferenceMatcher:
    """
    Matches citations to their bibliography entries and fixes both to ensure
    links work correctly.
    """
    
    def __init__(self):
        self.ref_fixer = ReferenceFixer()
    
    def fix_all(self, content: str, filename: str = "") -> Tuple[str, Dict]:
        """
        Fix both citations and references in content to ensure they match.
        
        Args:
            content: XML content
            filename: Optional filename for context
            
        Returns:
            Tuple of (fixed_content, report)
        """
        report = {
            'citations_found': 0,
            'references_fixed': 0,
            'id_mappings': {}
        }
        
        # First, collect all citation references
        citation_refs = self.ref_fixer.collect_citation_refs(content)
        report['citations_found'] = len(citation_refs)
        
        # Fix bibliography entries
        fixed_content, ref_changes = self.ref_fixer.fix_references_in_content(content, filename)
        report['references_fixed'] = len(ref_changes)
        
        # Collect bibliography IDs after fixing
        bib_ids = self.ref_fixer.collect_bib_ids(fixed_content)
        
        # Create mapping
        mapping = self.ref_fixer.create_id_mapping(citation_refs, bib_ids)
        report['id_mappings'] = mapping
        
        return fixed_content, report
