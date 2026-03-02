from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
import time
import logging

# ==============================
# App Config
# ==============================
app = Flask(__name__)
CORS(app)

app.config["JSON_SORT_KEYS"] = False

logging.basicConfig(level=logging.INFO)

# ==============================
# Supabase Client (Singleton)
# ==============================
_supabase_client = None

def get_supabase():
    global _supabase_client

    if _supabase_client:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("Missing Supabase environment variables")

    _supabase_client = create_client(url, key)
    return _supabase_client

# ==============================
# Utility Functions
# ==============================
def normalize(value):
    """Clamp value between 0 and 1"""
    return min(max(float(value), 0.0), 1.0)

def calculate_stress(gsr, sound, accel):
    return round(
        (0.4 * gsr) +
        (0.3 * sound) +
        (0.3 * accel),
        4
    )

# ==============================
# Health Check
# ==============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "NeuroLab Backend Running 🚀",
        "timestamp": int(time.time())
    }), 200

# ==============================
# Receive IoT Data
# ==============================
@app.route("/v1/data", methods=["POST"])
def receive_data():
    try:
        payload = request.get_json(silent=True)

        if not payload:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        required_fields = ["device_id", "gsr", "sound", "accel"]

        missing = [field for field in required_fields if field not in payload]
        if missing:
            return jsonify({
                "error": "Missing required fields",
                "missing": missing
            }), 400

        device_id = str(payload["device_id"]).strip()

        if not device_id:
            return jsonify({"error": "device_id cannot be empty"}), 400

        try:
            gsr = normalize(payload["gsr"])
            sound = normalize(payload["sound"])
            accel = normalize(payload["accel"])
        except Exception:
            return jsonify({"error": "gsr, sound and accel must be numeric"}), 400

        stress_index = calculate_stress(gsr, sound, accel)

        alert = None
        if stress_index > 0.7:
            alert = "Possible overstimulation detected"

        timestamp = int(time.time())

        supabase = get_supabase()

        insert_response = supabase.table("sensor_data").insert({
            "device_id": device_id,
            "gsr": gsr,
            "sound": sound,
            "accel": accel,
            "stress_index": stress_index,
            "timestamp": timestamp
        }).execute()

        logging.info(f"Data stored for device {device_id}")

        return jsonify({
            "status": "Data stored successfully",
            "data": {
                "device_id": device_id,
                "stress_index": stress_index,
                "alert": alert,
                "timestamp": timestamp
            }
        }), 201

    except RuntimeError as env_error:
        logging.error(str(env_error))
        return jsonify({"error": str(env_error)}), 500

    except Exception as e:
        logging.exception("Unexpected error occurred")
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e)
        }), 500

# ==============================
# Vercel Entry Point
# ==============================
# Vercel automatically detects `app`