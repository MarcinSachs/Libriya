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

# Run from repository root so all modules/templates are scanned correctly
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)

parser = argparse.ArgumentParser(description='Extract and update translation catalogs')
parser.add_argument('--compile', action='store_true', help='Compile .po to .mo after update')
args = parser.parse_args()

out_path = os.path.join(repo_root, 'translations', 'messages.pot')


def run_pybabel(cmd_args):
    try:
        subprocess.run(['pybabel'] + cmd_args, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


# Step 1: Extract messages to POT
print('Extracting messages...')
if not run_pybabel(['extract', '-F', 'babel.cfg', '-o', out_path, '.']):
    # Fallback: use Babel Python API directly
    from babel.messages.extract import extract_from_dir
    from babel.messages.catalog import Catalog
    from babel.messages.pofile import write_po
    import io

    catalog = Catalog()
    for filename, lineno, message, comments, context in extract_from_dir(
        repo_root,
        method_map=[
            ('**.py', 'python'),
            ('**/templates/**.html', 'jinja2'),
        ],
        options_map={
            '**/templates/**.html': {'extensions': 'jinja2.ext.i18n'},
        },
        comment_tags=('NOTE:',),
    ):
        catalog.add(message, locations=[(filename, lineno)], user_comments=comments)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        write_po(f, catalog)

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
    for lang in locales:
        print(f'Updating locale "{lang}"...')

        if run_pybabel(['update', '-i', out_path, '-d', locales_dir, '-l', lang]):
            continue

        print('`pybabel` CLI not available; falling back to Babel API for update_catalog')
        from babel.messages.frontend import update_catalog
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
        print('`pybabel` CLI not available; falling back to Babel API for compile_catalog')
        from babel.messages.frontend import compile_catalog
        compile_cmd = compile_catalog()
        compile_cmd.initialize_options()
        compile_cmd.directory = locales_dir
        compile_cmd.finalize_options()
        compile_cmd.run()

    print('Compilation complete.')
else:
    print('Skipping .mo compilation. Run with --compile when PO translation is ready.')
