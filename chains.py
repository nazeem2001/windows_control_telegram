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


def generate_audio(text, exaggeration, temperature, cfgw, min_p, top_p, repetition_penalty):
    model = ChatterboxTTS.from_pretrained(DEVICE)

    wav = model.generate(
        text,
        exaggeration=exaggeration,
        temperature=temperature,
        cfg_weight=cfgw,
        min_p=min_p,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
    )

    model = None
    gc.collect()
    torch.cuda.empty_cache()
    ta.save("./downloads/output.wav", wav.cpu(), 24000)
    return ["output.wav", text]


llm = ChatOllama(model="llama3", keep_alive="0")

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{user_name} says: {user_input}")
])

# ollamaChain that can be imported and used in features.py
olamaChain = prompt_template | llm | StrOutputParser()
# using olamaChain to create another chain wihich has chaterbox  tts and outputs wave file
ttsChain = olamaChain | RunnableLambda(lambda x: generate_audio(
    x, exaggeration=1.0, temperature=1.0, cfgw=0.5, min_p=0.05, top_p=1.0, repetition_penalty=1.2))
