"""
TOC XML Fixer - A tool to fix nesting and link issues in TOC XML files.

Supports:
- EPUB 2 NCX format
- EPUB 3 Navigation Document format
- Generic TOC XML structures
"""

from .toc_fixer import TOCFixer
from .ncx_parser import NCXParser
from .nav_parser import NavParser
from .nesting_fixer import NestingFixer
from .link_fixer import LinkFixer

__version__ = "1.0.0"
__all__ = ["TOCFixer", "NCXParser", "NavParser", "NestingFixer", "LinkFixer"]
