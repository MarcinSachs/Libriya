#!/usr/bin/env python
"""Extract messages to POT file"""
import os
import sys
from babel.messages.frontend import extract_messages

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.argv = ['extract_messages', '-F', 'babel.cfg', '-o', 'translations/messages.pot', '.']
extract_messages()
print("Done!")
