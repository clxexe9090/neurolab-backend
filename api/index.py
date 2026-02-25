from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"status": "Backend connected 🚀"})

# 👇 ESTA LÍNEA ES LA CORRECTA PARA VERCEL
app = app