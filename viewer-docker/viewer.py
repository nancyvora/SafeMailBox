from flask import Flask, request, render_template, send_file, abort
import os
import tempfile
import magic

app = Flask(__name__)

@app.route('/render', methods=['POST'])
def render_file():
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    temp_path = tempfile.NamedTemporaryFile(delete=False).name
    file.save(temp_path)

    mime_type = magic.from_file(temp_path, mime=True)

    if mime_type.startswith("image/") or mime_type == "application/pdf":
        return send_file(temp_path, mimetype=mime_type)
    elif mime_type.startswith("text/"):
        with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return render_template("viewer.html", content=content)
    elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       "application/msword",
                       "application/vnd.ms-excel",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       "application/vnd.ms-powerpoint",
                       "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        converted_path = temp_path + ".pdf"
        os.system(f"libreoffice --headless --convert-to pdf {temp_path} --outdir /tmp")
        if os.path.exists(converted_path):
            return send_file(converted_path, mimetype="application/pdf")
        else:
            return "Failed to convert document", 500
    else:
        return f"Unsupported file type: {mime_type}", 415


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)