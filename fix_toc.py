#!/usr/bin/env python3
"""
Convenience script to run TOC XML Fixer without installation.
Usage: python fix_toc.py <input_file> [options]
"""

import sys
import os

# Add src directory to path so we can import without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from toc_fixer.cli import main

if __name__ == '__main__':
    main()
