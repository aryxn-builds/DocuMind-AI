import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv('c:/Users/ay603/Desktop/DocuMind AI/apps/api/.env')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')
API_URL = 'http://127.0.0.1:8000/api/v1'

def get_token(email):
    res = httpx.post(
        f'{SUPABASE_URL}/auth/v1/token?grant_type=password',
        headers={'apikey': SUPABASE_KEY},
        json={'email': email, 'password': 'password123'}
    )
    return res.json()['access_token']

import jwt

try:
    token_a = get_token('adminA@documind.test')
    token_b = get_token('adminB@documind.test')

    print('Token A payload:', jwt.decode(token_a, options={'verify_signature': False}))
except Exception as e:
    print("Failed to get tokens:", e)
    sys.exit(1)

print('--- Starting E2E Phase 9 Test ---')

print('1. Getting signed url for User A...')
file_size = os.path.getsize('secret.pdf')
res = httpx.post(
    f'{API_URL}/documents/signed-url',
    headers={'Authorization': f'Bearer {token_a}'},
    json={'filename': 'secret.pdf', 'file_type': 'application/pdf', 'file_size_bytes': file_size}
)
try:
    res.raise_for_status()
except httpx.HTTPStatusError:
    print('Error Response:', res.text)
    sys.exit(1)
data = res.json()
doc_id = data['document_id']
signed_url = data['signed_url']
file_path = data['file_path']
print(f'Signed URL obtained for doc_id {doc_id}')

print('2. Uploading file to Supabase Storage...')
with open('secret.pdf', 'rb') as f:
    upload_res = httpx.put(signed_url, content=f.read(), headers={'Content-Type': 'application/pdf'})
upload_res.raise_for_status()
print('Upload complete.')

print('3. Registering document...')
reg_res = httpx.post(
    f'{API_URL}/documents/register',
    headers={'Authorization': f'Bearer {token_a}'},
    json={
        'document_id': doc_id,
        'file_path': file_path,
        'original_filename': 'secret.pdf',
        'file_type': 'application/pdf',
        'file_size_bytes': file_size
    }
)
reg_res.raise_for_status()
print('Registered.')

print("4. Polling for ready status...")
start_time = time.time()
with httpx.Client(timeout=60.0) as client:
    while True:
        stat = client.get(f'{API_URL}/documents/{doc_id}/status', headers={'Authorization': f'Bearer {token_a}'}).json()
        print(f"Status: {stat['status']} - {stat.get('job_progress', 0) * 100:.1f}% ({stat.get('job_stage', 'N/A')})")
        if stat['status'] == 'ready':
            break
        elif stat['status'] == 'failed':
            print("Document processing failed.")
            sys.exit(1)
        if time.time() - start_time > 300:
            print("Timeout waiting for document to be ready.")
            sys.exit(1)
        time.sleep(3)

print('5. Creating conversation...')
conv_res = httpx.post(
    f'{API_URL}/conversations',
    headers={'Authorization': f'Bearer {token_a}'},
    json={'title': 'Secret test', 'document_id': doc_id}
)
conv_res.raise_for_status()
conv_id = conv_res.json()['id']
print(f'Conversation created: {conv_id}')

print('6. Ask AI - exists...')
chat1_res = httpx.post(
    f'{API_URL}/conversations/{conv_id}/messages',
    headers={'Authorization': f'Bearer {token_a}', 'Content-Type': 'application/json'},
    json={'query': 'What is the secret password?', 'document_id': doc_id},
    timeout=60.0
)
answer1 = ''
for line in chat1_res.text.splitlines():
    if line.startswith('data: '):
        try:
            payload = json.loads(line[6:])
            if 'content' in payload:
                answer1 += payload['content']
        except:
            pass
print('Answer 1:', answer1)
if 'Banana42' not in answer1:
    print('Failed grounded answering test 1! Expected Banana42.')
else:
    print('Test 1 Passed.')

print('7. Ask AI - doesnt exist...')
chat2_res = httpx.post(
    f'{API_URL}/conversations/{conv_id}/messages',
    headers={'Authorization': f'Bearer {token_a}', 'Content-Type': 'application/json'},
    json={'query': 'What is the secret recipe?', 'document_id': doc_id},
    timeout=60.0
)
answer2 = ''
for line in chat2_res.text.splitlines():
    if line.startswith('data: '):
        try:
            payload = json.loads(line[6:])
            if 'content' in payload:
                answer2 += payload['content']
        except:
            pass
print('Answer 2:', answer2)
if 'find' not in answer2.lower() and 'document' not in answer2.lower() and 'provide' not in answer2.lower():
    print('Failed grounded answering test 2! Expected grounded failure.')
else:
    print('Test 2 Passed.')

print('8. User B tries to access User A document...')
b_res = httpx.post(
    f'{API_URL}/conversations/{conv_id}/messages',
    headers={'Authorization': f'Bearer {token_b}', 'Content-Type': 'application/json'},
    json={'query': 'What is the secret password?', 'document_id': doc_id},
    timeout=60.0
)
print('User B status for conv:', b_res.status_code)
if b_res.status_code not in (404, 403, 400):
    print('FAILED ISOLATION TEST! User B was able to call stream for User A convo.')
else:
    print('Test 3 Passed.')

print('9. Verifying persistence...')
hist = httpx.get(
    f'{API_URL}/conversations/{conv_id}',
    headers={'Authorization': f'Bearer {token_a}'}
)
hist.raise_for_status()
msgs = hist.json()['messages']
print(f'Total messages in DB: {len(msgs)}')
for m in msgs:
    print(f"- {m['role']}: {m['content'][:100]}...")

print('ALL TESTS FINISHED.')
