# Practice Friction Finder

Practice Friction Finder is a lightweight Streamlit app for therapists and small practice owners. It helps someone notice where their practice may be leaking time, energy, or right-fit clients, while helping Brittany and Nick learn what practice owners are actually struggling with.

This is a product discovery tool. It is not a clinical diagnosis, a business diagnosis, or a prescription for what someone should do next.

## Run Locally

```bash
python3 -m streamlit run friction_audit.py
```

The app is intentionally simple:

- No login
- No email sending
- No database
- Local CSV backup for testing
- Google Sheets saving for deployment

## What Gets Saved

Every completed audit is saved locally to:

```text
friction_audit_results.csv
```

If Google Sheets secrets are configured, the same row is also saved to a Google Sheet.

The saved fields are:

- Timestamp
- Optional name, email, practice name, and website
- Role and practice stage
- Answer selections as JSON
- AI attitude answer
- Primary and secondary friction area
- Result accuracy
- Optional free-text reflections
- Conversation opt-in
- Follow-up email, if provided

## Google Sheets Setup

Use Google Sheets for deployed submissions because local CSV files on Streamlit Community Cloud are not reliable long-term storage.

### 1. Create The Google Sheet

1. Create a new Google Sheet.
2. Rename the first tab to `Responses`.
3. Copy the spreadsheet ID from the URL.

The spreadsheet ID is the long value between `/d/` and `/edit` in the Google Sheets URL.

### 2. Create A Google Service Account

1. Go to Google Cloud Console.
2. Create a new project or use an existing one.
3. Enable the Google Sheets API.
4. Enable the Google Drive API.
5. Create a service account.
6. Create a JSON key for that service account.
7. Open the JSON key file and copy its values.

### 3. Share The Sheet

In the JSON key, find `client_email`. It will look like an email address.

Share the Google Sheet with that `client_email` and give it editor access. If you skip this step, the app will not be able to write to the sheet.

### 4. Add Streamlit Secrets

In Streamlit Community Cloud, open the app settings and add secrets like this:

```toml
[google_sheet]
spreadsheet_id = "YOUR_SPREADSHEET_ID"
worksheet_name = "Responses"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
-----END PRIVATE KEY-----"""
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CLIENT_CERT_URL"
universe_domain = "googleapis.com"
```

Keep the line breaks in `private_key`. Triple quotes help Streamlit read it correctly.

### 5. Test Saving

1. Deploy or run the app with secrets configured.
2. Complete one test audit.
3. Confirm a new row appears in the `Responses` tab.
4. Save the post-result quick check.
5. Confirm the same row updates with result accuracy, contact info, and conversation opt-in.

If the Google Sheet does not update, check:

- The spreadsheet ID is correct.
- The tab name matches `worksheet_name`.
- The Sheet was shared with the service account `client_email`.
- Google Sheets API and Google Drive API are enabled.
- Streamlit secrets were pasted without missing quotes or private key line breaks.

The app still saves a local CSV backup, but deployed data should be checked in Google Sheets.

## What The Finder Is For

The finder is meant to give therapists and practice owners a warm, useful reflection on patterns like client volume, client fit, messaging clarity, marketing discomfort, admin burden, AI uncertainty, consultation conversion, referral dependence, and group practice systems.

For Brittany and Nick, the saved responses can help reveal which practice problems feel most urgent, confusing, emotionally loaded, or worth solving.

## Deploy To Streamlit Community Cloud

When you are ready:

1. Create or use a GitHub repository.
2. Push these files to the repo:
   - `friction_audit.py`
   - `requirements.txt`
   - `README.md`
3. Go to Streamlit Community Cloud and create a new app from that GitHub repo.
4. Set the main file path to:

```text
friction_audit.py
```

5. Add the Google Sheets secrets above.
6. Deploy from Streamlit Community Cloud.
