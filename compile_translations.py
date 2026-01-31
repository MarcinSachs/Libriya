#!/usr/bin/env python
"""Compile PO files to MO files"""
import os
from babel.messages import pofile, mofile
import io


def compile_messages(locale='pl'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    po_file = os.path.join(base_dir, 'translations', locale, 'LC_MESSAGES', 'messages.po')
    mo_file = os.path.join(base_dir, 'translations', locale, 'LC_MESSAGES', 'messages.mo')

    print(f"Reading {po_file}...")
    with open(po_file, 'r', encoding='utf-8') as f:
        catalog = pofile.read_po(f, locale=locale)

    print(f"Writing {mo_file}...")
    with open(mo_file, 'wb') as f:
        mofile.write_mo(f, catalog)

    print("Done!")


if __name__ == '__main__':
    compile_messages('pl')
