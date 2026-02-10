# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from med import handle_message, conversation_state

import secrets
from datetime import timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
CORS(app, supports_credentials=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message", "").strip()
        reply = handle_message(user_msg)
        return jsonify({"success": True, "reply": reply})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "reply": "حدث خطأ"}), 500

@app.route("/reset", methods=["POST"])
def reset():
    try:
        conversation_state.reset()
        return jsonify({"success": True, "reply": "تم إعادة تعيين المحادثة."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "Medical Chatbot API"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
