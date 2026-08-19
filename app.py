"""
CrimeSense AI (India) - Forecasting Robbery Tendencies & Crime Prediction
Flask backend: auth, dashboard, dataset view, preprocessing, training, prediction,
hotspot analysis, and reports.
"""
import os
import sqlite3
import subprocess
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

import joblib
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DB_PATH = os.path.join(BASE_DIR, "database", "crimesense.db")
DATA_PATH = os.path.join(BASE_DIR, "data", "crime_data.csv")

app = Flask(__name__)
app.secret_key = "crimesense-india-dev-secret-change-me"


def load_artifacts():
    model = joblib.load(os.path.join(MODEL_DIR, "crime_model.pkl"))
    encoders = joblib.load(os.path.join(MODEL_DIR, "encoders.pkl"))
    meta = joblib.load(os.path.join(MODEL_DIR, "meta.pkl"))
    eval_path = os.path.join(MODEL_DIR, "evaluation.pkl")
    evaluation = joblib.load(eval_path) if os.path.exists(eval_path) else None
    df = pd.read_csv(DATA_PATH)
    return model, encoders, meta, evaluation, df


model, encoders, meta, evaluation, df = load_artifacts()


# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, city TEXT, area TEXT, area_type TEXT, weather TEXT,
            day TEXT, date TEXT, time TEXT,
            predicted_crime_type TEXT, risk_score REAL, risk_level TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            relation TEXT,
            phone TEXT,
            email TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            latitude REAL,
            longitude REAL,
            note TEXT,
            address TEXT,
            email_status TEXT,
            sms_status TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    # seed a demo user if none exists
    existing = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    if existing == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            ("admin", generate_password_hash("admin123"), datetime.now().isoformat())
        )
        conn.commit()
    conn.close()


init_db()


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- Auth Routes ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.")
            return render_template("register.html")
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already taken.")
            conn.close()
            return render_template("register.html")
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            (username, generate_password_hash(password), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        flash("Account created. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- App Routes ----------------
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", meta=meta, username=session.get("username"))


@app.route("/dataset")
@login_required
def dataset_page():
    return render_template("dataset.html", meta=meta, username=session.get("username"))


@app.route("/preprocessing")
@login_required
def preprocessing_page():
    return render_template("preprocessing.html", meta=meta, username=session.get("username"))


@app.route("/train")
@login_required
def train_page():
    return render_template("train.html", meta=meta, username=session.get("username"))


@app.route("/predict")
@login_required
def predict_page():
    return render_template("predict.html", meta=meta, username=session.get("username"))


@app.route("/hotspot")
@login_required
def hotspot_page():
    return render_template("hotspot.html", meta=meta, username=session.get("username"))


@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html", meta=meta, username=session.get("username"))


@app.route("/model-insights")
@login_required
def model_insights_page():
    return render_template("model_insights.html", meta=meta, username=session.get("username"))


@app.route("/sos")
@login_required
def sos_page():
    return render_template("sos.html", meta=meta, username=session.get("username"))


@app.route("/contacts")
@login_required
def contacts_page():
    return render_template("contacts.html", meta=meta, username=session.get("username"))


# ---------------- API ----------------
@app.route("/api/stats")
@login_required
def api_stats():
    by_city = df.groupby("city")["risk_score"].mean().sort_values(ascending=False).head(10)
    by_crime = df["crime_type"].value_counts()
    risk_dist = df["risk_level"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
    by_month = df.copy()
    by_month["month"] = pd.to_datetime(by_month["date"]).dt.strftime("%b")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_counts = by_month.groupby("month").size().reindex(month_order).fillna(0)

    return jsonify({
        "total_crimes": len(df),
        "robberies": int((df["crime_type"] == "Robbery").sum()),
        "high_risk_areas": int(df[df["risk_level"] == "High"]["area"].nunique()),
        "accuracy": meta["accuracy"],
        "cities": list(by_city.index),
        "city_scores": [round(v, 2) for v in by_city.values],
        "crime_labels": list(by_crime.index),
        "crime_counts": [int(v) for v in by_crime.values],
        "risk_labels": list(risk_dist.index),
        "risk_counts": [int(v) for v in risk_dist.values],
        "month_labels": month_order,
        "month_counts": [int(v) for v in monthly_counts.values],
    })


@app.route("/api/dataset")
@login_required
def api_dataset():
    page = int(request.args.get("page", 1))
    per_page = 15
    start = (page - 1) * per_page
    end = start + per_page
    rows = df.iloc[start:end].to_dict(orient="records")
    return jsonify({"rows": rows, "total": len(df), "page": page, "per_page": per_page})


@app.route("/api/cities/<city>/areas")
@login_required
def areas_for_city(city):
    return jsonify(meta["areas_by_city"].get(city, []))


@app.route("/api/hotspot-points")
@login_required
def hotspot_points():
    city = request.args.get("city")
    data = df if not city else df[df["city"] == city]
    if len(data) > 1500:
        data = data.sample(1500, random_state=1)
    heat_points = data[["latitude", "longitude", "risk_score"]].values.tolist()

    # Individual incident markers (capped for performance) for click-to-inspect popups
    marker_sample = data if len(data) <= 400 else data.sample(400, random_state=2)
    incidents = marker_sample[[
        "latitude", "longitude", "city", "area", "crime_type",
        "date", "time", "risk_level", "risk_score", "narrative"
    ]].to_dict(orient="records")

    return jsonify({"points": heat_points, "incidents": incidents})


@app.route("/api/train", methods=["POST"])
@login_required
def api_train():
    """Re-runs the training script and reloads artifacts in-memory."""
    global model, encoders, meta, evaluation, df
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "models", "train_model.py")],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return jsonify({"success": False, "error": result.stderr[-500:]}), 400
        model, encoders, meta, evaluation, df = load_artifacts()
        return jsonify({"success": True, "accuracy": meta["accuracy"], "log": result.stdout[-500:]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


def encode_input(payload):
    row = {}
    for col in ["city", "area", "area_type", "weather", "day"]:
        le = encoders[col]
        val = payload[col]
        if val not in le.classes_:
            val = le.classes_[0]
        row[col + "_enc"] = le.transform([val])[0]
    row["hour"] = int(payload["time"].split(":")[0])
    row["month"] = pd.to_datetime(payload["date"]).month
    return pd.DataFrame([row])[meta["feature_cols"]]


@app.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    payload = request.get_json()
    try:
        X = encode_input(payload)
        pred = model.predict(X)[0]
        proba = model.predict_proba(X)[0]
        classes = list(model.classes_)
        prob_map = {c: round(float(p) * 100, 1) for c, p in zip(classes, proba)}
        risk_score = round(float(max(proba)) * 100, 1)
        risk_level = "High" if risk_score >= 66 else ("Medium" if risk_score >= 40 else "Low")

        suggestions = {
            "High": "Increased patrolling recommended. Deploy additional CCTV and improve street lighting in this zone during the selected time slot.",
            "Medium": "Periodic patrols and community awareness advised for this location/time combination.",
            "Low": "Current safety infrastructure appears adequate based on historical patterns.",
        }

        conn = get_db()
        conn.execute("""
            INSERT INTO predictions (username, city, area, area_type, weather, day, date, time,
                predicted_crime_type, risk_score, risk_level, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session.get("username"), payload["city"], payload["area"], payload["area_type"],
            payload["weather"], payload["day"], payload["date"], payload["time"],
            pred, risk_score, risk_level, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        # ---- Previous / similar cases at this exact location ----
        loc_df = df[(df["city"] == payload["city"]) & (df["area"] == payload["area"])]
        similar_cases = (
            loc_df.sort_values("date", ascending=False)
            .head(5)[["date", "time", "day", "crime_type", "risk_score", "risk_level", "weather", "narrative"]]
            .to_dict(orient="records")
        )

        # ---- Location-specific stats: monthly trend, crime type distribution, top risk areas in this city ----
        loc_month = loc_df.copy()
        month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        if len(loc_month):
            loc_month["month"] = pd.to_datetime(loc_month["date"]).dt.strftime("%b")
            monthly = loc_month.groupby("month").size().reindex(month_labels).fillna(0)
        else:
            monthly = pd.Series([0]*12, index=month_labels)

        type_dist = loc_df["crime_type"].value_counts()

        city_df = df[df["city"] == payload["city"]]
        top_areas_city = city_df.groupby("area")["risk_score"].mean().sort_values(ascending=False).head(5)

        location_stats = {
            "area_case_count": int(len(loc_df)),
            "month_labels": month_labels,
            "month_counts": [int(v) for v in monthly.values],
            "type_labels": list(type_dist.index),
            "type_counts": [int(v) for v in type_dist.values],
            "top_areas_labels": list(top_areas_city.index),
            "top_areas_scores": [round(float(v), 1) for v in top_areas_city.values],
        }

        return jsonify({
            "success": True,
            "predicted_crime_type": pred,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "suggested_action": suggestions[risk_level],
            "probabilities": prob_map,
            "similar_cases": similar_cases,
            "location_stats": location_stats,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/recent-predictions")
@login_required
def recent_predictions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM predictions ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/model-insights")
@login_required
def api_model_insights():
    if evaluation is None:
        return jsonify({"available": False})
    return jsonify({
        "available": True,
        "class_labels": evaluation["class_labels"],
        "confusion_matrix": evaluation["confusion_matrix"],
        "per_class_metrics": evaluation["per_class_metrics"],
        "feature_importance": evaluation["feature_importance"],
        "macro_f1": evaluation["macro_f1"],
        "weighted_f1": evaluation["weighted_f1"],
        "accuracy": meta["accuracy"],
    })


# ---------------- Emergency Contacts ----------------
@app.route("/api/contacts", methods=["GET"])
@login_required
def get_contacts():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM emergency_contacts WHERE username = ? ORDER BY id DESC",
        (session["username"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/contacts", methods=["POST"])
@login_required
def add_contact():
    payload = request.get_json()
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO emergency_contacts (username, name, relation, phone, email, created_at) VALUES (?,?,?,?,?,?)",
        (session["username"], name, payload.get("relation", ""), payload.get("phone", ""),
         payload.get("email", ""), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_contact(contact_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM emergency_contacts WHERE id = ? AND username = ?",
        (contact_id, session["username"])
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ---------------- SOS Sending Helpers ----------------
def send_sos_email(to_addresses, subject, body):
    email_addr = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_APP_PASSWORD")
    smtp_server = os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))

    if not email_addr or not app_password or not to_addresses:
        return "skipped (email not configured or no recipient emails)"

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = email_addr
        msg["To"] = ", ".join(to_addresses)

        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(email_addr, app_password)
            server.sendmail(email_addr, to_addresses, msg.as_string())
        return f"sent to {len(to_addresses)} recipient(s)"
    except Exception as e:
        return f"failed: {e}"


def send_sos_sms(to_numbers, body):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")

    if not sid or not token or not from_number or not to_numbers or TwilioClient is None:
        return "skipped (SMS not configured or no recipient numbers)"

    try:
        client = TwilioClient(sid, token)
        results = []
        for number in to_numbers:
            try:
                client.messages.create(body=body, from_=from_number, to=number)
                results.append(f"{number}: sent")
            except Exception as e:
                results.append(f"{number}: failed ({e})")
        return "; ".join(results)
    except Exception as e:
        return f"failed: {e}"


@app.route("/api/sos/trigger", methods=["POST"])
@login_required
def trigger_sos():
    payload = request.get_json() or {}
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    note = payload.get("note", "").strip() or "No additional details provided."
    address = payload.get("address", "")

    conn = get_db()
    contacts = conn.execute(
        "SELECT * FROM emergency_contacts WHERE username = ?", (session["username"],)
    ).fetchall()

    maps_link = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else "location unavailable"
    body = (
        f"SOS ALERT from {session['username']} (sent via CrimeSense AI)\n\n"
        f"Message: {note}\n"
        f"Location: {address or 'Unknown address'}\n"
        f"Coordinates: {lat}, {lon}\n"
        f"Map link: {maps_link}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"This is an automated emergency alert. Please check on this person immediately."
    )

    to_emails = [c["email"] for c in contacts if c["email"]]
    # E.164-ish formatting note left to the user; we pass through as entered
    to_numbers = [c["phone"] for c in contacts if c["phone"]]

    email_status = send_sos_email(to_emails, "🚨 SOS ALERT - Immediate Attention Needed", body)
    sms_status = send_sos_sms(to_numbers, body)

    conn.execute("""
        INSERT INTO sos_alerts (username, latitude, longitude, note, address, email_status, sms_status, created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (session["username"], lat, lon, note, address, email_status, sms_status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "contacts_notified": len(contacts),
        "email_status": email_status,
        "sms_status": sms_status,
    })


@app.route("/api/sos/history")
@login_required
def sos_history():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sos_alerts WHERE username = ? ORDER BY id DESC LIMIT 20",
        (session["username"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/reports")
@login_required
def api_reports():
    yearly = df.copy()
    yearly["year"] = pd.to_datetime(yearly["date"]).dt.year
    yearly_counts = yearly.groupby("year").size()

    by_time = df.copy()
    def bucket(h):
        if 0 <= h < 6:
            return "Night (12AM-6AM)"
        if 6 <= h < 12:
            return "Morning (6AM-12PM)"
        if 12 <= h < 18:
            return "Afternoon (12PM-6PM)"
        return "Evening (6PM-12AM)"
    by_time["bucket"] = by_time["time"].str.split(":").str[0].astype(int).apply(bucket)
    time_counts = by_time["bucket"].value_counts().reindex(
        ["Night (12AM-6AM)", "Morning (6AM-12PM)", "Afternoon (12PM-6PM)", "Evening (6PM-12AM)"]
    ).fillna(0)

    top_areas = df.groupby(["city", "area"]).size().sort_values(ascending=False).head(5)
    top_area_labels = [f"{a} ({c})" for (c, a) in top_areas.index]

    return jsonify({
        "years": [str(y) for y in yearly_counts.index],
        "year_counts": [int(v) for v in yearly_counts.values],
        "time_labels": list(time_counts.index),
        "time_counts": [int(v) for v in time_counts.values],
        "top_area_labels": top_area_labels,
        "top_area_counts": [int(v) for v in top_areas.values],
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  CrimeSense AI (India) - Crime Prediction System")
    print("  Running at http://127.0.0.1:5000")
    print("  Default login -> username: admin / password: admin123")
    print("=" * 55)
    app.run(debug=True, port=5000)
