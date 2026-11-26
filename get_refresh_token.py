"""One-time OAuth 2.0 helper to generate a Google refresh token for YouTube + Drive."""
import json
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive",
]


def main():
    secrets_file = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    with open(secrets_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
    client_cfg = raw.get("installed") or raw.get("web") or {}

    print("\n=== Add these 3 secrets to GitHub Actions ===")
    print(f"GOOGLE_CLIENT_ID:     {client_cfg.get('client_id', '')}")
    print(f"GOOGLE_CLIENT_SECRET: {client_cfg.get('client_secret', '')}")
    print(f"GOOGLE_REFRESH_TOKEN: {creds.refresh_token}")
    print("=============================================\n")


if __name__ == "__main__":
    main()
