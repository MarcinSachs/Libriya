import os
import subprocess
import sys

def test_extract_messages_includes_new_strings():
    """Running the extraction script should produce a POT containing all
    recently added msgids.  This guards against cases where the extractor
    ignores calls with keyword arguments.  Use the Babel CLI directly so we
    exercise the same code users run manually.
    """
    pot_path = os.path.join(os.getcwd(), 'translations', 'messages.pot')
    # run pybabel extract directly rather than our wrapper script
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'babel.messages.frontend',
            'extract',
            '-F',
            'babel.cfg',
            '-o',
            pot_path,
            os.getcwd(),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Extraction failed: {result.stderr}"

    assert os.path.exists(pot_path), "POT file was not generated"
    content = open(pot_path, encoding='utf-8').read()
    # check for the strings we care about (quotes are escaped in the POT file)
    assert 'Super-admin replied to' in content
    assert 'New message from %(admin)s about' in content
    assert 'New reply from %(admin)s in' in content
