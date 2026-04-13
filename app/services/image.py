"""Image upload and WebP thumbnail conversion. Stores in data/ for persistence."""
import os
import uuid
from PIL import Image

# Store images in data/ directory (persisted on Railway volume)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
PRODUCT_IMG_DIR = os.path.join(BASE_DIR, 'data', 'images', 'products')
THUMBNAIL_SIZE = (400, 400)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file):
    """Save uploaded image, convert to WebP thumbnail. Returns filename."""
    os.makedirs(PRODUCT_IMG_DIR, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.webp"
    filepath = os.path.join(PRODUCT_IMG_DIR, filename)

    try:
        img = Image.open(file.stream)
        img.verify()  # Verify it's actually an image
        file.stream.seek(0)  # Reset after verify
        img = Image.open(file.stream)
    except Exception:
        return None  # Not a valid image

    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
    img.save(filepath, 'WEBP', quality=85, optimize=True)

    return filename


def delete_product_image(filename):
    """Delete a product image file."""
    if filename:
        filepath = os.path.join(PRODUCT_IMG_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)


def get_image_path(filename):
    """Get full path to an image file."""
    return os.path.join(PRODUCT_IMG_DIR, filename) if filename else None
