import json
from pathlib import Path

p = Path(r'C:\Users\seamegdool\AppData\Local\Temp\planner-vgb3pkyo\qr-plan-design.json')
raw = p.read_bytes()
text = raw.decode('utf-8-sig')

# Replace Unicode curly quotes with ASCII straight quotes
text = text.replace('“', '"').replace('”', '"')
# Replace Unicode curly apostrophes
text = text.replace('‘', "'").replace('’', "'")
# Replace Unicode em-dash with ASCII double-dash
text = text.replace('—', '--')
# Replace mojibake em-dash patterns (double-encoded UTF-8)
text = text.replace('\xc3\xa2\xe2\x82\xac\xe2\x80\x9d', '--')

try:
    data = json.loads(text)
except json.JSONDecodeError as e:
    print('JSON error:', e)
    # Find the problematic area
    lines = text.split('\n')
    print('Line', e.lineno, ':', repr(lines[e.lineno-1]))
    raise

print('Parsed OK, items:', len(data['items']))
for item in data['items']:
    if item['id'] in ('qa-008', 'qa-009'):
        item['status'] = 'PASS'
        print(f"  {item['id']} -> PASS (already set or updated)")

out = json.dumps(data, indent=2, ensure_ascii=True)
p.write_bytes(out.encode('ascii'))
print('Saved ASCII-safe.')
# Verify cp1252 readable
p.read_text(encoding='cp1252')
print('cp1252 read OK')
