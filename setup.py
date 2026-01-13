#!/usr/bin/env python3
"""
Setup script for TOC XML Fixer package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="toc-xml-fixer",
    version="1.0.0",
    author="TOC Fixer Team",
    description="Fix nesting and link issues in EPUB TOC XML files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Likith-Zentrovia/EPUBTOXMLTOC",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "lxml>=5.1.0",
    ],
    entry_points={
        "console_scripts": [
            "toc-fixer=toc_fixer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    keywords="epub, toc, xml, ncx, navigation, ebook",
)
