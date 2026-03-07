"""
voice.ai TTS Example - HTTP Streaming Speech

This atomic example demonstrates the `/api/v1/tts/speech/stream` endpoint.
Use it when you want HTTP chunked transfer so audio arrives as it is generated.

What this file shows:
- how to authenticate with a bearer token
- how to set every supported public request field at the top of the file
- how to stream the response directly to disk

Usage:
    python tts_generate_speech_stream.py
"""

from pathlib import Path

import requests

# Configuration
API_BASE_URL = "https://dev.voice.ai"
# API_BASE_URL = "http://localhost:8000"  # Local/self-hosted override
API_KEY = "YOUR_API_KEY_HERE"

# Supported audio_format values:
# - Basic: "mp3", "wav", "pcm"
# - Telephony: "alaw_8000", "ulaw_8000"
# - MP3 variants: "mp3_22050_32", "mp3_24000_48", "mp3_44100_32", "mp3_44100_64",
#   "mp3_44100_96", "mp3_44100_128", "mp3_44100_192"
# - Opus variants: "opus_48000_32", "opus_48000_64", "opus_48000_96",
#   "opus_48000_128", "opus_48000_192"
# - PCM variants: "pcm_8000", "pcm_16000", "pcm_22050", "pcm_24000",
#   "pcm_32000", "pcm_44100", "pcm_48000"
# - WAV variants: "wav_16000", "wav_22050", "wav_24000"
TEXT = "Hello from the voice.ai HTTP streaming speech example."
VOICE_ID = None  # Optional: set a voice ID to use a specific cloned voice
AUDIO_FORMAT = "mp3"
TEMPERATURE = 1.0
TOP_P = 0.8

# Supported model values:
# - "voiceai-tts-v1-latest"
# - "voiceai-tts-v1-2026-02-10"
# - "voiceai-tts-multilingual-v1-latest"
# - "voiceai-tts-multilingual-v1-2026-02-10"
MODEL = None  # Leave as None to let the server auto-select from LANGUAGE

# Supported language values:
# - "en", "ca", "sv", "es", "fr", "de", "it", "pt", "pl", "ru", "nl"
LANGUAGE = "en"

OUTPUT_FILE = "generated_speech_stream.mp3"  # Update the extension if you change AUDIO_FORMAT

headers = {
    "Authorization": f"Bearer {API_KEY}",
}


def build_payload() -> dict:
    """Build the request body from the top-level example constants."""
    payload = {
        "text": TEXT,
        "audio_format": AUDIO_FORMAT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "language": LANGUAGE,
    }
    if VOICE_ID is not None:
        payload["voice_id"] = VOICE_ID
    if MODEL is not None:
        payload["model"] = MODEL
    return payload


def main():
    print("=" * 60)
    print("voice.ai TTS Example: HTTP Streaming Speech")
    print("=" * 60)

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tts/speech/stream",
            headers=headers,
            json=build_payload(),
            stream=True,
        )
        response.raise_for_status()

        output_path = Path(OUTPUT_FILE)
        with output_path.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_handle.write(chunk)

        print(f"✓ Wrote streamed audio to {output_path} ({output_path.stat().st_size} bytes)")

    except requests.exceptions.HTTPError as exc:
        print(f"✗ HTTP Error: {exc}")
        if exc.response is not None:
            print(f"  Response: {exc.response.text}")
    except Exception as exc:
        print(f"✗ Error: {exc}")


if __name__ == "__main__":
    main()
