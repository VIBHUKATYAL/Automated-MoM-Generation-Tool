import urllib.request, urllib.parse, json, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
url = os.getenv('SUPABASE_URL')
req = urllib.request.Request(f'{url}/rest/v1/meetings?select=id,title,original_transcript,summary&order=created_at.desc&limit=10')
req.add_header('apikey', token)
req.add_header('Authorization', f'Bearer {token}')
req.add_header('Range', '0-15')
res = urllib.request.urlopen(req)
data = json.loads(res.read())
for d in data:
    if d['title'] == 'Text Transcript':
        c = d.get('original_transcript', '')
        if c and 'John:' not in c:
            print(f'---\nID: {d["id"]}')
            if c is None: c = 'NONE'
            print(f'TRANSCRIPT ({len(c)} chars): {repr(c[:100])}')
            s = d.get('summary', '')
            print(f'SUMMARY: {repr(s)}')
