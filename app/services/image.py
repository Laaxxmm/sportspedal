"""Image upload and WebP thumbnail conversion."""
import os
import uuid
from PIL import Image

PRODUCT_IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img', 'products')
THUMBNAIL_SIZE = (400, 400)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file):
    """Save uploaded image, convert to WebP thumbnail. Returns filename."""
    os.makedirs(PRODUCT_IMG_DIR, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.webp"
    filepath = os.path.join(PRODUCT_IMG_DIR, filename)

    img = Image.open(file.stream)

    # Convert RGBA to RGB if needed (WebP supports RGBA but keeping it simple)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Resize maintaining aspect ratio
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    # Save as WebP
    img.save(filepath, 'WEBP', quality=85, optimize=True)

    return filename


def delete_product_image(filename):
    """Delete a product image file."""
    if filename:
        filepath = os.path.join(PRODUCT_IMG_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
