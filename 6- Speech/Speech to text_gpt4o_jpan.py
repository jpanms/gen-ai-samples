import os
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY=os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_API_VERSION=os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_GPT4o_DEPLOYMENT=os.getenv("AZURE_OPENAI_GPT4o_DEPLOYMENT")

client = AzureOpenAI(
  azure_endpoint = AZURE_OPENAI_ENDPOINT, 
  api_key=AZURE_OPENAI_KEY,  
  api_version=AZURE_OPENAI_API_VERSION
)

SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")
engine_name = "test"

print(f"Model: {AZURE_OPENAI_GPT4o_DEPLOYMENT}; API Version:{AZURE_OPENAI_API_VERSION}")
print("Azure OpenAI model is ready to use!")
print(f"Speech Service in {SPEECH_REGION} is ready to use!")

speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
# Set up Azure Text-to-Speech language 
speech_config.speech_synthesis_language = "en-US"
# Set up Azure Speech-to-Text language recognition
speech_config.speech_recognition_language = "en-US"
# Use an absolute path for the log file
log_file_path = os.path.abspath("./log/log_gpt4o.txt")
speech_config.set_property(speechsdk.PropertyId.Speech_LogFilename, log_file_path)

# Set up the voice configuration
speech_config.speech_synthesis_voice_name = "en-US-JennyMultilingualNeural"
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

# Define the speech-to-text function
def speech_to_text():
    # Set up the audio configuration
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    # Create a speech recognizer and start the recognition
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    print("How can I help you today?")

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "Sorry, I didn't catch that."
    elif result.reason == speechsdk.ResultReason.Canceled:
        return "Recognition canceled."

# Define the text-to-speech function
def text_to_speech(text):
    try:
        result = speech_synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Text-to-speech conversion successful.")
            return True
        else:
            print(f"Error synthesizing audio: {result}")
            return False
    except Exception as ex:
        print(f"Error synthesizing audio: {ex}")
        return False

def evaluate_sentiment(text):
    system_message = """
    You are an AI assistant that helps recognize the sentiment in a given text.
    1. Evaluate the given text and provide the category of the sentiment as either positive, negative, or neutral.
    2. Do not provide any additional examples to the output, just the category.
    """

    response = client.chat.completions.create(
        model=AZURE_OPENAI_GPT4o_DEPLOYMENT,
        messages = [
            {"role":"system","content":system_message},
            {"role":"user","content":text}
            ],
        temperature=0   
    )
    return response.choices[0].message.content

def translate(text, target_language):
    system_message = """You are a helpful assistant that translates text into """ + target_language + """.
    Answer in a clear and concise manner only translating the text.
    Text:
    """

    response = client.chat.completions.create(
        model=AZURE_OPENAI_GPT4o_DEPLOYMENT,
        messages = [
            {"role":"system","content":system_message},
            {"role":"user","content":text}
            ],
        temperature=0   
    )
    return response.choices[0].message.content


# Main program loop
max_tries = 3
tries = 0

while tries < max_tries:
    # Get input from user using speech-to-text
    user_input = speech_to_text()
    print(f"You said: {user_input}")

    # Evaluate the sentiment using OpenAI
    response = evaluate_sentiment(user_input)
    print(f"AI says: {response}")

    # Translate the text to Chinese using OpenAI
    translated_text = translate(user_input, "Chinese")
    print(f"AI translated to Chinese: {response}")
    # Convert the response to speech using text-to-speech
    text_to_speech(translated_text)

    tries += 1
    print(f"Attempt {tries} of {max_tries}")
    
print("Finished after 3 tries.")