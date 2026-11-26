# YouTube Shorts Daily Auto-Uploader (Google Drive -> YouTube Data API v3)

This lightweight, zero-third-party uploader runs daily on **GitHub Actions** (free tier) while your computer is off. Every day it checks your Google Drive **Queue** folder for the next vertical `.mp4` Short (and optional matching `.json` metadata file), publishes it directly to YouTube via the official [YouTube Data API v3 (`videos.insert`)](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert), and moves the uploaded files into your **Published** folder.

## Pre-Configured Google Drive Folders
- **Queue folder ID:** `1Vbk8tyYVgoYyZDIbXdIllpZU2pducPP7`
- **Published folder ID:** `14r5oeekOKaaaCahDcdNhCHuZpCa4DpmZ`

## 5-Minute One-Time Setup

1. **Create a Google Cloud Project & Enable APIs**
   - Open [Google Cloud Console](https://console.cloud.google.com/), create a new project, and enable both **YouTube Data API v3** and **Google Drive API**.
   - Under **APIs & Services -> OAuth consent screen**, configure your app (choose **External** and add your own Google email under **Test users**).
   - **Then click "Publish app" (status: In production).** If you leave it in *Testing*, Google expires the refresh token after 7 days and the daily upload silently stops working. You don't need Google verification for personal use; you'll just click past an "unverified app" warning once when signing in.
   - Under **APIs & Services -> Credentials**, click **Create Credentials -> OAuth client ID -> Desktop app**, then download the JSON file as `client_secret.json`.

2. **Generate Your Refresh Token (One Time)**
   ```bash
   pip install -r requirements.txt
   python get_refresh_token.py client_secret.json
   ```
   Sign in with the Google account that owns your YouTube channel and Google Drive. Copy the 3 printed values (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`).

3. **Add the secrets to this GitHub repository**
   - Do **not** commit `client_secret.json` (it's in `.gitignore`).
   - Go to **Settings -> Secrets and variables -> Actions -> New repository secret** and add:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
     - `GOOGLE_REFRESH_TOKEN`

4. **Test & Run Daily**
   - Drop any `.mp4` (plus an optional `<same_name>.json` modeled on `sample_metadata.json`) into your Google Drive `Queue` folder.
   - In GitHub, open the **Actions** tab -> **Daily YouTube Shorts Uploader** -> **Run workflow** to test immediately.
   - After that, it automatically runs every day at 6:00 PM CET / 5:00 PM GMT / 10:30 PM Sri Lanka Time (17:00 UTC — European peak Shorts window). You can follow the [YouTube Data API upload guide](https://developers.google.com/youtube/data/guides/uploading_a_video) to customize categories or privacy settings (`public`, `unlisted`, or `private`).

## Troubleshooting / things that will bite you

| Symptom | Cause | Fix |
|---|---|---|
| `these GitHub secrets are empty or not set` | Secrets not added | Step 3 above. Names must match exactly. |
| `invalid_grant` after about a week | OAuth app still in **Testing** | Publish the app (step 1), rerun `get_refresh_token.py`, update `GOOGLE_REFRESH_TOKEN`. |
| Video uploads but is stuck on **Private** and you get a YouTube email | Google Cloud projects created after 28 July 2020 that haven't passed the YouTube API audit have every API upload locked to private | Apply for the free [YouTube API Services audit](https://support.google.com/youtube/contact/yt_api_form). Until it's approved, open YouTube Studio and make each video public yourself. The log prints a `WARNING` when this happens. |
| Scheduled runs stop | GitHub turns off cron workflows after 60 days with no repo activity | Push any commit, or re-enable the workflow in the Actions tab. |
| Same video uploaded twice | Can't happen anymore: every uploaded file is tagged with its YouTube ID in Drive, and tagged files only get moved, never re-uploaded. | — |
