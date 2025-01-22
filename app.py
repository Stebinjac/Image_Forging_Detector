from flask import Flask, render_template, request, url_for
import cv2
import hashlib
import os
import numpy as np
import json

with open('vercel.json', 'r') as file:
    data = json.load(file)
    print("Valid JSON!")


# Initialize Flask app
app = Flask(__name__)

# Configure upload and output folders
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'static'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Function to calculate MD5 hash of an image
def calculate_md5(image_path):
    """Calculate the MD5 hash of an image."""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return hashlib.md5(image_data).hexdigest()

# Function to highlight differences between two images
def highlight_differences(img1_path, img2_path, output_path):
    """Highlight differences between two images."""
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    # Ensure both images have the same dimensions
    img1 = cv2.resize(img1, (500, 500))
    img2 = cv2.resize(img2, (500, 500))

    # Compute absolute difference
    diff = cv2.absdiff(img1, img2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Apply threshold to highlight differences
    _, threshold = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    # Save the result
    cv2.imwrite(output_path, threshold)

# Define route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle uploaded files
        original_file = request.files['original']
        modified_file = request.files['modified']
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_file.filename)
        modified_path = os.path.join(app.config['UPLOAD_FOLDER'], modified_file.filename)
        original_file.save(original_path)
        modified_file.save(modified_path)

        # Path for the output difference image
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 'difference.jpg')

        # Calculate MD5 hashes
        original_hash = calculate_md5(original_path)
        modified_hash = calculate_md5(modified_path)

        # Determine if forgery is detected
        if original_hash == modified_hash:
            result = "No forgery detected."
            show_image = False
        else:
            result = "Forgery detected! Highlighting differences..."
            highlight_differences(original_path, modified_path, output_path)
            show_image = True

        # Render result with the output image
        return render_template('index.html', 
                               result=result, 
                               show_image=show_image, 
                               output_image=url_for('static', filename='difference.jpg'))

    # Render the initial form
    return render_template('index.html', result=None, show_image=False)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
