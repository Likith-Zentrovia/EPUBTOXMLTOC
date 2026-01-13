"""
Link Fixer module for fixing broken or incorrect links in TOC files.

This module handles:
- Broken links pointing to non-existent files
- Incorrect fragment identifiers
- URL encoding issues
- Relative path corrections
- Duplicate link detection
"""

import os
import re
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class LinkFixer:
    """
    Fixes link issues in TOC structures.
    
    Features:
    - Validates links against actual files
    - Fixes URL encoding issues
    - Corrects relative paths
    - Suggests alternative links for broken ones
    - Handles fragment identifiers (#id)
    """
    
    def __init__(self, content_base_path: Optional[str] = None):
        """
        Initialize the Link Fixer.
        
        Args:
            content_base_path: Base path to the content directory for link validation.
        """
        self.content_base_path = content_base_path
        self._file_cache = {}  # Cache for file existence checks
        self._id_cache = {}    # Cache for ID lookups in files
    
    def fix_links(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix link issues in the TOC structure.
        
        Args:
            toc_structure: The parsed TOC structure.
            
        Returns:
            Fixed TOC structure with corrected links.
        """
        items = toc_structure.get('items', [])
        fixed_items = self._fix_items_links(items)
        
        fixed_structure = toc_structure.copy()
        fixed_structure['items'] = fixed_items
        
        return fixed_structure
    
    def analyze_issues(self, toc_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze TOC structure and return list of link issues.
        
        Args:
            toc_structure: The parsed TOC structure.
            
        Returns:
            List of link issues found.
        """
        issues = []
        items = toc_structure.get('items', [])
        
        self._analyze_items_links(items, issues)
        
        return issues
    
    def _fix_items_links(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fix links in items recursively."""
        fixed_items = []
        
        for item in items:
            fixed_item = item.copy()
            
            # Fix the href
            if item.get('href'):
                fixed_item['href'] = self._fix_link(item['href'])
            
            # Recursively fix children
            if item.get('children'):
                fixed_item['children'] = self._fix_items_links(item['children'])
            else:
                fixed_item['children'] = []
            
            fixed_items.append(fixed_item)
        
        return fixed_items
    
    def _analyze_items_links(self, items: List[Dict[str, Any]], issues: List[Dict[str, Any]]):
        """Analyze links in items recursively."""
        for item in items:
            href = item.get('href', '')
            title = item.get('title', '')
            
            if href:
                issue = self._check_link(href, title)
                if issue:
                    issues.append(issue)
            else:
                # Missing href
                issues.append({
                    'title': title,
                    'type': 'missing_link',
                    'description': 'Item has no href attribute',
                    'href': '',
                    'suggested_href': None
                })
            
            # Recursively check children
            if item.get('children'):
                self._analyze_items_links(item['children'], issues)
    
    def _fix_link(self, href: str) -> str:
        """
        Fix a single link.
        
        Args:
            href: The original href value.
            
        Returns:
            Fixed href value.
        """
        if not href:
            return href
        
        # Parse the URL
        parsed = urllib.parse.urlparse(href)
        
        # Skip external links
        if parsed.scheme in ('http', 'https', 'mailto', 'ftp'):
            return href
        
        # Fix URL encoding issues
        fixed_path = self._fix_url_encoding(parsed.path)
        
        # Fix fragment identifier
        fixed_fragment = self._fix_fragment(parsed.fragment)
        
        # Check if file exists and try to fix path
        if self.content_base_path and fixed_path:
            fixed_path = self._fix_file_path(fixed_path)
        
        # Reconstruct the URL
        fixed_href = fixed_path
        if fixed_fragment:
            fixed_href += '#' + fixed_fragment
        
        return fixed_href
    
    def _check_link(self, href: str, title: str) -> Optional[Dict[str, Any]]:
        """
        Check a link for issues.
        
        Returns issue dict if problems found, None otherwise.
        """
        if not href:
            return None
        
        # Parse the URL
        parsed = urllib.parse.urlparse(href)
        
        # Skip external links
        if parsed.scheme in ('http', 'https', 'mailto', 'ftp'):
            return None
        
        issues = []
        
        # Check for URL encoding issues
        if self._has_encoding_issues(href):
            issues.append('URL encoding issues')
        
        # Check for malformed fragment
        if parsed.fragment and not self._is_valid_fragment(parsed.fragment):
            issues.append(f'Invalid fragment identifier: {parsed.fragment}')
        
        # Check if file exists
        if self.content_base_path and parsed.path:
            file_path = os.path.join(self.content_base_path, parsed.path)
            if not self._file_exists(file_path):
                issues.append(f'File not found: {parsed.path}')
        
        # Check if fragment exists in file
        if self.content_base_path and parsed.path and parsed.fragment:
            if not self._fragment_exists(parsed.path, parsed.fragment):
                issues.append(f'Fragment #{parsed.fragment} not found in file')
        
        if issues:
            return {
                'title': title,
                'type': 'broken_link',
                'description': '; '.join(issues),
                'href': href,
                'suggested_href': self._suggest_fix(href)
            }
        
        return None
    
    def _fix_url_encoding(self, path: str) -> str:
        """Fix URL encoding issues in a path."""
        if not path:
            return path
        
        # Decode any existing encoding first
        try:
            decoded = urllib.parse.unquote(path)
        except Exception:
            decoded = path
        
        # Fix common issues
        # Replace spaces with %20
        fixed = decoded.replace(' ', '%20')
        
        # Handle special characters
        # Keep alphanumeric, hyphen, underscore, period, slash
        result = []
        for char in fixed:
            if char.isalnum() or char in '-_./%#':
                result.append(char)
            elif char == ' ':
                result.append('%20')
            else:
                result.append(urllib.parse.quote(char, safe=''))
        
        return ''.join(result)
    
    def _fix_fragment(self, fragment: str) -> str:
        """Fix fragment identifier issues."""
        if not fragment:
            return fragment
        
        # Remove invalid characters
        # Fragment IDs should start with letter and contain only alphanumeric, hyphen, underscore, period, colon
        fixed = re.sub(r'[^\w\-._:]', '', fragment)
        
        # Ensure it starts with a letter or underscore
        if fixed and not (fixed[0].isalpha() or fixed[0] == '_'):
            fixed = '_' + fixed
        
        return fixed
    
    def _fix_file_path(self, path: str) -> str:
        """
        Fix file path by finding the correct file.
        
        Tries various corrections:
        - Case sensitivity fixes
        - Extension variations
        - Path normalization
        """
        if not self.content_base_path:
            return path
        
        # Normalize path
        normalized = os.path.normpath(path)
        full_path = os.path.join(self.content_base_path, normalized)
        
        # Check if file exists as-is
        if self._file_exists(full_path):
            return path
        
        # Try case-insensitive search
        fixed_path = self._find_file_case_insensitive(normalized)
        if fixed_path:
            return fixed_path
        
        # Try common extension variations
        base, ext = os.path.splitext(normalized)
        extensions = ['.xhtml', '.html', '.htm', '.xml']
        
        for new_ext in extensions:
            test_path = base + new_ext
            if self._file_exists(os.path.join(self.content_base_path, test_path)):
                return test_path
        
        # Try without any extension changes
        return path
    
    def _find_file_case_insensitive(self, path: str) -> Optional[str]:
        """Find a file with case-insensitive matching."""
        if not self.content_base_path:
            return None
        
        parts = path.replace('\\', '/').split('/')
        current_path = self.content_base_path
        result_parts = []
        
        for part in parts:
            if not part:
                continue
            
            try:
                entries = os.listdir(current_path)
            except OSError:
                return None
            
            # Case-insensitive match
            matched = None
            for entry in entries:
                if entry.lower() == part.lower():
                    matched = entry
                    break
            
            if not matched:
                return None
            
            result_parts.append(matched)
            current_path = os.path.join(current_path, matched)
        
        return '/'.join(result_parts) if result_parts else None
    
    def _has_encoding_issues(self, href: str) -> bool:
        """Check if href has URL encoding issues."""
        # Check for unencoded spaces
        if ' ' in href.split('#')[0]:  # Ignore fragment
            return True
        
        # Check for double encoding
        if '%25' in href:
            return True
        
        # Check for malformed percent encoding
        if re.search(r'%[^0-9A-Fa-f]|%.[^0-9A-Fa-f]|%$|%.$', href):
            return True
        
        return False
    
    def _is_valid_fragment(self, fragment: str) -> bool:
        """Check if a fragment identifier is valid."""
        if not fragment:
            return True
        
        # Should start with letter or underscore
        if not (fragment[0].isalpha() or fragment[0] == '_'):
            return False
        
        # Should only contain valid characters
        return bool(re.match(r'^[\w\-._:]+$', fragment))
    
    def _file_exists(self, path: str) -> bool:
        """Check if a file exists (with caching)."""
        if path in self._file_cache:
            return self._file_cache[path]
        
        exists = os.path.isfile(path)
        self._file_cache[path] = exists
        return exists
    
    def _fragment_exists(self, file_path: str, fragment: str) -> bool:
        """Check if a fragment ID exists in a file."""
        if not self.content_base_path:
            return True  # Assume it exists if we can't check
        
        full_path = os.path.join(self.content_base_path, file_path)
        cache_key = (full_path, fragment)
        
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for id attribute
            patterns = [
                rf'id\s*=\s*["\']?{re.escape(fragment)}["\'\s>]',
                rf'name\s*=\s*["\']?{re.escape(fragment)}["\'\s>]',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    self._id_cache[cache_key] = True
                    return True
            
            self._id_cache[cache_key] = False
            return False
            
        except (OSError, IOError):
            return True  # Assume it exists if we can't read the file
    
    def _suggest_fix(self, href: str) -> Optional[str]:
        """Suggest a fix for a broken link."""
        return self._fix_link(href)
    
    def normalize_links(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all links in the TOC.
        
        This ensures consistent formatting:
        - Consistent path separators
        - Consistent URL encoding
        - Relative paths normalized
        """
        items = toc_structure.get('items', [])
        normalized_items = self._normalize_items_links(items)
        
        normalized_structure = toc_structure.copy()
        normalized_structure['items'] = normalized_items
        
        return normalized_structure
    
    def _normalize_items_links(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize links in items recursively."""
        normalized_items = []
        
        for item in items:
            normalized_item = item.copy()
            
            if item.get('href'):
                normalized_item['href'] = self._normalize_link(item['href'])
            
            if item.get('children'):
                normalized_item['children'] = self._normalize_items_links(item['children'])
            else:
                normalized_item['children'] = []
            
            normalized_items.append(normalized_item)
        
        return normalized_items
    
    def _normalize_link(self, href: str) -> str:
        """Normalize a single link."""
        if not href:
            return href
        
        parsed = urllib.parse.urlparse(href)
        
        # Skip external links
        if parsed.scheme in ('http', 'https', 'mailto', 'ftp'):
            return href
        
        # Normalize path
        path = parsed.path
        if path:
            # Use forward slashes
            path = path.replace('\\', '/')
            
            # Remove redundant slashes
            path = re.sub(r'/+', '/', path)
            
            # Normalize relative paths
            path = os.path.normpath(path).replace('\\', '/')
        
        # Reconstruct
        result = path
        if parsed.fragment:
            result += '#' + parsed.fragment
        
        return result
    
    def deduplicate_links(self, toc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove duplicate entries with the same link.
        
        Keeps the first occurrence and removes subsequent duplicates.
        """
        items = toc_structure.get('items', [])
        seen_links = set()
        deduped_items = self._deduplicate_items(items, seen_links)
        
        deduped_structure = toc_structure.copy()
        deduped_structure['items'] = deduped_items
        
        return deduped_structure
    
    def _deduplicate_items(self, items: List[Dict[str, Any]], seen: set) -> List[Dict[str, Any]]:
        """Remove duplicate items recursively."""
        result = []
        
        for item in items:
            href = item.get('href', '')
            
            # Check for duplicate
            if href and href in seen:
                continue
            
            if href:
                seen.add(href)
            
            new_item = item.copy()
            if item.get('children'):
                new_item['children'] = self._deduplicate_items(item['children'], seen)
            else:
                new_item['children'] = []
            
            result.append(new_item)
        
        return result
    
    def map_links(self, toc_structure: Dict[str, Any], link_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Apply a link mapping to update hrefs.
        
        Args:
            toc_structure: The TOC structure.
            link_mapping: Dictionary mapping old hrefs to new hrefs.
            
        Returns:
            Updated TOC structure.
        """
        items = toc_structure.get('items', [])
        mapped_items = self._map_items_links(items, link_mapping)
        
        mapped_structure = toc_structure.copy()
        mapped_structure['items'] = mapped_items
        
        return mapped_structure
    
    def _map_items_links(self, items: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Apply link mapping to items recursively."""
        mapped_items = []
        
        for item in items:
            mapped_item = item.copy()
            
            href = item.get('href', '')
            if href and href in mapping:
                mapped_item['href'] = mapping[href]
            
            if item.get('children'):
                mapped_item['children'] = self._map_items_links(item['children'], mapping)
            else:
                mapped_item['children'] = []
            
            mapped_items.append(mapped_item)
        
        return mapped_items
