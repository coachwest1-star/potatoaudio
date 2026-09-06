import json
import os
import requests

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SOURCE = '/var/lib/potato-audio/google-selected-photos.json'
DEST = '/var/lib/potato-audio/photos'
TOKEN = '/var/lib/potato-audio/google-photos-token.json'

SCOPES = [
    'https://www.googleapis.com/auth/photospicker.mediaitems.readonly'
]

os.makedirs(DEST, exist_ok=True)

creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN, 'w') as f:
        f.write(creds.to_json())

headers = {
    'Authorization': f'Bearer {creds.token}'
}

with open(SOURCE) as f:
    data = json.load(f)

items = data.get('mediaItems', [])

print(f"Found {len(items)} selected media items.")

downloaded = 0
skipped = 0

for n, item in enumerate(items, 1):

    if item.get('type') != 'PHOTO':
        print(f"{n}/{len(items)} Skipping non-photo item")
        skipped += 1
        continue

    media = item.get('mediaFile', {})
    base = media.get('baseUrl')

    if not base:
        print(f"{n}/{len(items)} No baseUrl — skipping")
        skipped += 1
        continue

    mime = media.get('mimeType', 'image/jpeg')

    if mime == 'image/png':
        ext = '.png'
    elif mime == 'image/webp':
        ext = '.webp'
    else:
        ext = '.jpg'

    filename = f'photo-{n:03d}{ext}'
    path = os.path.join(DEST, filename)

    print(f"{n}/{len(items)} Downloading {filename}")

    url = base + '=w1920'

    r = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if r.ok:
        with open(path, 'wb') as f:
            f.write(r.content)

        downloaded += 1
        print(f"   OK {len(r.content) // 1024} KB")

    else:
        print(f"   ERROR HTTP {r.status_code}")
        print(r.text[:200])

print()
print(f"Downloaded: {downloaded}")
print(f"Skipped:    {skipped}")
print(f"Saved to:   {DEST}")
