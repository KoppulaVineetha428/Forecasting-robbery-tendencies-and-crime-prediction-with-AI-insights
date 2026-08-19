# CrimeSense AI (India) — Crime Prediction System

An end-to-end Flask + Machine Learning web app that forecasts robbery/crime
risk for Indian cities, with a dashboard, dataset explorer, training
pipeline, prediction tool, hotspot heatmap, and reports.

⚠️ **The dataset (`data/crime_data.csv`) is SYNTHETIC** — generated with
realistic patterns for demo purposes. It is NOT real crime data.

## Features
- Login / Register (SQLite-backed, hashed passwords)
- Dashboard — KPIs + monthly trend + crime-type distribution + city risk chart
- Dataset — paginated table of the 6,000-row dataset (city-level risk calibrated to real NCRB 2022 crime-rate data)
- Preprocessing — shows the cleaning/encoding steps applied
- Train Model — retrain the Random Forest live from the UI
- Model Insights — feature importance, confusion matrix, precision/recall per class
- AI Risk Predictor — pick city/area/weather/day/time → get predicted crime type, risk score, risk level, similar past cases, and location-specific charts
- Hotspot Analysis — Leaflet.js heatmap over India with clickable incident markers
- Reports — yearly trend, time-of-day breakdown, top 5 risk areas, recent predictions log
- **🚨 SOS Emergency Alerts** — one-tap button that captures your live GPS location and
  emails/texts all your saved emergency contacts
- **Emergency Contacts** — manage the people notified when SOS is triggered

## Requirements
- Python 3.10–3.14 (tested with 3.14.4)
- Internet connection on first page load (Chart.js / Leaflet load from a CDN with
  automatic fallback sources if one is blocked)

## Setup & Run

```bash
# 1. Go to the project folder
cd crimesense-india

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

### Default login
```
username: admin
password: admin123
```
Or click "Register" to create your own account.

## Setting up SOS (Email + SMS alerts)

The SOS feature works out of the box for **logging** alerts (visible in the Recent
Alerts table), but actually **sending** real emails/texts requires you to connect
your own free accounts — I can't send messages from your app without your own
credentials plugged in.

**1. Copy the config template**
```
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
```

**2. Fill in your Gmail credentials (for email alerts)**
- Turn on 2-Step Verification: https://myaccount.google.com/security
- Create an App Password: https://myaccount.google.com/apppasswords
- Put your Gmail address + the 16-character app password into `.env`
  (do NOT use your normal Gmail password — it won't work)

**3. Fill in your Twilio credentials (for SMS alerts)**
- Sign up free: https://www.twilio.com/try-twilio
- Copy your Account SID + Auth Token from the Twilio Console
- Get a free trial phone number (Console → Phone Numbers → Buy a number)
- ⚠️ **Twilio trial accounts can only text phone numbers you've manually
  "verified"** in the Twilio Console (Console → Verified Caller IDs). To message
  any number freely, you need to upgrade to a paid Twilio account (a few dollars
  covers a lot of SMS).

**4. Restart the app** — `python app.py` will now pick up the `.env` values
automatically and actually send email/SMS on SOS trigger.

**5. Add emergency contacts** in the app under "Emergency Contacts" before
testing the SOS button.

If `.env` is left unconfigured, SOS alerts still get logged in the app (so you
can demo the feature and show the history table) but email/SMS status will show
"skipped (not configured)" — this is expected, not a bug.



## Regenerating data / retraining the model (optional)
The model is already trained and included (`models/*.pkl`), so the app
works out of the box. To regenerate everything from scratch:

```bash
python data/generate_dataset.py   # creates data/crime_data.csv
python models/train_model.py      # trains model -> models/*.pkl
```
You can also retrain directly from the **Train Model** page in the UI.

## Project Structure
```
crimesense-india/
├── app.py                    # Flask app (routes + API)
├── requirements.txt
├── data/
│   ├── generate_dataset.py   # synthetic India crime data generator
│   └── crime_data.csv        # generated dataset (6,000 rows, 10 cities)
├── models/
│   ├── train_model.py        # trains RandomForestClassifier
│   ├── crime_model.pkl
│   ├── encoders.pkl
│   └── meta.pkl
├── database/
│   └── crimesense.db         # created automatically on first run (users, predictions)
├── templates/                # Jinja2 HTML pages
└── static/
    ├── css/style.css
    └── js/app.js
```

## Notes
- Model accuracy is ~57% across 5 crime-type classes (vs ~20% random
  baseline) — realistic for a demo model on synthetic multi-class data.
- The heatmap and charts are backed by real (synthetic) data queries, not
  hard-coded numbers — try changing filters and retraining to see values
  update.
