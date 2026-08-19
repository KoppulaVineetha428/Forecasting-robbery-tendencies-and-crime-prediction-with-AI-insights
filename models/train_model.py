"""
CrimeSense AI (India) - Model Training
Trains a RandomForestClassifier to predict crime_type from contextual features.
Risk score/level are derived from the model's predicted probabilities.
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "crime_data.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")


def main():
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["hour"] = df["time"].str.split(":").str[0].astype(int)

    cat_cols = ["city", "area", "area_type", "weather", "day"]
    encoders = {}
    enc_df = pd.DataFrame(index=df.index)
    for col in cat_cols:
        le = LabelEncoder()
        enc_df[col + "_enc"] = le.fit_transform(df[col])
        encoders[col] = le

    feature_cols = [c + "_enc" for c in cat_cols] + ["hour", "month"]
    X = pd.concat([enc_df[feature_cols[:-2]], df[["hour", "month"]]], axis=1)[feature_cols]
    y = df["crime_type"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    accuracy = round(accuracy_score(y_test, preds) * 100, 2)
    print(f"Test Accuracy: {accuracy}%")

    class_labels = sorted(y.unique().tolist())
    cm = confusion_matrix(y_test, preds, labels=class_labels).tolist()
    report = classification_report(y_test, preds, labels=class_labels, output_dict=True, zero_division=0)
    per_class_metrics = {
        label: {
            "precision": round(report[label]["precision"] * 100, 1),
            "recall": round(report[label]["recall"] * 100, 1),
            "f1": round(report[label]["f1-score"] * 100, 1),
            "support": int(report[label]["support"]),
        } for label in class_labels
    }

    friendly_names = {
        "city_enc": "City", "area_enc": "Area", "area_type_enc": "Area Type",
        "weather_enc": "Weather", "day_enc": "Day of Week", "hour": "Hour of Day", "month": "Month"
    }
    importances = model.feature_importances_
    feature_importance = sorted(
        [
            {"feature": friendly_names.get(f, f), "importance": round(float(imp) * 100, 2)}
            for f, imp in zip(feature_cols, importances)
        ],
        key=lambda x: x["importance"], reverse=True
    )

    evaluation = {
        "class_labels": class_labels,
        "confusion_matrix": cm,
        "per_class_metrics": per_class_metrics,
        "feature_importance": feature_importance,
        "macro_f1": round(report["macro avg"]["f1-score"] * 100, 1),
        "weighted_f1": round(report["weighted avg"]["f1-score"] * 100, 1),
    }
    joblib.dump(evaluation, os.path.join(MODEL_DIR, "evaluation.pkl"))

    # Build meta info used by the app (dropdown options, city->area map, etc.)
    city_area_map = df.groupby("city")["area"].unique().apply(list).to_dict()
    city_area_map = {k: sorted(v) for k, v in city_area_map.items()}

    meta = {
        "accuracy": accuracy,
        "cities": sorted(df["city"].unique().tolist()),
        "areas_by_city": city_area_map,
        "area_types": sorted(df["area_type"].unique().tolist()),
        "weather_options": sorted(df["weather"].unique().tolist()),
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "crime_types": sorted(df["crime_type"].unique().tolist()),
        "feature_cols": feature_cols,
    }

    joblib.dump(model, os.path.join(MODEL_DIR, "crime_model.pkl"))
    joblib.dump(encoders, os.path.join(MODEL_DIR, "encoders.pkl"))
    joblib.dump(meta, os.path.join(MODEL_DIR, "meta.pkl"))

    print("Saved model artifacts to", MODEL_DIR)


if __name__ == "__main__":
    main()
