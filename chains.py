from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
import random
import numpy as np
import torch
from chatterbox.tts import ChatterboxTTS
import torchaudio as ta
import gc

# chatterbox intitialization
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
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += word_length

    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def generate_audio(text, exaggeration, temperature, cfgw, min_p, top_p, repetition_penalty):
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
        ta.save(f"./downloads/output({i}).wav", wav.cpu(), 24000)
        file_names.append(f"output({i}).wav")

    model = None
    gc.collect()
    torch.cuda.empty_cache()
    return file_names, text


llm = ChatOllama(model="llama3.1", keep_alive="0")

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{user_name} says: {user_input}")
])

# ollamaChain that can be imported and used in features.py
olamaChain = prompt_template | llm | StrOutputParser()
# using olamaChain to create another chain wihich has chaterbox  tts and outputs wave file
ttsChain = olamaChain | RunnableLambda(lambda x: generate_audio(
    x, exaggeration=.5, temperature=1.0, cfgw=0.5, min_p=0.05, top_p=1.0, repetition_penalty=1.2))
