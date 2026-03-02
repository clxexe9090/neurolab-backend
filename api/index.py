from flask import Flask, request
from supabase import create_client
import os
import time

app = Flask(__name__)

# Supabase
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

@app.route("/")
def root():
    return {"status": "running"}

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/v1/data", methods=["POST"])
def receive_data():
    data = request.get_json()

    result = supabase.table("sensor_data").insert({
        "device_id": data["device_id"],
        "gsr": data["gsr"],
        "sound": data["sound"],
        "accel": data["accel"],
        "timestamp": int(time.time())
    }).execute()

    return {"stored": True}

# 🔴 IMPORTANTE EN VERCEL 2026
handler = app