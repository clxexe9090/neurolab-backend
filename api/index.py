from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
import time

app = Flask(__name__)
CORS(app)

# ==============================
# Supabase Client
# ==============================
def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise Exception("Missing Supabase environment variables")

    return create_client(url, key)

# ==============================
# Health Check
# ==============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "NeuroLab Backend Running 🚀"})

# ==============================
# Receive IoT Data
# ==============================
@app.route("/v1/data", methods=["POST"])
def receive_data():
    try:
        supabase = get_supabase()
        payload = request.get_json()

        if not payload:
            return jsonify({"error": "No JSON received"}), 400

        required_fields = ["device_id", "gsr", "sound", "accel"]

        for field in required_fields:
            if field not in payload:
                return jsonify({"error": f"Missing field: {field}"}), 400

        device_id = payload["device_id"]
        gsr = float(payload["gsr"])
        sound = float(payload["sound"])
        accel = float(payload["accel"])
        timestamp = int(time.time())

        gsr_norm = min(max(gsr, 0), 1)
        sound_norm = min(max(sound, 0), 1)
        accel_norm = min(max(accel, 0), 1)

        stress_index = (
            0.4 * gsr_norm +
            0.3 * sound_norm +
            0.3 * accel_norm
        )

        alert = None
        if stress_index > 0.7:
            alert = "Possible overstimulation detected"

        supabase.table("sensor_data").insert({
            "device_id": device_id,
            "gsr": gsr_norm,
            "sound": sound_norm,
            "accel": accel_norm,
            "stress_index": stress_index,
            "timestamp": timestamp
        }).execute()

        return jsonify({
            "status": "Data stored",
            "stress_index": stress_index,
            "alert": alert
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


handler = app