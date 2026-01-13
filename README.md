# EPUBTOXMLTOC - TOC XML Fixer

A Python tool to fix nesting and link issues in Table of Contents (TOC) XML files, commonly found in EPUB ebooks.

## Features

- **Fix Nesting Issues**: Automatically restructure flat TOC entries into proper hierarchical structure (chapters → sections → subsections)
- **Fix Link Issues**: Correct broken links, URL encoding problems, and invalid fragment identifiers
- **Multiple Format Support**:
  - EPUB 2 NCX (Navigation Control for XML)
  - EPUB 3 Navigation Document (XHTML)
  - Generic TOC XML structures
- **Analysis Mode**: Analyze TOC files and get detailed reports of issues without modifying
- **Command-line Interface**: Easy-to-use CLI for quick fixes

## Installation

### Option 1: Quick Start (No Installation Required)

```bash
# Clone the repository
git clone https://github.com/Likith-Zentrovia/EPUBTOXMLTOC.git
cd EPUBTOXMLTOC

# Install the required dependency
pip install lxml

# Run directly using the convenience script
python fix_toc.py input.ncx -o output.ncx
```

### Option 2: Full Installation

```bash
# Clone the repository
git clone https://github.com/Likith-Zentrovia/EPUBTOXMLTOC.git
cd EPUBTOXMLTOC

# Install dependencies
pip install -r requirements.txt

# Install the package (in development mode)
pip install -e .

# Now you can use toc-fixer from anywhere
toc-fixer input.ncx -o output.ncx
```

### Requirements

- Python 3.8+
- lxml >= 5.1.0

## Quick Start

### Command Line Usage (Using fix_toc.py)

```bash
# Fix a TOC file and save to new file
python fix_toc.py input.ncx -o output.ncx

# Fix a TOC file in place
python fix_toc.py input.ncx --in-place

# Analyze issues without fixing
python fix_toc.py input.ncx --analyze

# Analyze with JSON output
python fix_toc.py input.ncx --analyze --json

# Fix with content path for link validation
python fix_toc.py toc.ncx -o fixed.ncx --content-path ./OEBPS

# Verbose output
python fix_toc.py input.ncx -o output.ncx -v
```

### Windows Examples

```powershell
# From the EPUBTOXMLTOC directory:
python fix_toc.py "C:\Users\user\Documents\book\toc.xml" -o "C:\Users\user\Documents\book\toc_fixed.xml"

# Analyze a TOC file
python fix_toc.py "C:\path\to\toc.ncx" --analyze -v
```

### Python API Usage

```python
from toc_fixer import TOCFixer

# Create fixer instance
fixer = TOCFixer(content_base_path="./OEBPS")

# Fix from file
fixed_content = fixer.fix_from_file("input.ncx", "output.ncx")

# Fix from string
with open("input.ncx", "r") as f:
    xml_content = f.read()

fixed_content = fixer.fix(xml_content)

# Get analysis report
report = fixer.get_report(xml_content)
print(f"Found {len(report['nesting_issues'])} nesting issues")
print(f"Found {len(report['link_issues'])} link issues")
```

## What It Fixes

### Nesting Issues

The tool detects and fixes improper nesting based on title patterns:

**Before (flat structure):**
```xml
<navPoint id="ch1"><navLabel><text>Chapter 1</text></navLabel></navPoint>
<navPoint id="s1"><navLabel><text>1.1 Section One</text></navLabel></navPoint>
<navPoint id="s2"><navLabel><text>1.2 Section Two</text></navLabel></navPoint>
<navPoint id="ch2"><navLabel><text>Chapter 2</text></navLabel></navPoint>
```

**After (proper hierarchy):**
```xml
<navPoint id="ch1">
  <navLabel><text>Chapter 1</text></navLabel>
  <navPoint id="s1"><navLabel><text>1.1 Section One</text></navLabel></navPoint>
  <navPoint id="s2"><navLabel><text>1.2 Section Two</text></navLabel></navPoint>
</navPoint>
<navPoint id="ch2">
  <navLabel><text>Chapter 2</text></navLabel>
</navPoint>
```

#### Detected Patterns

**Chapter-level (level 0):**
- `Chapter 1`, `Ch. 1`, `CHAPTER ONE`
- `Part 1`, `Book 1`, `Unit 1`
- `1. Title` (numbered chapters)
- `I. Title` (Roman numerals)

**Section-level (level 1):**
- `1.1 Section Title`
- `Section 1`, `Sec. 1`
- `A. Title` (lettered sections)

**Subsection-level (level 2):**
- `1.1.1 Subsection Title`
- `a) Item`
- `(1) Item`

**Special top-level items** (always stay at level 0):
- Cover, Title Page, Copyright
- Preface, Foreword, Introduction
- Appendix, Glossary, Bibliography, Index

### Link Issues

The tool fixes various link problems:

1. **URL Encoding Issues**
   - Unencoded spaces: `chapter 1.xhtml` → `chapter%201.xhtml`
   - Double encoding: `%2520` → `%20`

2. **Broken Fragment Identifiers**
   - Invalid characters removed
   - Proper formatting ensured

3. **Path Corrections**
   - Case-sensitivity fixes
   - Extension variations (.html, .xhtml, .htm)
   - Path normalization

4. **Missing Links**
   - Detected and reported for manual review

## Supported Formats

### EPUB 2 NCX

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="ch1" playOrder="1">
      <navLabel><text>Chapter 1</text></navLabel>
      <content src="chapter01.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
```

### EPUB 3 Navigation Document

```html
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body>
  <nav epub:type="toc" id="toc">
    <ol>
      <li><a href="chapter01.xhtml">Chapter 1</a></li>
    </ol>
  </nav>
</body>
</html>
```

### Generic TOC XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<toc>
  <title>Table of Contents</title>
  <items>
    <item id="ch1">
      <title>Chapter 1</title>
      <link href="chapter01.html"/>
    </item>
  </items>
</toc>
```

## API Reference

### TOCFixer

Main class for fixing TOC files.

```python
class TOCFixer:
    def __init__(self, content_base_path: str = None):
        """
        Args:
            content_base_path: Base path for link validation
        """
    
    def fix(self, xml_content: str) -> str:
        """Fix TOC XML content and return fixed content."""
    
    def fix_from_file(self, input_path: str, output_path: str = None) -> str:
        """Fix a TOC file and optionally save to output."""
    
    def get_report(self, xml_content: str) -> dict:
        """Get analysis report of issues."""
    
    def detect_format(self, xml_content: str) -> str:
        """Detect format: 'ncx', 'nav', or 'generic'."""
```

### NestingFixer

Handles nesting structure issues.

```python
class NestingFixer:
    def fix_nesting(self, toc_structure: dict) -> dict:
        """Fix nesting issues in TOC structure."""
    
    def analyze_issues(self, toc_structure: dict) -> list:
        """Analyze and return list of nesting issues."""
```

### LinkFixer

Handles link-related issues.

```python
class LinkFixer:
    def __init__(self, content_base_path: str = None):
        """Initialize with optional content path for validation."""
    
    def fix_links(self, toc_structure: dict) -> dict:
        """Fix link issues in TOC structure."""
    
    def analyze_issues(self, toc_structure: dict) -> list:
        """Analyze and return list of link issues."""
```

## Examples

The `examples/` directory contains sample broken TOC files:

- `broken_toc.ncx` - NCX file with flat structure and link issues
- `broken_nav.xhtml` - EPUB 3 Nav with incorrect nesting
- `broken_generic.xml` - Generic TOC with various issues

Run the fixer on examples:

```bash
# Fix the broken NCX
toc-fixer examples/broken_toc.ncx -o examples/fixed_toc.ncx -v

# Analyze the broken Nav
toc-fixer examples/broken_nav.xhtml --analyze

# Fix generic TOC
toc-fixer examples/broken_generic.xml -o examples/fixed_generic.xml
```

## Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/ -v

# Or run directly
python -m unittest discover tests/
```

## Project Structure

```
EPUBTOXMLTOC/
├── src/
│   └── toc_fixer/
│       ├── __init__.py       # Package exports
│       ├── toc_fixer.py      # Main TOCFixer class
│       ├── ncx_parser.py     # EPUB 2 NCX parser
│       ├── nav_parser.py     # EPUB 3 Nav parser
│       ├── nesting_fixer.py  # Nesting hierarchy fixer
│       ├── link_fixer.py     # Link validation/fixer
│       └── cli.py            # Command-line interface
├── tests/
│   ├── __init__.py
│   └── test_toc_fixer.py     # Unit tests
├── examples/
│   ├── broken_toc.ncx        # Example broken NCX
│   ├── broken_nav.xhtml      # Example broken Nav
│   └── broken_generic.xml    # Example broken generic TOC
├── requirements.txt          # Dependencies
├── setup.py                  # Package setup
└── README.md                 # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### v1.0.0
- Initial release
- Support for EPUB 2 NCX format
- Support for EPUB 3 Navigation Document format
- Support for generic TOC XML
- Nesting structure fixing
- Link validation and fixing
- Command-line interface
- Analysis/report mode
