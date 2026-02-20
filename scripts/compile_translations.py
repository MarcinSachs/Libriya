#!/usr/bin/env python
"""Compile PO files to MO files (moved to scripts/)

Usage: python scripts/compile_translations.py [locale]
"""
import os
from babel.messages import pofile, mofile
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

locale = sys.argv[1] if len(sys.argv) > 1 else 'pl'
po_file = os.path.join(repo_root, 'translations', locale, 'LC_MESSAGES', 'messages.po')
mo_file = os.path.join(repo_root, 'translations', locale, 'LC_MESSAGES', 'messages.mo')

print(f"Reading {po_file}...")
with open(po_file, 'r', encoding='utf-8') as f:
    catalog = pofile.read_po(f, locale=locale)

print(f"Writing {mo_file}...")
with open(mo_file, 'wb') as f:
    mofile.write_mo(f, catalog)

print("Done!")
