from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
import time
import logging

# ======================================================
# APP CONFIGURATION
# ======================================================

app = Flask(__name__)
CORS(app)
app.config["JSON_SORT_KEYS"] = False

logging.basicConfig(level=logging.INFO)

# ======================================================
# SUPABASE SINGLETON CLIENT
# ======================================================

_supabase = None

def get_supabase():
    global _supabase

    if _supabase is not None:
        return _supabase

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not configured")

    _supabase = create_client(url, key)
    return _supabase


# ======================================================
# UTILITY FUNCTIONS
# ======================================================

def normalize(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError("Values must be numeric")

    return max(0.0, min(1.0, value))


def calculate_stress(gsr, sound, accel):
    stress = (
        0.4 * gsr +
        0.3 * sound +
        0.3 * accel
    )
    return round(stress, 4)


# ======================================================
# ROUTES
# ======================================================

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "NeuroLab API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "post_data": "/v1/data"
        }
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time())
    }), 200


@app.route("/v1/data", methods=["POST"])
def receive_data():
    try:
        payload = request.get_json(silent=True)

        if not payload:
            return jsonify({"error": "Invalid JSON body"}), 400

        required_fields = ["device_id", "gsr", "sound", "accel"]

        missing_fields = [
            field for field in required_fields if field not in payload
        ]

        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing": missing_fields
            }), 400

        device_id = str(payload["device_id"]).strip()

        if not device_id:
            return jsonify({"error": "device_id cannot be empty"}), 400

        gsr = normalize(payload["gsr"])
        sound = normalize(payload["sound"])
        accel = normalize(payload["accel"])

        stress_index = calculate_stress(gsr, sound, accel)

        alert = None
        if stress_index > 0.7:
            alert = "Possible overstimulation detected"

        timestamp = int(time.time())

        supabase = get_supabase()

        insert_result = supabase.table("sensor_data").insert({
            "device_id": device_id,
            "gsr": gsr,
            "sound": sound,
            "accel": accel,
            "stress_index": stress_index,
            "timestamp": timestamp
        }).execute()

        logging.info(f"Stored data for device {device_id}")

        return jsonify({
            "status": "stored",
            "stress_index": stress_index,
            "alert": alert,
            "timestamp": timestamp
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except RuntimeError as re:
        logging.error(str(re))
        return jsonify({"error": str(re)}), 500

    except Exception as e:
        logging.exception("Unexpected server error")
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e)
        }), 500


# ======================================================
# VERCEL ENTRYPOINT
# ======================================================
# Vercel automatically detects `app`