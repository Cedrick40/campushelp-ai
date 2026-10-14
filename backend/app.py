from flask import Flask, jsonify, request

app = Flask(__name__)

KNOWLEDGE = {
    "library hours": "The main library is open from 8:00 AM to 10:00 PM on weekdays and from 9:00 AM to 6:00 PM on weekends.",
    "admissions": "The admissions office is open Monday to Friday from 9:00 AM to 5:00 PM, and application deadline dates are March 1 for fall and November 1 for spring.",
    "student support": "The student support center provides academic advising, mental health counseling, and emergency financial assistance during weekday office hours.",
    "default": "I can answer questions about library hours, admissions, or student support. Try asking one of those topics."
}


def find_answer(question: str) -> str:
    q = question.lower()
    for key, answer in KNOWLEDGE.items():
        if key in q:
            return answer
    return KNOWLEDGE["default"]


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400

    return jsonify({
        "question": question,
        "answer": find_answer(question),
        "sources": [
            {"title": "Campus Knowledge", "snippet": "University information guide"}
        ]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
