import json
import time
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN='/var/lib/potato-audio/google-photos-token.json'
SCOPES=['https://www.googleapis.com/auth/photospicker.mediaitems.readonly']

creds=Credentials.from_authorized_user_file(TOKEN,SCOPES)

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN,'w') as f:
        f.write(creds.to_json())

headers={
    'Authorization':f'Bearer {creds.token}',
    'Content-Type':'application/json'
}

r=requests.post(
    'https://photospicker.googleapis.com/v1/sessions',
    headers=headers,
    json={}
)

r.raise_for_status()
session=r.json()

print("\nOPEN THIS URL IN YOUR BROWSER:\n")
print(session['pickerUri'])
print("\nWaiting for you to finish selecting photos...\n")

sid=session['id']

while True:
    r=requests.get(
        f'https://photospicker.googleapis.com/v1/sessions/{sid}',
        headers=headers
    )
    r.raise_for_status()
    status=r.json()

    if status.get('mediaItemsSet'):
        break

    time.sleep(3)

print("Selection complete.")

r=requests.get(
    'https://photospicker.googleapis.com/v1/mediaItems',
    headers=headers,
    params={'sessionId':sid,'pageSize':100}
)

r.raise_for_status()

with open('/var/lib/potato-audio/google-selected-photos.json','w') as f:
    json.dump(r.json(),f,indent=2)

print("Selected photo information saved.")
print("/var/lib/potato-audio/google-selected-photos.json")
