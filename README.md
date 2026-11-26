# YouTube Shorts Daily Auto-Uploader (Google Drive -> YouTube Data API v3)

This lightweight, zero-third-party uploader runs daily on **GitHub Actions** (free tier) while your computer is off. Every day it checks your Google Drive **Queue** folder for the next vertical `.mp4` Short (and optional matching `.json` metadata file), publishes it directly to YouTube via the official [YouTube Data API v3 (`videos.insert`)](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert), and moves the uploaded files into your **Published** folder.

## Pre-Configured Google Drive Folders
- **Queue folder ID:** `1Vbk8tyYVgoYyZDIbXdIllpZU2pducPP7`
- **Published folder ID:** `14r5oeekOKaaaCahDcdNhCHuZpCa4DpmZ`

## 5-Minute One-Time Setup

1. **Create a Google Cloud Project & Enable APIs**
   - Open [Google Cloud Console](https://console.cloud.google.com/), create a new project, and enable both **YouTube Data API v3** and **Google Drive API**.
   - Under **APIs & Services -> OAuth consent screen**, configure your app (choose **External** and add your own Google email under **Test users**).
   - Under **APIs & Services -> Credentials**, click **Create Credentials -> OAuth client ID -> Desktop app**, then download the JSON file as `client_secret.json`.

2. **Generate Your Refresh Token (One Time)**
   ```bash
   pip install -r requirements.txt
   python get_refresh_token.py client_secret.json
   ```
   Sign in with the Google account that owns your YouTube channel and Google Drive. Copy the 3 printed values (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`).

3. **Push to a Private GitHub Repository**
   - Create a new **private** repository on GitHub and upload all files from this folder (including `.github/workflows/daily_upload.yml`).
   - Do **not** commit `client_secret.json`.
   - Go to **Settings -> Secrets and variables -> Actions -> New repository secret** and add:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
     - `GOOGLE_REFRESH_TOKEN`

4. **Test & Run Daily**
   - Drop any `.mp4` (plus an optional `<same_name>.json` modeled on `sample_metadata.json`) into your Google Drive `Queue` folder.
   - In GitHub, open the **Actions** tab -> **Daily YouTube Shorts Uploader** -> **Run workflow** to test immediately.
   - After that, it automatically runs every day at 6:00 PM CET / 5:00 PM GMT / 10:30 PM Sri Lanka Time (17:00 UTC — European peak Shorts window). You can follow the [YouTube Data API upload guide](https://developers.google.com/youtube/data/guides/uploading_a_video) to customize categories or privacy settings (`public`, `unlisted`, or `private`).
