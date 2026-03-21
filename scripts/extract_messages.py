#!/usr/bin/env python
"""Extract and update translation catalogs.

Usage:
  python scripts/extract_messages.py        # extract + update .po
  python scripts/extract_messages.py --compile  # extract + update .po + compile .mo
"""
import argparse
import os
import sys
import subprocess
from babel.messages.frontend import extract_messages, update_catalog, compile_catalog

# Run from repository root so all modules/templates are scanned correctly
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)

parser = argparse.ArgumentParser(description='Extract and update translation catalogs')
parser.add_argument('--compile', action='store_true', help='Compile .po to .mo after update')
args = parser.parse_args()

out_path = os.path.join(repo_root, 'translations', 'messages.pot')

# Step 1: Extract messages to POT
sys.argv = ['extract_messages', '-F', 'babel.cfg', '-o', out_path, repo_root]
extract_messages()
print(f"Done! Wrote: {out_path}")

# Step 2: Update locale catalogs (all existing locales under translations)
locales_dir = os.path.join(repo_root, 'translations')

locales = []
for entry in os.listdir(locales_dir):
    locale_path = os.path.join(locales_dir, entry)
    if os.path.isdir(locale_path) and os.path.isdir(os.path.join(locale_path, 'LC_MESSAGES')):
        locales.append(entry)

if not locales:
    print('No locale directories found under translations/. Skipping locale update.')
else:
    def run_pybabel(args):
        try:
            subprocess.run(['pybabel'] + args, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    for lang in locales:
        print(f'Updating locale "{lang}"...')

        if run_pybabel(['update', '-i', out_path, '-d', locales_dir, '-l', lang]):
            continue

        print('`pybabel` CLI not available; falling back to Babel frontend update_catalog')
        update_cmd = update_catalog()
        update_cmd.initialize_options()
        update_cmd.input_file = out_path
        update_cmd.output_dir = locales_dir
        update_cmd.locale = lang
        update_cmd.mapping_file = None
        update_cmd.finalize_options()
        update_cmd.run()

if args.compile:
    print('Compiling translation catalogs...')

    if not run_pybabel(['compile', '-d', locales_dir]):
        print('`pybabel` CLI not available; falling back to Babel frontend compile_catalog')
        compile_cmd = compile_catalog()
        compile_cmd.initialize_options()
        compile_cmd.directory = locales_dir
        compile_cmd.finalize_options()
        compile_cmd.run()

    print('Compilation complete.')
else:
    print('Skipping .mo compilation. Run with --compile when PO translation is ready.')
