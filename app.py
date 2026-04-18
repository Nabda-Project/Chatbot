import secrets
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from med import handle_message, reset_session

app = Flask(__name__)
CORS(app, supports_credentials=True)


def _get_or_create_session():
    """Return (session_id, is_new)."""
    sid = request.cookies.get("session_id")
    if sid:
        return sid, False
    return secrets.token_hex(16), True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True, silent=True) or {}

        # "message" can be str (number/text/choice) or list[str] (multi_choice)
        payload = data.get("message", None)
        if payload == "":
            payload = None

        session_id, is_new = _get_or_create_session()
        result = handle_message(session_id, payload)

        response = jsonify({
            "success":  True,
            "done":     result["done"],
            "question": result["question"],
            "reply":    result["reply"],
        })

        if is_new:
            response.set_cookie("session_id", session_id, samesite="Lax")

        return response

    except Exception as exc:
        return jsonify({
            "success": False,
            "error":   str(exc),
            "reply":   "حدث خطأ في الخادم – الرجاء المحاولة مرة أخرى.",
        }), 500


@app.route("/reset", methods=["POST"])
def reset():
    session_id = request.cookies.get("session_id")
    if session_id:
        reset_session(session_id)
    response = jsonify({"success": True})
    response.set_cookie("session_id", "", expires=0)
    return response


if __name__ == "__main__":
    app.run(debug=True)
