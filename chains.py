from langchain_core.prompts import ChatPromptTemplate
from langchain.messages import SystemMessage
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
import torch
from chatterbox.tts import ChatterboxTTS
import torchaudio as ta
import gc

from tool_config import build_tools

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
    chat_history, exaggeration, temperature, cfgw, min_p, top_p, repetition_penalty
):
    model = ChatterboxTTS.from_pretrained(DEVICE)
    chunks = []
    text = chat_history["output"] if chat_history else ""
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
    return file_names, chat_history


llm = ChatOllama(model="gemma4", keep_alive="0", reasoning=True)

agent_system_prompt = SystemMessage(
    content="""You are a helpful assistant.you can use tools to interact with the system. Use them wisely to help the user. 
    Only use the tools when necessary and make sure to provide the correct input to the tools. 
    don't give an empty response. 
    ## If you are unsure about something, ask the user for clarification.
    ##Important: dont use'*' for list items in your response as it may interfere with markdown parsing. 
    ##Important: If you are using the video tool, make sure to ask the user for confirmation before starting the video stream.
    ##Important: If you are using the screen sharing tool, make sure to ask the user for confirmation before starting the screen sharing.
    ##Important: use the system status to decide whether to use the video or screen sharing tool.
    ##Important: If the user asks for the system status, provide the current status of the system including remote desktop, live video, screen sharing, and NLP state.for opening applications.
    use the 'execute_command_terminal' with the start command for non-blocking behavior.
    ##Important: If you want to open an application, use the 'execute_command_terminal' tool with the start command for non-blocking behavior. For example, to open notepad, don't use 'notepad' as the command, use 'start notepad' as the command.
    #tool List:
    - video: Start or stop webcam streaming. Input should be empty.,
    - types: Type text on the system keyboard. Input should be the text to type.,
    - send: Send a file to the user by path. Input should be the path of the file to send.,
    - screenshot: Take a screenshot of the current screen. Input should be empty.,
    - get_date_time: Get the current date and time. Input should be empty.,
    - screen_share: Start or stop screen sharing. Input should be empty.,
    - remove_user: Remove a user from the system. Input should be the username of the user to remove.,
    - get_authorized_users: Get a list of authorized users. Input should be empty.,
    - toggle_rdp_tunnel: Toggle the RDP tunnel. Input should be empty.,
    - execute_command_terminal: Execute a command in the terminal. Input should be the command to execute.,
    - schedule_reminder: **Important**:don't call this tool if you get a message starts with "Remnder Message:" this means its a reminder. Schedule a reminder at a future time using natural language. Input should be the reminder text and optional schedule details. Example: "send me the latest news every day at 9am." the input to this tool will be something like "Remnder Message: send me the latest news at 9:00am everyday." the time format should be like HH:MM(am/pm) and the recurrence pattern can be daily, every day, everyday, or every monday/tuesday/wednesday/thursday/friday/saturday/sunday. if no time is provided, the reminder will be set for 1 minute from now. if no recurrence pattern is provided, the reminder will be set as one-time.
    - clear_history: Clear the chat history. Input should be empty.,
    - DuckDuckGoSearchRun: Perform a search using DuckDuckGo. Input should be the search query."""
)
prompt_template = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="history"),
        ("system", "{system_status}"),
        ("user", "{user_name} says: {user_input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)


response_formatter_chain = (
    ChatPromptTemplate.from_messages(
        [
            (
                "user",
                'response: {response} \n format the response in markdown format##Important## remove "*" for bullet points and use "-" instead. if there is code block use triple backticks for code blocks. ##Important## only respond with the markdown text without any additional explanation. ##Imoprtant## if the response contains a list, make sure to format it properly in markdown format. ##Important## if the response contains a code block, make sure to format it properly in markdown format.',
            ),
        ]
    )
    | llm
    | StrOutputParser()
)


def create_agent_text(features, tool_ctx):
    # tools will be injected later
    tools = build_tools(features, tool_ctx)

    agent = create_agent(
        model=llm,
        tools=tools,
    )
    return (
        prompt_template
        | agent
        | RunnableLambda(lambda x: {"response": x, "output": x["messages"][-1].content})
    )


def create_agent_tts(features, tool_ctx):
    # tools will be injected later
    agent = create_agent_text(features, tool_ctx)
    return agent | RunnableLambda(
        lambda x: generate_audio(
            x,
            exaggeration=0.5,
            temperature=1.0,
            cfgw=0.5,
            min_p=0.05,
            top_p=1.0,
            repetition_penalty=1.2,
        )
    )
