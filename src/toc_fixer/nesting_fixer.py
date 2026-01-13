"""
Nesting Fixer module for fixing TOC hierarchy issues.

This module handles:
- Incorrect nesting levels (e.g., flat structures that should be hierarchical)
- Chapters, sections, and subsections detection based on title patterns
- Orphaned items that should be nested under parent items
- Duplicate nesting issues
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NestingIssue:
    """Represents a nesting issue found in the TOC."""
    item_title: str
    issue_type: str
    description: str
    suggested_level: int
    current_level: int


class NestingFixer:
    """
    Fixes nesting issues in TOC structures.
    
    Features:
    - Detects chapters, sections, and subsections by title patterns
    - Fixes flat structures into proper hierarchies
    - Handles orphaned items
    - Maintains logical ordering
    """
    
    # Patterns to detect chapter-level items
    CHAPTER_PATTERNS = [
        r'^chapter\s+\d+',
        r'^ch\.?\s*\d+',
        r'^part\s+\d+',
        r'^book\s+\d+',
        r'^unit\s+\d+',
        r'^module\s+\d+',
        r'^\d+\.\s+[A-Z]',  # "1. Title" style
        r'^[IVXLCDM]+\.\s+',  # Roman numerals
    ]
    
    # Patterns to detect section-level items
    SECTION_PATTERNS = [
        r'^section\s+\d+',
        r'^sec\.?\s*\d+',
        r'^\d+\.\d+\s+',  # "1.1 Title" style
        r'^[A-Z]\.\s+',  # "A. Title" style
        r'^lesson\s+\d+',
    ]
    
    # Patterns to detect subsection-level items
    SUBSECTION_PATTERNS = [
        r'^subsection\s+\d+',
        r'^\d+\.\d+\.\d+\s+',  # "1.1.1 Title" style
        r'^[a-z]\)\s+',  # "a) Title" style
        r'^\(\d+\)\s+',  # "(1) Title" style
    ]
    
    # Special items that should stay at top level
    TOP_LEVEL_ITEMS = [
        'cover',
        'title page',
        'copyright',
        'dedication',
        'acknowledgments',
        'acknowledgements',
        'preface',
        'foreword',
        'introduction',
        'prologue',
        'contents',
        'table of contents',
        'epilogue',
        'afterword',
        'appendix',
        'appendices',
        'glossary',
        'bibliography',
        'references',
        'index',
        'about the author',
        'colophon',
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self.chapter_re = [re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS]
        self.section_re = [re.compile(p, re.IGNORECASE) for p in self.SECTION_PATTERNS]
        self.subsection_re = [re.compile(p, re.IGNORECASE) for p in self.SUBSECTION_PATTERNS]
    
    def fix_nesting(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix nesting issues in the TOC structure.
        
        Args:
            toc_structure: The parsed TOC structure.
            
        Returns:
            Fixed TOC structure with proper nesting.
        """
        items = toc_structure.get('items', [])
        
        # First, flatten the structure to analyze it
        flat_items = self._flatten_items(items)
        
        # Detect the intended level for each item
        items_with_levels = self._detect_levels(flat_items)
        
        # Rebuild hierarchy based on detected levels
        fixed_items = self._rebuild_hierarchy(items_with_levels)
        
        # Create fixed structure
        fixed_structure = toc_structure.copy()
        fixed_structure['items'] = fixed_items
        
        return fixed_structure
    
    def analyze_issues(self, toc_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze TOC structure and return list of nesting issues.
        
        Args:
            toc_structure: The parsed TOC structure.
            
        Returns:
            List of issues found.
        """
        issues = []
        items = toc_structure.get('items', [])
        
        # Flatten and analyze
        flat_items = self._flatten_items(items)
        items_with_levels = self._detect_levels(flat_items)
        
        for item, detected_level in items_with_levels:
            current_level = item.get('level', 0)
            
            if detected_level != current_level:
                issues.append({
                    'title': item.get('title', ''),
                    'type': 'incorrect_level',
                    'description': f"Item should be at level {detected_level} but is at level {current_level}",
                    'current_level': current_level,
                    'suggested_level': detected_level
                })
        
        # Check for orphaned items
        orphans = self._find_orphaned_items(items)
        for orphan in orphans:
            issues.append({
                'title': orphan.get('title', ''),
                'type': 'orphaned_item',
                'description': "Item appears to be orphaned and should be nested under a parent",
                'current_level': orphan.get('level', 0),
                'suggested_level': orphan.get('level', 0) + 1
            })
        
        return issues
    
    def _flatten_items(self, items: List[Dict[str, Any]], level: int = 0) -> List[Dict[str, Any]]:
        """Flatten nested items into a single list with level information."""
        flat = []
        
        for item in items:
            flat_item = item.copy()
            flat_item['level'] = level
            flat_item['children'] = []  # Clear children for flat representation
            flat.append(flat_item)
            
            # Recursively flatten children
            if item.get('children'):
                flat.extend(self._flatten_items(item['children'], level + 1))
        
        return flat
    
    def _detect_levels(self, flat_items: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int]]:
        """
        Detect the intended nesting level for each item.
        
        Returns list of (item, detected_level) tuples.
        """
        results = []
        
        for item in flat_items:
            title = item.get('title', '').strip()
            
            # Check if it's a top-level item
            if self._is_top_level(title):
                results.append((item, 0))
                continue
            
            # Check for chapter pattern
            if self._matches_pattern(title, self.chapter_re):
                results.append((item, 0))
                continue
            
            # Check for section pattern
            if self._matches_pattern(title, self.section_re):
                results.append((item, 1))
                continue
            
            # Check for subsection pattern
            if self._matches_pattern(title, self.subsection_re):
                results.append((item, 2))
                continue
            
            # Try to infer from numbering pattern
            inferred_level = self._infer_level_from_numbering(title)
            if inferred_level is not None:
                results.append((item, inferred_level))
                continue
            
            # Keep existing level if no pattern matches
            results.append((item, item.get('level', 0)))
        
        return results
    
    def _is_top_level(self, title: str) -> bool:
        """Check if the title indicates a top-level item."""
        title_lower = title.lower().strip()
        
        for top_item in self.TOP_LEVEL_ITEMS:
            if title_lower == top_item or title_lower.startswith(top_item + ' '):
                return True
        
        return False
    
    def _matches_pattern(self, title: str, patterns: List[re.Pattern]) -> bool:
        """Check if title matches any of the given patterns."""
        for pattern in patterns:
            if pattern.search(title):
                return True
        return False
    
    def _infer_level_from_numbering(self, title: str) -> Optional[int]:
        """
        Infer nesting level from numbering pattern in title.
        
        Examples:
        - "1. Title" -> level 0
        - "1.1 Title" -> level 1
        - "1.1.1 Title" -> level 2
        """
        # Match numbered patterns
        match = re.match(r'^(\d+(?:\.\d+)*)[.\s]', title)
        if match:
            number_part = match.group(1)
            # Count dots to determine level
            level = number_part.count('.')
            return min(level, 3)  # Cap at level 3
        
        return None
    
    def _find_orphaned_items(self, items: List[Dict[str, Any]], parent_level: int = -1) -> List[Dict[str, Any]]:
        """Find items that appear to be orphaned (wrong nesting)."""
        orphans = []
        
        for i, item in enumerate(items):
            # Check if item looks like it should be nested but isn't
            title = item.get('title', '').strip()
            
            # If it looks like a subsection but is at top level
            if parent_level == -1 and self._matches_pattern(title, self.subsection_re):
                orphans.append(item)
            
            # Recursively check children
            if item.get('children'):
                orphans.extend(self._find_orphaned_items(item['children'], item.get('level', 0)))
        
        return orphans
    
    def _rebuild_hierarchy(self, items_with_levels: List[Tuple[Dict[str, Any], int]]) -> List[Dict[str, Any]]:
        """
        Rebuild TOC hierarchy based on detected levels.
        
        Uses a stack-based approach to properly nest items.
        """
        if not items_with_levels:
            return []
        
        # Create clean copies of items
        processed_items = []
        for item, level in items_with_levels:
            new_item = item.copy()
            new_item['level'] = level
            new_item['children'] = []
            processed_items.append((new_item, level))
        
        # Build hierarchy using stack
        root = []
        stack = [(root, -1)]  # (children_list, level)
        
        for item, level in processed_items:
            # Pop stack until we find the right parent
            while len(stack) > 1 and stack[-1][1] >= level:
                stack.pop()
            
            # Add item to current parent's children
            parent_children = stack[-1][0]
            parent_children.append(item)
            
            # Push this item onto stack as potential parent
            stack.append((item['children'], level))
        
        return root
    
    def fix_numbering_sequence(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix numbering sequence issues in the TOC.
        
        This ensures chapters are numbered 1, 2, 3... and sections follow properly.
        """
        items = toc_structure.get('items', [])
        fixed_items = self._renumber_items(items)
        
        fixed_structure = toc_structure.copy()
        fixed_structure['items'] = fixed_items
        
        return fixed_structure
    
    def _renumber_items(self, items: List[Dict[str, Any]], prefix: str = "") -> List[Dict[str, Any]]:
        """Renumber items recursively."""
        result = []
        chapter_count = 0
        
        for item in items:
            new_item = item.copy()
            title = item.get('title', '')
            
            # Check if this is a numbered item
            match = re.match(r'^(\d+(?:\.\d+)*)[.\s]+(.+)$', title)
            if match:
                chapter_count += 1
                if prefix:
                    new_number = f"{prefix}.{chapter_count}"
                else:
                    new_number = str(chapter_count)
                
                new_item['title'] = f"{new_number}. {match.group(2)}"
            
            # Recursively fix children
            if item.get('children'):
                new_item['children'] = self._renumber_items(
                    item['children'],
                    prefix=new_number if match else prefix
                )
            else:
                new_item['children'] = []
            
            result.append(new_item)
        
        return result
    
    def merge_duplicate_entries(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge duplicate TOC entries that have the same title and href.
        """
        items = toc_structure.get('items', [])
        merged_items = self._merge_duplicates(items)
        
        merged_structure = toc_structure.copy()
        merged_structure['items'] = merged_items
        
        return merged_structure
    
    def _merge_duplicates(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge duplicate items recursively."""
        seen = {}
        result = []
        
        for item in items:
            key = (item.get('title', ''), item.get('href', ''))
            
            if key in seen:
                # Merge children
                existing = seen[key]
                if item.get('children'):
                    existing_children = existing.get('children', [])
                    existing['children'] = existing_children + item['children']
            else:
                new_item = item.copy()
                if item.get('children'):
                    new_item['children'] = self._merge_duplicates(item['children'])
                else:
                    new_item['children'] = []
                
                seen[key] = new_item
                result.append(new_item)
        
        return result
