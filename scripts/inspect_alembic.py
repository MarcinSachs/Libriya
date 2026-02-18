from alembic.config import Config
from alembic.script import ScriptDirectory
import json

cfg = Config('migrations/alembic.ini')
script = ScriptDirectory.from_config(cfg)

print('Script dir:', script.dir)
try:
    print('Heads:', script.get_heads())
except Exception as e:
    print('get_heads error:', e)

try:
    revs = list(script.walk_revisions())
    print('Total revisions:', len(revs))
    for r in revs:
        print(r.revision, 'down_revision=', r.down_revision)
except Exception as e:
    print('walk_revisions error:', e)

try:
    # revision_map details
    rm = script.revision_map
    heads = list(rm.heads)
    print('revision_map heads count:', len(heads))
    for h in heads:
        print(' head:', h)
except Exception as e:
    print('revision_map error:', e)
