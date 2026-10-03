import asyncio
import os

from dotenv import load_dotenv, main
from telegram.ext import ApplicationBuilder

# # IMPORTANT: If you are on Windows, you must point to the tesseract executable
# pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

# def perform_ocr(image_path):
#     try:
#         # Open the image file
#         img = Image.open(image_path)

#         # Use pytesseract to convert the image to string
#         text = pytesseract.image_to_string(img)

#         return text
#     except Exception as e:
#         return f"An error occurred: {e}"

# # Usage
# image_file = "WhatsApp Image 2025-12-29 at 8.44.18 PM.jpeg" # Replace with your image path
# extracted_text = perform_ocr(image_file)


# print("--- Extracted Text ---")
# print(extracted_text)
# async def main():
#     # Load environment variables
#     load_dotenv()
#     api_key = os.getenv("API_KEY")

#     # Initialize the bot application
#     app = (
#         ApplicationBuilder().token(api_key).connect_timeout(30).read_timeout(30).build()
#     )

#     # Use 'async with' to properly initialize and close the bot session
#     async with app:
#         try:
#             # Note: 1235 is likely an invalid chat ID; ensure you use a real one
#             data = await app.bot.get_chat(chat_id=1144964888)
#             print(data.first_name)
#         except Exception as e:
#             print(f"Error fetching chat: {e}")


# if __name__ == "__main__":
#     # This is the entry point to run async code from a synchronous script
#     asyncio.run(main())

# chatterbox intitialization
import torch
from chatterbox.tts import ChatterboxTTS
import torchaudio as ta
import gc

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {DEVICE}")
def split_text_into_chunks(text, max_length=300):
    """Split text into chunks of words, respecting word boundaries."""
    if len(text) <= max_length:
        return [text]

    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        # Check if adding this word would exceed the limit
        word_length = len(word) + (1 if current_chunk else 0)  # +1 for space
        if current_length + word_length > max_length and current_chunk:
            # Save current chunk and start a new one
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += word_length

    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def generate_audio(
    text, exaggeration, temperature, cfgw, min_p, top_p, repetition_penalty,n
):
    model = ChatterboxTTS.from_pretrained(DEVICE)
    chunks = []
    if len(text) > 300:
        chunks = split_text_into_chunks(text, 300)
    else:
        chunks = [text]
    file_names = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        wav = model.generate(
            chunk,
            exaggeration=exaggeration,
            temperature=temperature,
            cfg_weight=cfgw,
            min_p=min_p,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
        )
        ta.save(f"./downloads/output({n})({i}).wav", wav.cpu(), 24000)
        file_names.append(f"output({i}).wav")

    model = None
    gc.collect()
    torch.cuda.empty_cache()
    return file_names, 
if __name__ == "__main__":
    
    exaggeration = 0.5
    temperature = 0.5
    cfgw = 1.0
    min_p = 0.0
    top_p = 1.0
    repetition_penalty = 1.0
    num=0
    while True:
        text = input("Enter text to convert to speech (or 'exit' to quit): ")
        if text.lower() == "exit":
            break
        file_names = generate_audio(
            text, exaggeration, temperature, cfgw, min_p, top_p, repetition_penalty, num
        )
        print(f"Generated audio files: {file_names}")
        num += 1