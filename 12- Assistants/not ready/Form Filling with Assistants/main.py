from dotenv import load_dotenv
import openai
import os
from openai import AzureOpenAI
import html
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from PIL import Image

import yfinance as yf
from openai import AzureOpenAI
from openai.types import FileObject
from openai.types.beta.threads import Message, TextContentBlock, ImageFileContentBlock, Run
from openai.types.beta.thread import Thread

load_dotenv()
SWEDEN_AZURE_OPENAI_ENDPOINT=os.getenv("SWEDEN_AZURE_OPENAI_ENDPOINT")
SWEDEN_AZURE_OPENAI_API_KEY=os.getenv("SWEDEN_AZURE_OPENAI_API_KEY")
SWEDEN_AZURE_OPENAI_API_VERSION="2024-05-01-preview"
SWEDEN_OPENAI_GPT4_DEPLOYMENT_NAME=os.getenv("SWEDEN_OPENAI_GPT4_DEPLOYMENT_NAME")

def init_llm():
    client = openai.AzureOpenAI(
            azure_endpoint=SWEDEN_AZURE_OPENAI_ENDPOINT,
            api_key=SWEDEN_AZURE_OPENAI_API_KEY,
            api_version=SWEDEN_AZURE_OPENAI_API_VERSION
    )
    return client

# Define the Assistant tools
tools_list = [
    {"type": "code_interpreter"},
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Retrieve the latest closing price of a stock using its ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "The ticker symbol of the stock"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email to a recipient(s).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "The email(s) the email should be sent to."},
                    "content": {"type": "string", "description": "The content of the email."},
                },
                "required": ["to", "content"],
            },
        },
    },
]


# Get the latest stock price by ticker symbol using Yahoo Finance
def get_stock_price(symbol: str) -> float:
    stock = yf.Ticker(symbol)
    return stock.history(period="1d")["Close"].iloc[-1]

# mock mail sending function
def send_email(to: str, content: str) -> None:
    json_payload = {"to": to, "content": html.unescape(content)}
    print("mock email sent to: " + json_payload["to"])



def upload_file(client: AzureOpenAI, path: str) -> FileObject:
    with Path(path).open("rb") as f:
        return client.files.create(file=f, purpose="assistants")


def load_data():    
    DATA_FOLDER = "./Assistants/Form Filling with Assistants/data/"
    arr = os.listdir(DATA_FOLDER)
    assistant_files = []
    for file in arr:
        filePath = DATA_FOLDER + file
        assistant_files.append(upload_file(client, filePath))

    file_ids = [file.id for file in assistant_files]
    return assistant_files, file_ids

def create_assistant(client, file_ids):
    assistant = client.beta.assistants.create(
        name="Travel Assistant",
        instructions="""
        You are a travel support assistant. Please be polite, professional, helpful, and friendly.
        These are the questions that needs to be answered by the user:
        - Inquiry: "Happy to help you with questions about traveling with pets! What do you want to do?"
            ResponseType: "Multiple Choice"
            Options:
            - Option: "Read information about traveling with pets"
            - Option: "Check the pet quota"
            - Option: "Book transportation for my pet"
            - Option: "Cancel my pet's transportation"

        - Inquiry: "Do you want to book transportation in the cabin or in the hold?"
            ResponseType: "Multiple Choice"
            Options:
            - Option: "In the cabin"
                FollowUp: 
                - Inquiry: "Here you can book transportation for a pet in the cabin. Do you want to book the transportation now?"
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "Yes"
                    - Option: "No"
                - Inquiry: "What is the weight of your pet including the carrier? (Cabin transportation requires the pet and carrier's combined weight to be under 8kg)"
                    ResponseType: "Open-ended"
                    Instructions: "Please enter the weight in kilograms."
                - Inquiry: "Does your pet's carrier meet our cabin dimensions criteria? (Max dimensions: 45cm x 35cm x 25cm)"
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "Yes"
                    - Option: "No"
            - Option: "In the hold"
                FollowUp:
                - Inquiry: "Here you can book transportation for a pet in hold. Do you want to book the transportation now?"
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "Yes"
                    - Option: "No"
                - Inquiry: "Your transportation box must comply with the IATA regulations. How many transportation boxes are you using?"
                    ResponseType: "Open-ended"
                    Instructions: "Enter the number of transportation boxes."
                - Inquiry: "Number of pets inside the transportation box."
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "1"
                    - Option: "2 or more"
                - Inquiry: "What is the weight of your pet including the carrier? (Hold transportation requires the pet and carrier's combined weight to be under 75kg)"
                    ResponseType: "Open-ended"
                    Instructions: "Please enter the weight in kilograms."
                - Inquiry: "Please provide the dimensions of the transportation box (Length x Width x Height in cm)."
                    ResponseType: "Open-ended"
                    Instructions: "Enter the dimensions of the box."
                - Inquiry: "Do you want to book transportation for special baggage for outbound, inbound or both outbound and inbound?"
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "Outbound"
                    - Option: "Inbound"
                    - Option: "Both outbound and inbound"
                - Inquiry: "Are the animals familiar with each other?"
                    ResponseType: "Multiple Choice"
                    Options:
                    - Option: "Yes"
                    - Option: "No"
                - Inquiry: "Type of animal(s) you are travelling with."
                    ResponseType: "Open-ended"
                    Instructions: "Enter the type of animal(s)."

        - Inquiry: "I confirm that the pet has all travel documents required by the destination authorities."
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        - Inquiry: "Is there at least 1 week to your flight departure?"
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        - Inquiry: "Do you travel on the same flight with your pet?"
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        - Inquiry: "Please answer the following questions."
            ResponseType: "Open-ended"
            Instructions: "Enter your first and last name."

        - Inquiry: "Please provide your mobile number in international format (e.g. +35850...)."
            ResponseType: "Open-ended"
            Instructions: "Enter your mobile number."

        - Inquiry: "Please provide your email address."
            ResponseType: "Open-ended"
            Instructions: "Enter your email address."

        - Inquiry: "Is your flight destination in the United States?"
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        - Inquiry: "Please provide the departure date."
            ResponseType: "Open-ended"
            Instructions: "Enter the departure date."

        - Inquiry: "Please provide the departure city."
            ResponseType: "Open-ended"
            Instructions: "Enter the departure city."

        - Inquiry: "Please provide the destination city."
            ResponseType: "Open-ended"
            Instructions: "Enter the destination city."

        - Inquiry: "Are you travelling from a destination outside of EU?"
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        - Inquiry: "I confirm that the person travelling with the pet is the owner."
            ResponseType: "Multiple Choice"
            Options:
            - "Yes"
            - "No"

        
        ## Requirements
        1. You are required to ask only one question at the time from the list above and collect answers.
        2. You only ask the same question more than once if you do not get a satisfactory answer. The questions above list either possible answer options or accepts free form answers.
        3. To know what is the next question to ask from the from, you will always analyze the earlier questions and answers in the conversation.
        4. After all the questions in the list above have been answered successfully, you will provide a summary to the user which contains all questions and answers.
        """
        ,
        tools=tools_list,
        model=SWEDEN_OPENAI_GPT4_DEPLOYMENT_NAME,
        tool_resources={"code_interpreter": {"file_ids": file_ids}},
    )

    thread = client.beta.threads.create()
    return assistant, thread

def call_functions(client: AzureOpenAI, thread: Thread, run: Run) -> None:
    print("Function Calling")
    required_actions = run.required_action.submit_tool_outputs.model_dump()
    print(required_actions)
    tool_outputs = []
    import json

    for action in required_actions["tool_calls"]:
        func_name = action["function"]["name"]
        arguments = json.loads(action["function"]["arguments"])

        if func_name == "get_stock_price":
            output = get_stock_price(symbol=arguments["symbol"])
            tool_outputs.append({"tool_call_id": action["id"], "output": str(output)})
        elif func_name == "send_email":
            print("Sending email...")
            email_to = arguments["to"]
            email_content = arguments["content"]
            send_email(email_to, email_content)

            tool_outputs.append({"tool_call_id": action["id"], "output": "Email sent"})
        else:
            raise ValueError(f"Unknown function: {func_name}")

    print("Submitting outputs back to the Assistant...")
    client.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

def format_messages(messages: Iterable[Message]) -> None:
    message_list = []

    # Get all the messages till the last user message
    for message in messages:
        message_list.append(message)
        if message.role == "user":
            break

    # Reverse the messages to show the last user message first
    message_list.reverse()

    # Print the user or Assistant messages or images
    for message in message_list:
        for item in message.content:
            # Determine the content type
            if isinstance(item, TextContentBlock):
                print(f"{message.role}:\n{item.text.value}\n")
            elif isinstance(item, ImageFileContentBlock):
                # Retrieve image from file id
                response_content = client.files.content(item.image_file.file_id)
                data_in_bytes = response_content.read()
                # Convert bytes to image
                readable_buffer = io.BytesIO(data_in_bytes)
                image = Image.open(readable_buffer)
                # Resize image to fit in terminal
                width, height = image.size
                image = image.resize((width // 2, height // 2), Image.LANCZOS)
                # Display image
                image.show()

def process_message(client, assistant, thread, content: str) -> None:
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=content)

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="The current date and time is: " + datetime.now().strftime("%x %X") + ".",
    )

    print("processing...")
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            format_messages(messages)
            break
        if run.status == "failed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            format_messages(messages)
            # Handle failed
            break
        if run.status == "expired":
            # Handle expired
            break
        if run.status == "cancelled":
            # Handle cancelled
            break
        if run.status == "requires_action":
            call_functions(client, thread, run)
        else:
            time.sleep(5)

# Main chat loop
# Type 'exit' to end the chat
try:
    print("Starting LLM...")
    client = init_llm()
    print("Loading info...")
    assistant_files, file_ids = load_data()
    print("Creating assistant...")
    assistant, thread = create_assistant(client, file_ids)
    print("Starting chat...")

    while True:
        user_message = input("user: ").strip()
        if user_message.lower() == 'exit':
            print("Exiting chat.")
            break

        # Create a new message in the conversation thread
        process_message(client, assistant, thread, user_message)
        print() # Add a newline for better readability

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    client.beta.assistants.delete(assistant.id)
    client.beta.threads.delete(thread.id)
    for file in assistant_files:
        client.files.delete(file.id)