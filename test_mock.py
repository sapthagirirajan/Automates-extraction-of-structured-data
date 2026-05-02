#!/usr/bin/env python3
import requests

with open('fixtures/resume_1.pdf', 'rb') as f:
    r = requests.post('http://127.0.0.1:8005/parse/resume', files={'file': f}, timeout=30)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        print('✓ Successfully parsed resume with mock mode')
        data = r.json()
        print(f'  model_used: {data.get("model_used")}')
        print(f'  candidate_name: {data.get("candidate_name")}')
    else:
        print(f'Error: {r.text[:500]}')
