"""
TOC XML Fixer - A tool to fix nesting and link issues in TOC XML files.

Supports:
- EPUB 2 NCX format
- EPUB 3 Navigation Document format
- Generic TOC XML structures
- Citation tag fixing in content files
- Full book/EPUB zip processing
"""

from .toc_fixer import TOCFixer
from .ncx_parser import NCXParser
from .nav_parser import NavParser
from .nesting_fixer import NestingFixer
from .link_fixer import LinkFixer
from .citation_fixer import CitationFixer
from .reference_fixer import ReferenceFixer
from .bibliography_fixer import BibliographyFixer
from .book_fixer import BookFixer

__version__ = "1.3.0"
__all__ = [
    "TOCFixer", 
    "NCXParser", 
    "NavParser", 
    "NestingFixer", 
    "LinkFixer",
    "CitationFixer",
    "ReferenceFixer",
    "BibliographyFixer",
    "BookFixer",
]
