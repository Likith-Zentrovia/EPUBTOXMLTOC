#!/usr/bin/env python3
"""
Tests for TOC XML Fixer.
"""

import os
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from toc_fixer import TOCFixer, NCXParser, NavParser, NestingFixer, LinkFixer


class TestNCXParser(unittest.TestCase):
    """Tests for NCX Parser."""
    
    def setUp(self):
        self.parser = NCXParser()
        self.sample_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
            <head>
                <meta name="dtb:uid" content="test-uid"/>
            </head>
            <docTitle><text>Test Book</text></docTitle>
            <navMap>
                <navPoint id="ch1" playOrder="1">
                    <navLabel><text>Chapter 1</text></navLabel>
                    <content src="ch1.xhtml"/>
                    <navPoint id="sec1" playOrder="2">
                        <navLabel><text>Section 1.1</text></navLabel>
                        <content src="ch1.xhtml#sec1"/>
                    </navPoint>
                </navPoint>
            </navMap>
        </ncx>'''
    
    def test_parse_ncx(self):
        """Test parsing NCX content."""
        result = self.parser.parse(self.sample_ncx)
        
        self.assertEqual(result['title'], 'Test Book')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['title'], 'Chapter 1')
        self.assertEqual(result['items'][0]['href'], 'ch1.xhtml')
    
    def test_parse_nested_items(self):
        """Test parsing nested navPoints."""
        result = self.parser.parse(self.sample_ncx)
        
        chapter = result['items'][0]
        self.assertEqual(len(chapter['children']), 1)
        self.assertEqual(chapter['children'][0]['title'], 'Section 1.1')
    
    def test_build_ncx(self):
        """Test building NCX from structure."""
        structure = {
            'title': 'Test Book',
            'metadata': {'dtb:uid': 'test'},
            'items': [
                {
                    'id': 'ch1',
                    'title': 'Chapter 1',
                    'href': 'ch1.xhtml',
                    'children': []
                }
            ]
        }
        
        result = self.parser.build(structure)
        
        self.assertIn('<?xml version', result)
        self.assertIn('Chapter 1', result)
        self.assertIn('ch1.xhtml', result)


class TestNavParser(unittest.TestCase):
    """Tests for Nav Parser."""
    
    def setUp(self):
        self.parser = NavParser()
        self.sample_nav = '''<?xml version="1.0" encoding="UTF-8"?>
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
        <head><title>Contents</title></head>
        <body>
            <nav epub:type="toc" id="toc">
                <h1>Table of Contents</h1>
                <ol>
                    <li><a href="ch1.xhtml">Chapter 1</a>
                        <ol>
                            <li><a href="ch1.xhtml#sec1">Section 1.1</a></li>
                        </ol>
                    </li>
                </ol>
            </nav>
        </body>
        </html>'''
    
    def test_parse_nav(self):
        """Test parsing Nav document."""
        result = self.parser.parse(self.sample_nav)
        
        self.assertEqual(result['title'], 'Contents')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['title'], 'Chapter 1')
    
    def test_parse_nested_nav_items(self):
        """Test parsing nested nav items."""
        result = self.parser.parse(self.sample_nav)
        
        chapter = result['items'][0]
        self.assertEqual(len(chapter['children']), 1)
        self.assertEqual(chapter['children'][0]['title'], 'Section 1.1')


class TestNestingFixer(unittest.TestCase):
    """Tests for Nesting Fixer."""
    
    def setUp(self):
        self.fixer = NestingFixer()
    
    def test_detect_chapter_pattern(self):
        """Test detection of chapter patterns."""
        patterns = [
            ('Chapter 1. Introduction', True),
            ('Ch. 1 Getting Started', True),
            ('Part 1: Beginning', True),
            ('1. First Chapter', True),
            ('Random Title', False),
        ]
        
        for title, expected in patterns:
            result = self.fixer._matches_pattern(title, self.fixer.chapter_re)
            self.assertEqual(result, expected, f"Failed for: {title}")
    
    def test_detect_section_pattern(self):
        """Test detection of section patterns."""
        patterns = [
            ('1.1 First Section', True),
            ('Section 1. Overview', True),
            ('A. Introduction', True),
            ('Random Text', False),
        ]
        
        for title, expected in patterns:
            result = self.fixer._matches_pattern(title, self.fixer.section_re)
            self.assertEqual(result, expected, f"Failed for: {title}")
    
    def test_detect_subsection_pattern(self):
        """Test detection of subsection patterns."""
        patterns = [
            ('1.1.1 Deep Section', True),
            ('a) First Item', True),
            ('(1) Numbered Item', True),
            ('Normal Text', False),
        ]
        
        for title, expected in patterns:
            result = self.fixer._matches_pattern(title, self.fixer.subsection_re)
            self.assertEqual(result, expected, f"Failed for: {title}")
    
    def test_fix_flat_structure(self):
        """Test fixing a flat structure into nested hierarchy."""
        flat_structure = {
            'title': 'Test',
            'items': [
                {'id': '1', 'title': 'Chapter 1', 'href': 'ch1.html', 'level': 0, 'children': []},
                {'id': '2', 'title': '1.1 Section One', 'href': 'ch1.html#s1', 'level': 0, 'children': []},
                {'id': '3', 'title': '1.2 Section Two', 'href': 'ch1.html#s2', 'level': 0, 'children': []},
                {'id': '4', 'title': 'Chapter 2', 'href': 'ch2.html', 'level': 0, 'children': []},
            ]
        }
        
        result = self.fixer.fix_nesting(flat_structure)
        
        # Chapter 1 should have 2 children (sections)
        self.assertEqual(len(result['items']), 2)  # 2 chapters
        self.assertEqual(result['items'][0]['title'], 'Chapter 1')
        self.assertEqual(len(result['items'][0]['children']), 2)


class TestLinkFixer(unittest.TestCase):
    """Tests for Link Fixer."""
    
    def setUp(self):
        self.fixer = LinkFixer()
    
    def test_fix_url_encoding(self):
        """Test URL encoding fixes."""
        test_cases = [
            ('chapter 1.xhtml', 'chapter%201.xhtml'),
            ('file.xhtml#section', 'file.xhtml#section'),
            ('path/to/file.xhtml', 'path/to/file.xhtml'),
        ]
        
        for input_path, expected in test_cases:
            result = self.fixer._fix_url_encoding(input_path)
            self.assertEqual(result, expected, f"Failed for: {input_path}")
    
    def test_fix_fragment(self):
        """Test fragment identifier fixes."""
        test_cases = [
            ('section1', 'section1'),
            ('my-section', 'my-section'),
            ('_private', '_private'),
        ]
        
        for input_frag, expected in test_cases:
            result = self.fixer._fix_fragment(input_frag)
            self.assertEqual(result, expected, f"Failed for: {input_frag}")
    
    def test_detect_encoding_issues(self):
        """Test detection of encoding issues."""
        self.assertTrue(self.fixer._has_encoding_issues('file name.xhtml'))
        self.assertTrue(self.fixer._has_encoding_issues('file%25encoded.xhtml'))
        self.assertFalse(self.fixer._has_encoding_issues('file%20name.xhtml'))
        self.assertFalse(self.fixer._has_encoding_issues('normal-file.xhtml'))


class TestTOCFixer(unittest.TestCase):
    """Integration tests for TOC Fixer."""
    
    def setUp(self):
        self.fixer = TOCFixer()
    
    def test_detect_ncx_format(self):
        """Test format detection for NCX."""
        ncx_content = '<ncx><navMap></navMap></ncx>'
        self.assertEqual(self.fixer.detect_format(ncx_content), 'ncx')
    
    def test_detect_nav_format(self):
        """Test format detection for Nav."""
        nav_content = '<html><nav epub:type="toc"></nav></html>'
        self.assertEqual(self.fixer.detect_format(nav_content), 'nav')
    
    def test_detect_generic_format(self):
        """Test format detection for generic XML."""
        generic_content = '<toc><items></items></toc>'
        self.assertEqual(self.fixer.detect_format(generic_content), 'generic')
    
    def test_full_ncx_fix(self):
        """Test full NCX fixing process."""
        ncx_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
            <head><meta name="dtb:uid" content="test"/></head>
            <docTitle><text>Test</text></docTitle>
            <navMap>
                <navPoint id="ch1" playOrder="1">
                    <navLabel><text>Chapter 1</text></navLabel>
                    <content src="ch1.xhtml"/>
                </navPoint>
                <navPoint id="sec1" playOrder="2">
                    <navLabel><text>1.1 Section</text></navLabel>
                    <content src="ch1.xhtml#sec1"/>
                </navPoint>
            </navMap>
        </ncx>'''
        
        result = self.fixer.fix(ncx_content)
        
        self.assertIn('<?xml version', result)
        self.assertIn('Chapter 1', result)
        self.assertIn('1.1 Section', result)


class TestExampleFiles(unittest.TestCase):
    """Tests using example files."""
    
    @classmethod
    def setUpClass(cls):
        cls.examples_dir = Path(__file__).parent.parent / "examples"
        cls.fixer = TOCFixer()
    
    def test_fix_broken_ncx(self):
        """Test fixing the broken NCX example."""
        ncx_path = self.examples_dir / "broken_toc.ncx"
        if not ncx_path.exists():
            self.skipTest("Example file not found")
        
        with open(ncx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = self.fixer.fix(content)
        
        # Should produce valid XML
        self.assertIn('<?xml version', result)
        self.assertIn('navMap', result)
    
    def test_fix_broken_nav(self):
        """Test fixing the broken Nav example."""
        nav_path = self.examples_dir / "broken_nav.xhtml"
        if not nav_path.exists():
            self.skipTest("Example file not found")
        
        with open(nav_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = self.fixer.fix(content)
        
        # Should produce valid HTML/XHTML
        self.assertIn('nav', result)
    
    def test_analyze_report(self):
        """Test analysis report generation."""
        ncx_path = self.examples_dir / "broken_toc.ncx"
        if not ncx_path.exists():
            self.skipTest("Example file not found")
        
        with open(ncx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        report = self.fixer.get_report(content)
        
        self.assertIn('format', report)
        self.assertIn('total_items', report)
        self.assertIn('nesting_issues', report)
        self.assertIn('link_issues', report)
        self.assertEqual(report['format'], 'ncx')


if __name__ == '__main__':
    unittest.main()
