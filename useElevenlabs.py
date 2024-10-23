from dotenv import load_dotenv
import requests
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO
import os

load_dotenv() # Carrega o plug-in do dotenv

url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM/stream"

querystring = {"optimize_streaming_latency": "3"}

payload = {
    "text": "Olá, bom dia, tudo bem, como posso te ajudar hoje?",
    "model_id": "eleven_multilingual_v1"
}

headers = {
    "xi-api-key": os.getenv('ELEVENLABS_API_KEY'),
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers, params=querystring)

# Verifica se a solicitação foi bem-sucedida
if response.status_code == 200:
    # Carrega o áudio retornado pela API
    audio_data = response.content
    # Reproduz o áudio
    sound = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
    play(sound)
else:
    print("Erro ao solicitar o áudio:", response.text)
