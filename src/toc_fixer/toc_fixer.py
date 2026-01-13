"""
Main TOC Fixer module that orchestrates the TOC fixing process.
"""

import os
import re
from typing import Optional, Dict, List, Any
from lxml import etree
from pathlib import Path

from .ncx_parser import NCXParser
from .nav_parser import NavParser
from .nesting_fixer import NestingFixer
from .link_fixer import LinkFixer


class TOCFixer:
    """
    Main class to fix TOC XML files with nesting and link issues.
    
    Supports:
    - EPUB 2 NCX format (.ncx)
    - EPUB 3 Navigation Document format (.xhtml, .html)
    - Generic TOC XML structures
    """
    
    def __init__(self, content_base_path: Optional[str] = None):
        """
        Initialize the TOC Fixer.
        
        Args:
            content_base_path: Base path to the EPUB content directory for link validation.
                              If provided, links will be validated against actual files.
        """
        self.content_base_path = content_base_path
        self.ncx_parser = NCXParser()
        self.nav_parser = NavParser()
        self.nesting_fixer = NestingFixer()
        self.link_fixer = LinkFixer(content_base_path)
        
    def detect_format(self, xml_content: str) -> str:
        """
        Detect the format of the TOC XML.
        
        Args:
            xml_content: The XML content as a string.
            
        Returns:
            Format type: 'ncx', 'nav', or 'generic'
        """
        content_lower = xml_content.lower()
        
        # Check for NCX format
        if '<ncx' in content_lower or 'navmap' in content_lower:
            return 'ncx'
        
        # Check for EPUB 3 Nav format
        if '<nav' in content_lower and ('epub:type' in content_lower or 'toc' in content_lower):
            return 'nav'
        
        # Generic TOC XML
        return 'generic'
    
    def fix_from_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Fix a TOC XML file and optionally save to a new file.
        
        Args:
            input_path: Path to the input TOC XML file.
            output_path: Optional path to save the fixed TOC. If not provided,
                        returns the fixed content without saving.
                        
        Returns:
            The fixed TOC XML content as a string.
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Update content base path if not set
        if not self.content_base_path:
            self.content_base_path = os.path.dirname(os.path.abspath(input_path))
            self.link_fixer.content_base_path = self.content_base_path
        
        fixed_content = self.fix(xml_content)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
        
        return fixed_content
    
    def fix(self, xml_content: str) -> str:
        """
        Fix the TOC XML content.
        
        Args:
            xml_content: The TOC XML content as a string.
            
        Returns:
            The fixed TOC XML content.
        """
        # Detect format
        format_type = self.detect_format(xml_content)
        
        if format_type == 'ncx':
            return self._fix_ncx(xml_content)
        elif format_type == 'nav':
            return self._fix_nav(xml_content)
        else:
            return self._fix_generic(xml_content)
    
    def _fix_ncx(self, xml_content: str) -> str:
        """Fix NCX format TOC."""
        # Parse the NCX
        toc_structure = self.ncx_parser.parse(xml_content)
        
        # Fix nesting
        fixed_structure = self.nesting_fixer.fix_nesting(toc_structure)
        
        # Fix links
        fixed_structure = self.link_fixer.fix_links(fixed_structure)
        
        # Rebuild NCX
        return self.ncx_parser.build(fixed_structure, xml_content)
    
    def _fix_nav(self, xml_content: str) -> str:
        """Fix EPUB 3 Nav format TOC."""
        # Parse the Nav document
        toc_structure = self.nav_parser.parse(xml_content)
        
        # Fix nesting
        fixed_structure = self.nesting_fixer.fix_nesting(toc_structure)
        
        # Fix links
        fixed_structure = self.link_fixer.fix_links(fixed_structure)
        
        # Rebuild Nav document
        return self.nav_parser.build(fixed_structure, xml_content)
    
    def _fix_generic(self, xml_content: str) -> str:
        """Fix generic TOC XML format."""
        # Parse as generic structure
        toc_structure = self._parse_generic(xml_content)
        
        # Fix nesting
        fixed_structure = self.nesting_fixer.fix_nesting(toc_structure)
        
        # Fix links
        fixed_structure = self.link_fixer.fix_links(fixed_structure)
        
        # Rebuild generic XML
        return self._build_generic(fixed_structure, xml_content)
    
    def _parse_generic(self, xml_content: str) -> Dict[str, Any]:
        """Parse generic TOC XML into a structured format."""
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
        except etree.XMLSyntaxError:
            # Try with HTML parser for malformed XML
            parser = etree.HTMLParser()
            root = etree.fromstring(xml_content.encode('utf-8'), parser)
        
        items = self._extract_generic_items(root)
        
        return {
            'title': self._find_title(root),
            'items': items,
            'metadata': {}
        }
    
    def _extract_generic_items(self, element, depth: int = 0) -> List[Dict[str, Any]]:
        """Extract TOC items from generic XML structure."""
        items = []
        
        # Look for common TOC patterns
        for child in element:
            tag = etree.QName(child).localname if isinstance(child.tag, str) else str(child.tag)
            
            # Check for item-like elements
            if tag.lower() in ['item', 'entry', 'chapter', 'section', 'navpoint', 'li', 'a']:
                item = self._parse_generic_item(child, depth)
                if item:
                    items.append(item)
            else:
                # Recursively check children
                child_items = self._extract_generic_items(child, depth)
                items.extend(child_items)
        
        return items
    
    def _parse_generic_item(self, element, depth: int) -> Optional[Dict[str, Any]]:
        """Parse a single TOC item from generic XML."""
        # Try to extract title
        title = None
        href = None
        
        # Check element text
        if element.text and element.text.strip():
            title = element.text.strip()
        
        # Check for href attribute
        href = element.get('href') or element.get('src') or element.get('link')
        
        # Look for nested elements
        for child in element:
            tag = etree.QName(child).localname if isinstance(child.tag, str) else str(child.tag)
            
            if tag.lower() in ['title', 'text', 'label', 'navlabel']:
                if child.text and child.text.strip():
                    title = child.text.strip()
                # Check for nested text element
                for subchild in child:
                    if subchild.text and subchild.text.strip():
                        title = subchild.text.strip()
            
            if tag.lower() in ['a', 'link', 'content']:
                href = child.get('href') or child.get('src') or href
                if child.text and child.text.strip() and not title:
                    title = child.text.strip()
        
        if not title:
            return None
        
        # Extract children
        children = []
        for child in element:
            tag = etree.QName(child).localname if isinstance(child.tag, str) else str(child.tag)
            if tag.lower() in ['ol', 'ul', 'children', 'items']:
                children = self._extract_generic_items(child, depth + 1)
            elif tag.lower() in ['item', 'entry', 'chapter', 'section', 'navpoint', 'li']:
                child_item = self._parse_generic_item(child, depth + 1)
                if child_item:
                    children.append(child_item)
        
        return {
            'id': element.get('id') or f'item_{hash(title) % 10000}',
            'title': title,
            'href': href,
            'level': depth,
            'children': children
        }
    
    def _find_title(self, root) -> str:
        """Find the document title."""
        # Common title element names
        for tag in ['title', 'docTitle', 'head/title']:
            elem = root.find(f'.//{tag}', namespaces=None)
            if elem is not None and elem.text:
                return elem.text.strip()
        return "Table of Contents"
    
    def _build_generic(self, toc_structure: Dict[str, Any], original_xml: str) -> str:
        """Rebuild generic TOC XML from structure."""
        # Create root element
        root = etree.Element('toc')
        
        # Add title
        title_elem = etree.SubElement(root, 'title')
        title_elem.text = toc_structure.get('title', 'Table of Contents')
        
        # Add items
        items_elem = etree.SubElement(root, 'items')
        self._build_generic_items(items_elem, toc_structure.get('items', []))
        
        # Format output
        return etree.tostring(root, encoding='unicode', pretty_print=True, 
                             xml_declaration=True)
    
    def _build_generic_items(self, parent, items: List[Dict[str, Any]]):
        """Build generic XML items recursively."""
        for item in items:
            item_elem = etree.SubElement(parent, 'item')
            item_elem.set('id', item.get('id', ''))
            
            # Add title
            title_elem = etree.SubElement(item_elem, 'title')
            title_elem.text = item.get('title', '')
            
            # Add link if present
            if item.get('href'):
                link_elem = etree.SubElement(item_elem, 'link')
                link_elem.set('href', item['href'])
            
            # Add children
            if item.get('children'):
                children_elem = etree.SubElement(item_elem, 'children')
                self._build_generic_items(children_elem, item['children'])
    
    def get_report(self, xml_content: str) -> Dict[str, Any]:
        """
        Generate a report of issues found in the TOC XML.
        
        Args:
            xml_content: The TOC XML content.
            
        Returns:
            Dictionary with issues found and statistics.
        """
        format_type = self.detect_format(xml_content)
        
        # Parse based on format
        if format_type == 'ncx':
            toc_structure = self.ncx_parser.parse(xml_content)
        elif format_type == 'nav':
            toc_structure = self.nav_parser.parse(xml_content)
        else:
            toc_structure = self._parse_generic(xml_content)
        
        # Get nesting issues
        nesting_issues = self.nesting_fixer.analyze_issues(toc_structure)
        
        # Get link issues
        link_issues = self.link_fixer.analyze_issues(toc_structure)
        
        return {
            'format': format_type,
            'total_items': self._count_items(toc_structure.get('items', [])),
            'nesting_issues': nesting_issues,
            'link_issues': link_issues,
            'severity': 'high' if (nesting_issues or link_issues) else 'none'
        }
    
    def _count_items(self, items: List[Dict[str, Any]]) -> int:
        """Count total items including nested ones."""
        count = len(items)
        for item in items:
            count += self._count_items(item.get('children', []))
        return count
