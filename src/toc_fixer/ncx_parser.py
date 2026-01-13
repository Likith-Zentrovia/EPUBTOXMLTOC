"""
NCX Parser for EPUB 2 Navigation Control for XML format.
"""

import re
from typing import Dict, List, Any, Optional
from lxml import etree

# NCX namespace
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
NSMAP = {'ncx': NCX_NS}


class NCXParser:
    """
    Parser for EPUB 2 NCX (Navigation Control for XML) files.
    """
    
    def __init__(self):
        self.nsmap = NSMAP
        self.play_order_counter = 1
    
    def parse(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse NCX XML content into a structured dictionary.
        
        Args:
            xml_content: The NCX XML content as a string.
            
        Returns:
            Dictionary containing the TOC structure.
        """
        # Clean up the XML content
        xml_content = self._clean_xml(xml_content)
        
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            # Try to fix common XML issues
            xml_content = self._fix_xml_issues(xml_content)
            root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Extract metadata
        metadata = self._parse_metadata(root)
        
        # Extract document title
        doc_title = self._parse_doc_title(root)
        
        # Extract navMap items
        items = self._parse_nav_map(root)
        
        return {
            'title': doc_title,
            'metadata': metadata,
            'items': items,
            'original_root': root
        }
    
    def _clean_xml(self, xml_content: str) -> str:
        """Clean up common XML issues."""
        # Remove BOM if present
        xml_content = xml_content.lstrip('\ufeff')
        
        # Fix common encoding issues
        xml_content = xml_content.replace('&nbsp;', '&#160;')
        
        return xml_content
    
    def _fix_xml_issues(self, xml_content: str) -> str:
        """Fix common XML syntax issues."""
        # Fix unclosed tags
        xml_content = re.sub(r'<(meta|link)([^>]*)(?<!/)>', r'<\1\2/>', xml_content)
        
        # Fix unescaped ampersands
        xml_content = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', xml_content)
        
        return xml_content
    
    def _parse_metadata(self, root) -> Dict[str, str]:
        """Parse NCX metadata."""
        metadata = {}
        
        # Find head element
        head = root.find('.//{%s}head' % NCX_NS)
        if head is None:
            head = root.find('.//head')
        if head is not None:
            for meta in head.findall('.//{%s}meta' % NCX_NS) or head.findall('.//meta'):
                name = meta.get('name', '')
                content = meta.get('content', '')
                if name and content:
                    metadata[name] = content
        
        return metadata
    
    def _parse_doc_title(self, root) -> str:
        """Parse document title."""
        # Try with namespace
        doc_title = root.find('.//{%s}docTitle/{%s}text' % (NCX_NS, NCX_NS))
        if doc_title is None:
            # Try without namespace
            doc_title = root.find('.//docTitle/text')
        if doc_title is None:
            doc_title = root.find('.//docTitle')
        
        if doc_title is not None and doc_title.text:
            return doc_title.text.strip()
        
        return "Table of Contents"
    
    def _parse_nav_map(self, root) -> List[Dict[str, Any]]:
        """Parse the navMap element."""
        # Find navMap with or without namespace
        nav_map = root.find('.//{%s}navMap' % NCX_NS)
        if nav_map is None:
            nav_map = root.find('.//navMap')
        
        if nav_map is None:
            return []
        
        return self._parse_nav_points(nav_map, 0)
    
    def _parse_nav_points(self, parent, level: int) -> List[Dict[str, Any]]:
        """Parse navPoint elements recursively."""
        items = []
        
        # Find navPoints with or without namespace
        nav_points = parent.findall('{%s}navPoint' % NCX_NS)
        if not nav_points:
            nav_points = parent.findall('navPoint')
        
        for nav_point in nav_points:
            item = self._parse_nav_point(nav_point, level)
            if item:
                items.append(item)
        
        return items
    
    def _parse_nav_point(self, nav_point, level: int) -> Optional[Dict[str, Any]]:
        """Parse a single navPoint element."""
        # Get ID and playOrder
        item_id = nav_point.get('id', '')
        play_order = nav_point.get('playOrder', '')
        
        # Get navLabel/text
        title = self._get_nav_label(nav_point)
        
        # Get content/src
        href = self._get_content_src(nav_point)
        
        if not title:
            return None
        
        # Parse child navPoints
        children = self._parse_nav_points(nav_point, level + 1)
        
        return {
            'id': item_id,
            'play_order': play_order,
            'title': title,
            'href': href,
            'level': level,
            'children': children
        }
    
    def _get_nav_label(self, nav_point) -> str:
        """Extract navLabel text."""
        # Try with namespace
        nav_label = nav_point.find('{%s}navLabel/{%s}text' % (NCX_NS, NCX_NS))
        if nav_label is None:
            nav_label = nav_point.find('navLabel/text')
        if nav_label is None:
            nav_label = nav_point.find('{%s}navLabel' % NCX_NS)
        if nav_label is None:
            nav_label = nav_point.find('navLabel')
        
        if nav_label is not None:
            # Check for nested text element
            text_elem = nav_label.find('{%s}text' % NCX_NS) or nav_label.find('text')
            if text_elem is not None and text_elem.text:
                return text_elem.text.strip()
            if nav_label.text:
                return nav_label.text.strip()
        
        return ""
    
    def _get_content_src(self, nav_point) -> str:
        """Extract content src attribute."""
        # Try with namespace
        content = nav_point.find('{%s}content' % NCX_NS)
        if content is None:
            content = nav_point.find('content')
        
        if content is not None:
            return content.get('src', '')
        
        return ""
    
    def build(self, toc_structure: Dict[str, Any], original_xml: str = None) -> str:
        """
        Build NCX XML from the TOC structure.
        
        Args:
            toc_structure: The TOC structure dictionary.
            original_xml: Optional original XML to preserve formatting/metadata.
            
        Returns:
            The NCX XML as a string.
        """
        self.play_order_counter = 1
        
        # Create NCX root element
        nsmap = {None: NCX_NS}
        root = etree.Element('ncx', nsmap=nsmap)
        root.set('version', '2005-1')
        
        # Add head
        head = etree.SubElement(root, 'head')
        metadata = toc_structure.get('metadata', {})
        
        # Add required metadata
        if 'dtb:uid' not in metadata:
            metadata['dtb:uid'] = 'urn:uuid:toc-fixer-generated'
        if 'dtb:depth' not in metadata:
            metadata['dtb:depth'] = str(self._calculate_depth(toc_structure.get('items', [])))
        if 'dtb:totalPageCount' not in metadata:
            metadata['dtb:totalPageCount'] = '0'
        if 'dtb:maxPageNumber' not in metadata:
            metadata['dtb:maxPageNumber'] = '0'
        
        for name, content in metadata.items():
            meta = etree.SubElement(head, 'meta')
            meta.set('name', name)
            meta.set('content', content)
        
        # Add docTitle
        doc_title = etree.SubElement(root, 'docTitle')
        text = etree.SubElement(doc_title, 'text')
        text.text = toc_structure.get('title', 'Table of Contents')
        
        # Add navMap
        nav_map = etree.SubElement(root, 'navMap')
        self._build_nav_points(nav_map, toc_structure.get('items', []))
        
        # Format output
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        doctype = '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
        
        body = etree.tostring(root, encoding='UTF-8', pretty_print=True).decode('utf-8')
        
        # Remove the XML declaration from body if present (we'll add our own)
        if body.startswith('<?xml'):
            body = body.split('?>', 1)[1].lstrip('\n')
        
        return xml_declaration + doctype + body
    
    def _build_nav_points(self, parent, items: List[Dict[str, Any]]):
        """Build navPoint elements recursively."""
        for item in items:
            nav_point = etree.SubElement(parent, 'navPoint')
            
            # Set ID
            item_id = item.get('id', f'navPoint-{self.play_order_counter}')
            nav_point.set('id', item_id)
            
            # Set playOrder
            nav_point.set('playOrder', str(self.play_order_counter))
            self.play_order_counter += 1
            
            # Add navLabel
            nav_label = etree.SubElement(nav_point, 'navLabel')
            text = etree.SubElement(nav_label, 'text')
            text.text = item.get('title', '')
            
            # Add content
            content = etree.SubElement(nav_point, 'content')
            content.set('src', item.get('href', ''))
            
            # Add children recursively
            if item.get('children'):
                self._build_nav_points(nav_point, item['children'])
    
    def _calculate_depth(self, items: List[Dict[str, Any]], current_depth: int = 1) -> int:
        """Calculate the maximum depth of the TOC."""
        if not items:
            return current_depth - 1
        
        max_depth = current_depth
        for item in items:
            if item.get('children'):
                child_depth = self._calculate_depth(item['children'], current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
