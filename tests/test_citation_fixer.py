#!/usr/bin/env python3
"""
Tests for Citation Fixer.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from toc_fixer.citation_fixer import CitationFixer


class TestCitationFixer(unittest.TestCase):
    """Tests for Citation Fixer."""
    
    def setUp(self):
        self.fixer = CitationFixer()
    
    def test_basic_citation_fix(self):
        """Test fixing a basic citation tag."""
        content = '<para>Some text <citation>ch0011-c1-bib-0001</citation> more text.</para>'
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 1)
        # Citation links to chapter's References section (default fallback pattern)
        self.assertIn('<ulink url="ch0011#ch0011s009000-5">1</ulink>', fixed)
        self.assertNotIn('<citation>', fixed)
    
    def test_multiple_citations(self):
        """Test fixing multiple citations in one content."""
        content = '''
        <para>
            First reference <citation>ch0011-c1-bib-0001</citation> and
            second reference <citation>ch0011-c1-bib-0002</citation> and
            third reference <citation>ch0011-c1-bib-0010</citation>.
        </para>
        '''
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 3)
        self.assertIn('>1</ulink>', fixed)
        self.assertIn('>2</ulink>', fixed)
        self.assertIn('>10</ulink>', fixed)
    
    def test_citation_with_filename_context(self):
        """Test citation fixing with filename context."""
        content = '<citation>c1-bib-0005</citation>'
        fixed, changes = self.fixer.fix_citations_in_content(content, 'ch0015.xml')
        
        self.assertEqual(len(changes), 1)
        # Should use chapter from filename
        self.assertIn('ch0015', fixed)
    
    def test_preserves_other_content(self):
        """Test that other content is preserved."""
        content = '''
        <para id="ch0011-c1-para-0005">
            The effective provision of AHPC <citation>ch0011-c1-bib-0001</citation>.
            Hospice care (see <ulink url="ch0020">Chapter 9</ulink>).
        </para>
        '''
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 1)
        # Original ulink should be preserved
        self.assertIn('<ulink url="ch0020">Chapter 9</ulink>', fixed)
        # Para tag should be preserved
        self.assertIn('id="ch0011-c1-para-0005"', fixed)
    
    def test_citation_with_references_section(self):
        """Test citation fix when References section exists in content."""
        content = '''
        <chapter>
            <para>Some text <citation>ch0011-c1-bib-0001</citation>.</para>
            <sect2 id="ch0011s009000-5">
                <title>References</title>
                <orderedlist>
                    <listitem id="ch0011-c1-bib-0001">
                        <para>Reference 1 content</para>
                    </listitem>
                </orderedlist>
            </sect2>
        </chapter>
        '''
        fixed, changes = self.fixer.fix_citations_in_content(content, 'ch0011.xml')
        
        self.assertEqual(len(changes), 1)
        # Should link to the References section ID found in content
        self.assertIn('url="ch0011#ch0011s009000-5"', fixed)
    
    def test_analyze_citations(self):
        """Test analyzing citations without fixing."""
        content = '''
        <citation>ch0011-c1-bib-0001</citation>
        <citation>ch0011-c1-bib-0002</citation>
        '''
        citations = self.fixer.analyze_citations(content)
        
        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]['citation_id'], 'ch0011-c1-bib-0001')
        self.assertEqual(citations[0]['chapter'], 'ch0011')
        self.assertEqual(citations[0]['bib_num'], '0001')
    
    def test_no_citations(self):
        """Test content with no citations."""
        content = '<para>Just regular text with <ulink url="test">a link</ulink>.</para>'
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 0)
        self.assertEqual(fixed, content)
    
    def test_parse_citation_id_variations(self):
        """Test parsing various citation ID formats."""
        test_cases = [
            ('ch0011-c1-bib-0001', ('ch0011', '0001')),
            ('ch0020-c1-bib-0015', ('ch0020', '0015')),
            ('bib-0005', (None, '0005')),
            ('ref-0003', (None, '0003')),
        ]
        
        for citation_id, expected in test_cases:
            chapter, bib_num = self.fixer._parse_citation_id(citation_id)
            self.assertEqual(chapter, expected[0], f"Failed for {citation_id}")
            self.assertEqual(bib_num, expected[1], f"Failed for {citation_id}")


class TestCitationFixerEdgeCases(unittest.TestCase):
    """Edge case tests for Citation Fixer."""
    
    def setUp(self):
        self.fixer = CitationFixer()
    
    def test_citation_with_whitespace(self):
        """Test citation with internal whitespace."""
        content = '<citation> ch0011-c1-bib-0001 </citation>'
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 1)
        self.assertIn('>1</ulink>', fixed)
    
    def test_case_insensitive_citation_tag(self):
        """Test that CITATION tag is also matched."""
        content = '<CITATION>ch0011-c1-bib-0001</CITATION>'
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 1)
    
    def test_mixed_content(self):
        """Test with mixed content types."""
        content = '''<?xml version="1.0"?>
        <chapter>
            <title>Test Chapter</title>
            <para>
                Reference one <citation>ch0011-c1-bib-0001</citation>,
                see also <ulink url="ch0020">Chapter 20</ulink>.
            </para>
            <para>
                Another reference <citation>ch0011-c1-bib-0002</citation>.
            </para>
        </chapter>
        '''
        fixed, changes = self.fixer.fix_citations_in_content(content)
        
        self.assertEqual(len(changes), 2)
        self.assertIn('<?xml version="1.0"?>', fixed)
        self.assertIn('<title>Test Chapter</title>', fixed)


if __name__ == '__main__':
    unittest.main()
