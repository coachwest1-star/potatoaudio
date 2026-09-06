from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

flow = InstalledAppFlow.from_client_secrets_file(
    '/var/lib/potato-audio/google-credentials.json',
    SCOPES
)

creds = flow.run_local_server(
    host='localhost',
    port=8089,
    open_browser=False,
    authorization_prompt_message='\nOpen this URL in your Mac browser:\n{url}\n'
)

with open('/var/lib/potato-audio/google-token.json', 'w') as f:
    f.write(creds.to_json())

print("\nGoogle Calendar authorization complete!")
