#!/usr/bin/env python3
"""
Tests for Bibliography Structure Fixer.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from toc_fixer.bibliography_fixer import BibliographyFixer


class TestBibliographyFixer(unittest.TestCase):
    """Tests for Bibliography Structure Fixer."""
    
    def setUp(self):
        self.fixer = BibliographyFixer()
    
    def test_convert_orderedlist_to_bibliography(self):
        """Test converting orderedlist structure to bibliography."""
        content = '''
        <sect2 id="ch0011s009000-5">
            <title>References</title>
            <orderedlist>
                <listitem id="ch0011-c1-bib-0001" role="bibliographyEntry">
                    <para><emphasis role="strong">1</emphasis> Rollin, B.E. (2011). Content here.</para>
                </listitem>
                <listitem id="ch0011-c1-bib-0002" role="bibliographyEntry">
                    <para><emphasis role="strong">2</emphasis> Leary, S. (2020). More content.</para>
                </listitem>
            </orderedlist>
        </sect2>
        '''
        
        fixed, changes = self.fixer.fix_bibliography_structure(content, 'ch0011.xml')
        
        self.assertEqual(len(changes), 1)
        self.assertIn('<bibliography', fixed)
        self.assertIn('<bibliomixed', fixed)
        self.assertIn('id="ch0011-c1-bib-0001"', fixed)
        self.assertIn('id="ch0011-c1-bib-0002"', fixed)
        # Should NOT have orderedlist
        self.assertNotIn('<orderedlist', fixed)
        self.assertNotIn('<listitem', fixed)
        # Should NOT have duplicate numbers
        self.assertNotIn('<emphasis role="strong">1</emphasis>', fixed)
    
    def test_remove_duplicate_numbers(self):
        """Test that duplicate numbers are removed from entries."""
        content = '''
        <sect2 id="ch0020s009000-5">
            <title>References</title>
            <orderedlist>
                <listitem id="ch0020-bib-0001">
                    <para><emphasis role="strong">1</emphasis> Author Name (2020). Title here.</para>
                </listitem>
            </orderedlist>
        </sect2>
        '''
        
        fixed, changes = self.fixer.fix_bibliography_structure(content)
        
        # The content should have the author name without the number prefix
        self.assertIn('Author Name (2020)', fixed)
        # Should not have the emphasis number
        self.assertNotIn('<emphasis role="strong">1</emphasis>', fixed)
    
    def test_preserve_entry_ids(self):
        """Test that entry IDs are preserved."""
        content = '''
        <sect2 id="ch0011s009000-5">
            <title>References</title>
            <orderedlist>
                <listitem id="ch0011-c1-bib-0001">
                    <para>1 Content one.</para>
                </listitem>
                <listitem id="ch0011-c1-bib-0002">
                    <para>2 Content two.</para>
                </listitem>
            </orderedlist>
        </sect2>
        '''
        
        fixed, changes = self.fixer.fix_bibliography_structure(content)
        
        self.assertIn('id="ch0011-c1-bib-0001"', fixed)
        self.assertIn('id="ch0011-c1-bib-0002"', fixed)
    
    def test_no_change_when_no_orderedlist(self):
        """Test that content without orderedlist is not changed."""
        content = '''
        <bibliography id="ch0020">
            <title>References</title>
            <bibliodiv>
                <bibliomixed id="ch0020-bib0001">Content here.</bibliomixed>
            </bibliodiv>
        </bibliography>
        '''
        
        fixed, changes = self.fixer.fix_bibliography_structure(content)
        
        self.assertEqual(len(changes), 0)
        self.assertEqual(fixed.strip(), content.strip())
    
    def test_clean_various_number_formats(self):
        """Test cleaning various number format patterns."""
        fixer = self.fixer
        
        # Test emphasis with role
        content1 = '<emphasis role="strong">1</emphasis> Author text'
        cleaned1 = fixer._clean_entry_content(f'<para>{content1}</para>')
        self.assertEqual(cleaned1, 'Author text')
        
        # Test plain number
        content2 = '1. Author text'
        cleaned2 = fixer._clean_entry_content(f'<para>{content2}</para>')
        self.assertEqual(cleaned2, 'Author text')
        
        # Test number without period
        content3 = '1 Author text'
        cleaned3 = fixer._clean_entry_content(f'<para>{content3}</para>')
        self.assertEqual(cleaned3, 'Author text')


class TestBibliographyFixerAnalysis(unittest.TestCase):
    """Tests for bibliography issue analysis."""
    
    def setUp(self):
        self.fixer = BibliographyFixer()
    
    def test_analyze_finds_issues(self):
        """Test that analysis finds structure issues."""
        content = '''
        <sect2 id="ch0011s009000-5">
            <title>References</title>
            <orderedlist>
                <listitem id="ch0011-c1-bib-0001">
                    <para><emphasis role="strong">1</emphasis> Content.</para>
                </listitem>
            </orderedlist>
        </sect2>
        '''
        
        issues = self.fixer.analyze_bibliography_issues(content)
        
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]['type'], 'wrong_structure')
        self.assertTrue(issues[0]['has_duplicate_numbers'])


if __name__ == '__main__':
    unittest.main()
