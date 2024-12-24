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
    {
        "type": "function",
        "function": {
            "name": "getplanprice",
            "parameters": {
                "type": "object",
                "properties": {
                "plan": {
                    "type": "string",
                    "Description": "Individual or Family"
                },
                "people": {
                    "type": "integer",
                    "description": "The number of people on the plan"
                },
                "ages": {
                    "type": "string",
                    "description": "Commma separates list of the ages of all plan participants"
                }
                },
                "required": [
                "plan",
                "people",
                "ages"
                ]
            },
            "description": "Needs the city/state, the type of plan, the number of peole on the plan and the ages of the people"
        }
    }
]


# mock mail sending function
def send_email(to: str, content: str) -> None:
    json_payload = {"to": to, "content": html.unescape(content)}
    print("mock email sent to: " + json_payload["to"])

def get_plan_price(plan: str, people: int, ages: str) -> str:
    print(f"Plan: {plan}, People: {people}, Ages: {ages}")
    return "Plan price: $100"

def upload_file(client: AzureOpenAI, path: str) -> FileObject:
    with Path(path).open("rb") as f:
        return client.files.create(file=f, purpose="assistants")


def load_data():    
    DATA_FOLDER = "./Assistants/not ready/Form Filling with Assistants/data/"
    arr = os.listdir(DATA_FOLDER)
    assistant_files = []
    for file in arr:
        filePath = DATA_FOLDER + file
        assistant_files.append(upload_file(client, filePath))

    file_ids = [file.id for file in assistant_files]
    return assistant_files, file_ids

def create_assistant(client, file_ids):
    assistant = client.beta.assistants.create(
        name="Assistant",
        instructions="""
        You are Billy, a helpful chatbot assistant who asks the user questions and stores the results for further use,
        Begin by introducing yourself, explaining that you need some info and then ask for the following information from the user one question for each piece of info:

        name
        hobbies
        location
        age
        email
        Be subtle how you ask about this information. Ask me one question at a time.
        Begin the conversation:        
        """
        ,
        tools=[],
        model=SWEDEN_OPENAI_GPT4_DEPLOYMENT_NAME,
        tool_resources={},
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

        if func_name == "getplanprice":
            print("Getting plan price...")
            plan = arguments["plan"]
            people = arguments["people"]
            ages = arguments["ages"]
            plan_price = get_plan_price(plan, people, ages)
            tool_outputs.append({"tool_call_id": action["id"], "output": plan_price})
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