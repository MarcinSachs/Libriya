#!/usr/bin/env python
"""Update PO files from POT template"""
import os
from babel.messages.pofile import read_po, write_po
from babel.messages.catalog import Catalog

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Update Polish
with open('translations/messages.pot', 'r', encoding='utf-8') as f:
    template = read_po(f)

po_file = 'translations/pl/LC_MESSAGES/messages.po'
with open(po_file, 'r', encoding='utf-8') as f:
    current = read_po(f, locale='pl')

# Merge
for message in template:
    if message.id and message.id not in [m.id for m in current]:
        current.add(message)

with open(po_file, 'wb') as f:
    write_po(f, current)

print("Polish updated!")

# Update English
po_file_en = 'translations/en/LC_MESSAGES/messages.po'
if os.path.exists(po_file_en):
    with open(po_file_en, 'r', encoding='utf-8') as f:
        current_en = read_po(f, locale='en')

    for message in template:
        if message.id and message.id not in [m.id for m in current_en]:
            current_en.add(message)

    with open(po_file_en, 'wb') as f:
        write_po(f, current_en)

    print("English updated!")
else:
    print("English PO file not found")
