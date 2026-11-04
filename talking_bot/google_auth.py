"""One-time desktop OAuth: python -m talking_bot.google_auth."""
from google_auth_oauthlib.flow import InstalledAppFlow

from .calendar_api import ROOT, SCOPES, save_credentials


def main():
    client = ROOT / 'credentials.json'
    if not client.exists():
        print('Download your Desktop OAuth client JSON from Google Cloud and save it as credentials.json in the project folder.')
        return 1
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
        credentials = flow.run_local_server(host='localhost', port=0, timeout_seconds=180,
                                           authorization_prompt_message='Complete Google sign-in in the browser window.')
        save_credentials(credentials)
    except Exception as exc:
        print(f'Google sign-in failed ({type(exc).__name__}). Check the Desktop OAuth client and test-user settings.')
        return 1
    print('Calendar connected. token.json is private: never share or commit it. Restart your bot.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
