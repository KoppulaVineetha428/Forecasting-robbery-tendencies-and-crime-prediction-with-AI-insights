"""
CrimeSense AI (India) - Synthetic Crime Dataset Generator
Generates a realistic synthetic crime dataset for major Indian cities/areas.
NOTE: This is SYNTHETIC data for demo/training purposes only - not real crime records.
"""
import random
import csv
import os
from datetime import datetime, timedelta

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# City -> areas, each area given a base "riskiness" 0-1 (higher = more crime prone)
CITY_AREAS = {
    "Bangalore": {
        "MG Road": 0.75, "Koramangala": 0.55, "Indiranagar": 0.5, "Whitefield": 0.35,
        "Jayanagar": 0.3, "Electronic City": 0.4, "Hebbal": 0.45, "Yelahanka": 0.25
    },
    "Mumbai": {
        "Andheri": 0.6, "Dadar": 0.55, "Bandra": 0.45, "Borivali": 0.3,
        "Kurla": 0.65, "Powai": 0.35, "Colaba": 0.4, "Malad": 0.4
    },
    "Delhi": {
        "Connaught Place": 0.7, "Karol Bagh": 0.6, "Dwarka": 0.35, "Saket": 0.4,
        "Rohini": 0.45, "Lajpat Nagar": 0.55, "Nehru Place": 0.6, "Vasant Kunj": 0.3
    },
    "Chennai": {
        "T Nagar": 0.6, "Anna Nagar": 0.4, "Velachery": 0.35, "Adyar": 0.3,
        "Guindy": 0.45, "Tambaram": 0.4, "Mylapore": 0.35, "Porur": 0.4
    },
    "Hyderabad": {
        "Hitech City": 0.35, "Ameerpet": 0.55, "Secunderabad": 0.5, "Banjara Hills": 0.35,
        "Dilsukhnagar": 0.55, "Madhapur": 0.35, "Kukatpally": 0.45, "Begumpet": 0.4
    },
    "Pune": {
        "Koregaon Park": 0.45, "Hinjewadi": 0.35, "Camp": 0.55, "Kothrud": 0.35,
        "Viman Nagar": 0.4, "Hadapsar": 0.45, "Aundh": 0.3, "Shivajinagar": 0.5
    },
    "Kolkata": {
        "Park Street": 0.6, "Salt Lake": 0.35, "Howrah": 0.55, "Gariahat": 0.45,
        "New Town": 0.3, "Esplanade": 0.6, "Behala": 0.4, "Dum Dum": 0.5
    },
    "Ahmedabad": {
        "Navrangpura": 0.45, "Satellite": 0.3, "Maninagar": 0.5, "Vastrapur": 0.35,
        "Bapunagar": 0.55, "Paldi": 0.4, "Chandkheda": 0.35, "Naranpura": 0.4
    },
    "Jaipur": {
        "MI Road": 0.55, "Malviya Nagar": 0.4, "Vaishali Nagar": 0.35, "C Scheme": 0.45,
        "Mansarovar": 0.35, "Sanganer": 0.4, "Bani Park": 0.4, "Jagatpura": 0.3
    },
    "Lucknow": {
        "Hazratganj": 0.55, "Gomti Nagar": 0.4, "Aliganj": 0.35, "Indira Nagar": 0.45,
        "Alambagh": 0.5, "Chowk": 0.55, "Aminabad": 0.5, "Mahanagar": 0.4
    },
}

# Approximate lat/long centers for cities (areas get small jitter around these)
CITY_COORDS = {
    "Bangalore": (12.9716, 77.5946), "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.7041, 77.1025), "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867), "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639), "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873), "Lucknow": (26.8467, 80.9462),
}

# Real-world calibration: relative crime-rate multipliers derived from NCRB
# "Crime in India 2022" report (crimes per lakh/million population across
# 19 major metros). This grounds the city-level baseline in actual reported
# statistics: Delhi is India's highest-crime metro, Kolkata is the safest
# for the 3rd year running, Pune/Hyderabad are also comparatively safe,
# while Ahmedabad/Jaipur/Chennai run above the metro average.
# Source: NCRB Crime in India 2022 (ncrb.gov.in); news analyses of that report.
CITY_RISK_MULTIPLIER = {
    "Delhi": 1.35,       # highest crime rate among all Indian metros (NCRB 2022)
    "Ahmedabad": 1.18,   # above-average metro crime rate
    "Jaipur": 1.15,      # above-average metro crime rate, high crimes-against-women rate
    "Chennai": 1.05,
    "Mumbai": 1.00,      # near metro average
    "Bangalore": 0.98,
    "Lucknow": 0.95,
    "Hyderabad": 0.80,   # NCRB: 3rd safest metro
    "Pune": 0.78,        # NCRB: 2nd safest metro
    "Kolkata": 0.55,     # NCRB: safest metro, 3 years running
}

CRIME_TYPES = ["Robbery", "Theft", "Assault", "Burglary", "Others"]
AREA_TYPES = ["Commercial", "Residential", "Industrial", "Educational"]
WEATHER = ["Clear", "Cloudy", "Rainy", "Foggy"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

AREA_TYPE_BY_AREA = {}  # cache consistent area_type per area


def pick_area_type(area):
    if area not in AREA_TYPE_BY_AREA:
        AREA_TYPE_BY_AREA[area] = random.choices(
            AREA_TYPES, weights=[0.4, 0.35, 0.1, 0.15]
        )[0]
    return AREA_TYPE_BY_AREA[area]


def risk_level_from_score(score):
    if score >= 0.66:
        return "High"
    if score >= 0.33:
        return "Medium"
    return "Low"


def hour_factor(hour):
    # Night hours (10PM-4AM) riskier, then early morning safer, evenings elevated
    if 22 <= hour or hour < 4:
        return 0.9
    if 4 <= hour < 8:
        return 0.35
    if 8 <= hour < 17:
        return 0.4
    if 17 <= hour < 22:
        return 0.7
    return 0.5


def weather_factor(w):
    return {"Clear": 0.4, "Cloudy": 0.5, "Rainy": 0.65, "Foggy": 0.6}[w]


def day_factor(day):
    return {"Friday": 0.65, "Saturday": 0.7, "Sunday": 0.55}.get(day, 0.45)


def choose_crime_type(risk_score, area_type, hour):
    # Strong, learnable relationship between area_type/time-of-day and crime_type,
    # with some noise so the model has to generalize (not memorize).
    weights = {"Robbery": 1.0, "Theft": 1.0, "Assault": 1.0, "Burglary": 1.0, "Others": 1.0}

    if area_type == "Commercial":
        weights["Robbery"] *= 9.0
        weights["Theft"] *= 3.0
    elif area_type == "Residential":
        weights["Burglary"] *= 10.0
        weights["Theft"] *= 2.0
    elif area_type == "Industrial":
        weights["Theft"] *= 9.0
        weights["Robbery"] *= 2.0
    elif area_type == "Educational":
        weights["Others"] *= 8.0
        weights["Assault"] *= 4.0

    is_night = hour >= 22 or hour < 4
    is_evening = 17 <= hour < 22
    if is_night:
        weights["Robbery"] *= 3.0
        weights["Assault"] *= 2.2
        weights["Burglary"] *= 1.8
    elif is_evening:
        weights["Assault"] *= 2.0
        weights["Robbery"] *= 1.5
    else:
        weights["Theft"] *= 1.6
        weights["Others"] *= 1.4

    if risk_score >= 0.66:
        weights["Robbery"] *= 1.6
        weights["Assault"] *= 1.4

    labels = list(weights.keys())
    w = list(weights.values())
    return random.choices(labels, weights=w)[0]


NARRATIVE_TEMPLATES = {
    "Robbery": [
        "A robbery was reported near {area}, {city} — valuables snatched from a pedestrian.",
        "An armed robbery incident was reported at a shop in {area}, {city}.",
        "A chain/bag-snatching robbery was reported on the main road in {area}, {city}.",
    ],
    "Theft": [
        "A theft case was reported in {area}, {city} — a two-wheeler was stolen from a parking area.",
        "A pickpocketing incident was reported in a crowded market in {area}, {city}.",
        "A shop reported theft of goods overnight in {area}, {city}.",
    ],
    "Assault": [
        "An assault case was reported following an altercation in {area}, {city}.",
        "A physical assault was reported near a public gathering spot in {area}, {city}.",
    ],
    "Burglary": [
        "A house burglary was reported in a residential complex in {area}, {city} while occupants were away.",
        "Forced entry and burglary was reported at a residence in {area}, {city}.",
    ],
    "Others": [
        "A miscellaneous public-nuisance/disturbance case was reported in {area}, {city}.",
        "A minor altercation/disturbance was reported near an institution in {area}, {city}.",
    ],
}


def make_narrative(crime_type, city, area):
    template = random.choice(NARRATIVE_TEMPLATES[crime_type])
    return template.format(area=area, city=city)


def generate(n_rows=6000):
    rows = []
    start_date = datetime(2023, 1, 1)
    row_id = 1
    for _ in range(n_rows):
        city = random.choice(list(CITY_AREAS.keys()))
        area = random.choice(list(CITY_AREAS[city].keys()))
        base_risk = CITY_AREAS[city][area]
        area_type = pick_area_type(f"{city}-{area}")

        days_offset = random.randint(0, 730)
        date_obj = start_date + timedelta(days=days_offset)
        hour = random.randint(0, 23)
        minute = random.choice([0, 15, 30, 45])
        day_name = DAYS[date_obj.weekday()]
        weather = random.choice(WEATHER)

        score = (
            0.45 * base_risk
            + 0.25 * hour_factor(hour)
            + 0.15 * weather_factor(weather)
            + 0.15 * day_factor(day_name)
        )
        score *= CITY_RISK_MULTIPLIER.get(city, 1.0)
        score = max(0.0, min(1.0, score + random.uniform(-0.08, 0.08)))
        risk_level = risk_level_from_score(score)
        crime_type = choose_crime_type(score, area_type, hour)

        lat0, lon0 = CITY_COORDS[city]
        lat = round(lat0 + random.uniform(-0.06, 0.06), 4)
        lon = round(lon0 + random.uniform(-0.06, 0.06), 4)

        rows.append({
            "id": row_id,
            "date": date_obj.strftime("%Y-%m-%d"),
            "time": f"{hour:02d}:{minute:02d}",
            "day": day_name,
            "city": city,
            "area": area,
            "area_type": area_type,
            "weather": weather,
            "crime_type": crime_type,
            "risk_score": round(score * 100, 1),
            "risk_level": risk_level,
            "latitude": lat,
            "longitude": lon,
            "narrative": make_narrative(crime_type, city, area),
        })
        row_id += 1
    return rows


def main():
    rows = generate(6000)
    out_path = os.path.join(BASE_DIR, "crime_data.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
