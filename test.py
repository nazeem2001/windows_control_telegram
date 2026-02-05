import pytesseract
from PIL import Image

# IMPORTANT: If you are on Windows, you must point to the tesseract executable
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

def perform_ocr(image_path):
    try:
        # Open the image file
        img = Image.open(image_path)

        # Use pytesseract to convert the image to string
        text = pytesseract.image_to_string(img)

        return text
    except Exception as e:
        return f"An error occurred: {e}"

# Usage
image_file = "WhatsApp Image 2025-12-29 at 8.44.18 PM.jpeg" # Replace with your image path
extracted_text = perform_ocr(image_file)

print("--- Extracted Text ---")
print(extracted_text)