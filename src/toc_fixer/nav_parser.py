"""
Nav Parser for EPUB 3 Navigation Document format.
"""

import re
from typing import Dict, List, Any, Optional
from lxml import etree

# XHTML and EPUB namespaces
XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
NSMAP = {
    'xhtml': XHTML_NS,
    'epub': EPUB_NS
}


class NavParser:
    """
    Parser for EPUB 3 Navigation Document files.
    """
    
    def __init__(self):
        self.nsmap = NSMAP
    
    def parse(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse EPUB 3 Nav document content into a structured dictionary.
        
        Args:
            xml_content: The Nav document content as a string.
            
        Returns:
            Dictionary containing the TOC structure.
        """
        # Clean up the content
        xml_content = self._clean_content(xml_content)
        
        try:
            # Try parsing as XML first
            root = etree.fromstring(xml_content.encode('utf-8'))
        except etree.XMLSyntaxError:
            # Fall back to HTML parser
            parser = etree.HTMLParser()
            doc = etree.fromstring(xml_content.encode('utf-8'), parser)
            root = doc
        
        # Extract title
        title = self._parse_title(root)
        
        # Find the TOC nav element
        toc_nav = self._find_toc_nav(root)
        
        # Parse items from nav
        items = []
        if toc_nav is not None:
            items = self._parse_nav_items(toc_nav)
        
        return {
            'title': title,
            'metadata': {},
            'items': items,
            'original_root': root
        }
    
    def _clean_content(self, content: str) -> str:
        """Clean up common content issues."""
        # Remove BOM
        content = content.lstrip('\ufeff')
        
        # Fix common HTML entities
        content = content.replace('&nbsp;', '&#160;')
        
        return content
    
    def _parse_title(self, root) -> str:
        """Extract document title."""
        # Try with namespace
        title = root.find('.//{%s}title' % XHTML_NS)
        if title is None:
            title = root.find('.//title')
        
        if title is not None and title.text:
            return title.text.strip()
        
        # Try h1
        h1 = root.find('.//{%s}h1' % XHTML_NS)
        if h1 is None:
            h1 = root.find('.//h1')
        
        if h1 is not None and h1.text:
            return h1.text.strip()
        
        return "Table of Contents"
    
    def _find_toc_nav(self, root):
        """Find the TOC nav element."""
        # Look for nav with epub:type="toc"
        for nav in root.iter():
            tag_name = etree.QName(nav).localname if isinstance(nav.tag, str) else ''
            if tag_name == 'nav':
                epub_type = nav.get('{%s}type' % EPUB_NS, '')
                if not epub_type:
                    epub_type = nav.get('epub:type', '')
                if not epub_type:
                    epub_type = nav.get('type', '')
                
                if 'toc' in epub_type.lower():
                    return nav
                
                # Check for id="toc" or class containing "toc"
                nav_id = nav.get('id', '').lower()
                nav_class = nav.get('class', '').lower()
                if 'toc' in nav_id or 'toc' in nav_class:
                    return nav
        
        # Fall back to first nav element
        nav = root.find('.//{%s}nav' % XHTML_NS)
        if nav is None:
            nav = root.find('.//nav')
        
        return nav
    
    def _parse_nav_items(self, nav_element) -> List[Dict[str, Any]]:
        """Parse navigation items from a nav element."""
        items = []
        
        # Find the ordered list (ol) inside nav
        ol = nav_element.find('.//{%s}ol' % XHTML_NS)
        if ol is None:
            ol = nav_element.find('.//ol')
        
        if ol is None:
            # Try unordered list
            ol = nav_element.find('.//{%s}ul' % XHTML_NS)
            if ol is None:
                ol = nav_element.find('.//ul')
        
        if ol is not None:
            items = self._parse_list_items(ol, 0)
        
        return items
    
    def _parse_list_items(self, list_element, level: int) -> List[Dict[str, Any]]:
        """Parse li elements from a list."""
        items = []
        
        # Find li elements
        list_items = list_element.findall('{%s}li' % XHTML_NS)
        if not list_items:
            list_items = list_element.findall('li')
        
        for li in list_items:
            item = self._parse_list_item(li, level)
            if item:
                items.append(item)
        
        return items
    
    def _parse_list_item(self, li_element, level: int) -> Optional[Dict[str, Any]]:
        """Parse a single li element."""
        # Find the anchor element
        a = li_element.find('{%s}a' % XHTML_NS)
        if a is None:
            a = li_element.find('a')
        
        # Get span if no anchor
        span = li_element.find('{%s}span' % XHTML_NS)
        if span is None:
            span = li_element.find('span')
        
        title = ""
        href = ""
        
        if a is not None:
            # Get href
            href = a.get('href', '')
            
            # Get title - might be in text or nested elements
            title = self._get_element_text(a)
        elif span is not None:
            title = self._get_element_text(span)
        else:
            # Try direct text
            if li_element.text and li_element.text.strip():
                title = li_element.text.strip()
        
        if not title:
            return None
        
        # Get ID
        item_id = li_element.get('id', '') or (a.get('id', '') if a is not None else '')
        if not item_id:
            item_id = f'nav-{level}-{hash(title) % 10000}'
        
        # Look for nested list (children)
        children = []
        for child_list in li_element.findall('{%s}ol' % XHTML_NS):
            children.extend(self._parse_list_items(child_list, level + 1))
        for child_list in li_element.findall('ol'):
            children.extend(self._parse_list_items(child_list, level + 1))
        for child_list in li_element.findall('{%s}ul' % XHTML_NS):
            children.extend(self._parse_list_items(child_list, level + 1))
        for child_list in li_element.findall('ul'):
            children.extend(self._parse_list_items(child_list, level + 1))
        
        return {
            'id': item_id,
            'title': title,
            'href': href,
            'level': level,
            'children': children
        }
    
    def _get_element_text(self, element) -> str:
        """Get all text content from an element, including nested elements."""
        text_parts = []
        
        if element.text:
            text_parts.append(element.text.strip())
        
        for child in element:
            child_text = self._get_element_text(child)
            if child_text:
                text_parts.append(child_text)
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return ' '.join(filter(None, text_parts))
    
    def build(self, toc_structure: Dict[str, Any], original_xml: str = None) -> str:
        """
        Build EPUB 3 Nav document from the TOC structure.
        
        Args:
            toc_structure: The TOC structure dictionary.
            original_xml: Optional original XML to preserve some formatting.
            
        Returns:
            The Nav document as a string.
        """
        # Create XHTML root
        nsmap = {
            None: XHTML_NS,
            'epub': EPUB_NS
        }
        
        html = etree.Element('html', nsmap=nsmap)
        html.set('{http://www.w3.org/XML/1998/namespace}lang', 'en')
        
        # Add head
        head = etree.SubElement(html, 'head')
        
        # Add meta charset
        meta = etree.SubElement(head, 'meta')
        meta.set('charset', 'UTF-8')
        
        # Add title
        title = etree.SubElement(head, 'title')
        title.text = toc_structure.get('title', 'Table of Contents')
        
        # Add body
        body = etree.SubElement(html, 'body')
        
        # Add nav element
        nav = etree.SubElement(body, 'nav')
        nav.set('{%s}type' % EPUB_NS, 'toc')
        nav.set('id', 'toc')
        
        # Add heading
        h1 = etree.SubElement(nav, 'h1')
        h1.text = toc_structure.get('title', 'Table of Contents')
        
        # Add items as ordered list
        if toc_structure.get('items'):
            ol = etree.SubElement(nav, 'ol')
            self._build_list_items(ol, toc_structure['items'])
        
        # Format output
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        doctype = '<!DOCTYPE html>\n'
        
        body_str = etree.tostring(html, encoding='unicode', pretty_print=True)
        
        return xml_declaration + doctype + body_str
    
    def _build_list_items(self, parent_list, items: List[Dict[str, Any]]):
        """Build li elements recursively."""
        for item in items:
            li = etree.SubElement(parent_list, 'li')
            
            # Set ID if available
            if item.get('id'):
                li.set('id', item['id'])
            
            # Add anchor
            a = etree.SubElement(li, 'a')
            a.set('href', item.get('href', '#'))
            a.text = item.get('title', '')
            
            # Add children as nested list
            if item.get('children'):
                ol = etree.SubElement(li, 'ol')
                self._build_list_items(ol, item['children'])
