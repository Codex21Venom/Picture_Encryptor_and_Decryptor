from flask import Flask, render_template, request, redirect, send_file, flash, session, url_for, make_response
from PIL import Image
import io
import os
import random
import uuid
import zipfile

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = "uploads"
KEY_FOLDER = "keys"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(KEY_FOLDER, exist_ok=True)


def swap_pixels(img):
    pixels = list(img.getdata())
    total_pixels = len(pixels)
    shuffled_indices = list(range(total_pixels))
    random.shuffle(shuffled_indices)
    shuffled_pixels = [pixels[i] for i in shuffled_indices]
    img.putdata(shuffled_pixels)
    return img, shuffled_indices


def reverse_swap(img, indices):
    shuffled_pixels = list(img.getdata())
    original_pixels = [None] * len(shuffled_pixels)
    for i, index in enumerate(indices):
        original_pixels[index] = shuffled_pixels[i]
    img.putdata(original_pixels)
    return img


def apply_math_op(img, key=20):
    pixels = list(img.getdata())
    new_pixels = [((r + key) % 256, (g + key) % 256, (b + key) % 256) for r, g, b in pixels]
    img.putdata(new_pixels)
    return img


def reverse_math_op(img, key=20):
    pixels = list(img.getdata())
    new_pixels = [((r - key) % 256, (g - key) % 256, (b - key) % 256) for r, g, b in pixels]
    img.putdata(new_pixels)
    return img


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/encrypt", methods=["POST"])
def encrypt():
    image = request.files['image']
    if not image:
        flash("No image selected.")
        return redirect("/")

    img = Image.open(image).convert("RGB")
    filename = image.filename
    img, indices = swap_pixels(img)
    img = apply_math_op(img, key=20)

    # Unique name
    unique_id = str(uuid.uuid4())
    img_filename = f"encrypted_{unique_id}.png"
    key_filename = f"{unique_id}.key"

    # Save image
    img_path = os.path.join(UPLOAD_FOLDER, img_filename)
    img.save(img_path, format="PNG")

    # Save key
    key_path = os.path.join(KEY_FOLDER, key_filename)
    with open(key_path, "w") as f:
        f.write(",".join(map(str, indices)))

    # Create ZIP containing both
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        zipf.write(img_path, arcname=img_filename)
        zipf.write(key_path, arcname=key_filename)
    zip_buffer.seek(0)

    response = make_response(send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='encrypted_package.zip'))
    return response


@app.route("/decrypt", methods=["POST"])
def decrypt():
    image = request.files['image']
    key_file = request.files['key']

    if not image or not key_file:
        flash("Image or key file missing.")
        return redirect("/")

    img = Image.open(image).convert("RGB")
    indices = list(map(int, key_file.read().decode().split(",")))

    img = reverse_math_op(img, key=20)
    img = reverse_swap(img, indices)

    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return send_file(output, mimetype="image/png", as_attachment=True, download_name="decrypted.png")


if __name__ == "__main__":
    app.run(debug=True)
