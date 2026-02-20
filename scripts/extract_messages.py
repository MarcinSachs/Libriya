#!/usr/bin/env python
"""Extract messages to POT file (moved into scripts/)

Usage: python scripts/extract_messages.py
"""
import os
import sys
from babel.messages.frontend import extract_messages

# Run from repository root so all modules/templates are scanned correctly
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)

out_path = os.path.join(repo_root, 'translations', 'messages.pot')

sys.argv = ['extract_messages', '-F', 'babel.cfg', '-o', out_path, repo_root]
extract_messages()
print(f"Done! Wrote: {out_path}")
