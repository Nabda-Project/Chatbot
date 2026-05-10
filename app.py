import secrets
# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from med import handle_message, reset_session

app = Flask(__name__)

CORS(app, supports_credentials=True)

# ================= SESSION =================
def _get_or_create_session():
    sid = request.cookies.get("session_id")
    if sid:
        return sid, False
    return secrets.token_hex(16), True


# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        print("Incoming request")

        data = request.get_json(force=True, silent=True) or {}
        payload = data.get("message", None)

        if payload == "":
            payload = None

        print("Payload:", payload)

        session_id, is_new = _get_or_create_session()

        result = handle_message(session_id, payload)

        response = jsonify({
            "success": True,
            "done": result["done"],
            "question": result["question"],
            "reply": result["reply"],
        })

        if is_new:            response.set_cookie(
                "session_id",
                session_id,
                samesite="Lax",
                secure=False
            )

        return response

    except Exception as exc:
        print("ERROR:", exc)
        import traceback
        traceback.print_exc()  

        return jsonify({
            "success": False,
            "error": str(exc),
            "reply": "حدث خطأ في الخادم",
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
    
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.timeout = 300  
    app.run(debug=True, threaded=True)  