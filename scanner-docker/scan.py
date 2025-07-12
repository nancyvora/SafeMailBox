from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/scan", methods=["POST"])
def scan():
    file = request.files['file']
    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)

    # YARA scan
    try:
        result = subprocess.run(["yara", "-r", "/app/rules.yar", filepath], capture_output=True, text=True, timeout=30)
        if result.stdout:
            return jsonify({"status": "infected", "output": result.stdout})
        else:
            return jsonify({"status": "clean"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(filepath)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
