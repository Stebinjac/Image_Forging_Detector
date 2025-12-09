# backend/main.py
import os
import hashlib
import uuid
from flask import Flask, render_template, request, url_for, redirect, flash
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from flask_cors import CORS

# Configuration
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "static"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get("FLASK_SECRET", "replace_this_in_prod")

# If frontend runs on a different domain, enable CORS and set origins appropriately
# For production, restrict origins to your frontend domain.
CORS(app, origins="*")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_md5(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def highlight_differences(img1_path, img2_path, output_path):
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)
    if img1 is None or img2 is None:
        raise ValueError("One of the images could not be read")

    # Resize to the smaller of the two to preserve some detail (preserve aspect ratio optionally)
    h, w = 500, 500
    img1 = cv2.resize(img1, (w, h))
    img2 = cv2.resize(img2, (w, h))

    diff = cv2.absdiff(img1, img2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    # Optional: dilate to make regions more visible
    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.dilate(thresh, kernel, iterations=1)
    # Save result as RGB/gray image
    cv2.imwrite(output_path, thresh)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None, show_image=False)

@app.route("/", methods=["POST"])
def upload_and_compare():
    # Simple validation
    if "original" not in request.files or "modified" not in request.files:
        flash("Please upload both files")
        return redirect(url_for("index"))

    orig_file = request.files["original"]
    mod_file = request.files["modified"]

    if orig_file.filename == "" or mod_file.filename == "":
        flash("Empty filename submitted")
        return redirect(url_for("index"))

    if not (allowed_file(orig_file.filename) and allowed_file(mod_file.filename)):
        flash("Allowed file types: png, jpg, jpeg")
        return redirect(url_for("index"))

    # Save files with secure, unique names
    orig_name = secure_filename(orig_file.filename)
    mod_name = secure_filename(mod_file.filename)
    orig_unique = f"{uuid.uuid4().hex}_{orig_name}"
    mod_unique = f"{uuid.uuid4().hex}_{mod_name}"
    orig_path = os.path.join(app.config["UPLOAD_FOLDER"], orig_unique)
    mod_path = os.path.join(app.config["UPLOAD_FOLDER"], mod_unique)
    orig_file.save(orig_path)
    mod_file.save(mod_path)

    # compute hashes
    original_hash = calculate_md5(orig_path)
    modified_hash = calculate_md5(mod_path)

    output_filename = f"difference_{uuid.uuid4().hex}.png"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    try:
        if original_hash == modified_hash:
            result = "No forgery detected."
            show_image = False
        else:
            result = "Forgery detected! Highlighting differences..."
            highlight_differences(orig_path, mod_path, output_path)
            show_image = True

    except Exception as e:
        # Log error server-side (Render logs)
        app.logger.exception("Error while processing images")
        flash("Server error while processing images.")
        return redirect(url_for("index"))

    # Optionally: clean up uploads (not removing output)
    # os.remove(orig_path); os.remove(mod_path)

    return render_template(
        "index.html",
        result=result,
        show_image=show_image,
        output_image=url_for("static", filename=output_filename),
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
