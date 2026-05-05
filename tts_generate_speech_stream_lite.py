"""
voice.ai TTS Example - HTTP Streaming Speech with Lite

This atomic example demonstrates Lite inference through `/api/v1/tts/speech/stream`.
Lite is a hosted English-only TTS model, so this sample pins both:

- model: "voiceai-tts-lite-v1-latest"
- language: "en"

Usage:
    python tts_generate_speech_stream_lite.py
"""

from pathlib import Path

import requests

# Configuration
API_BASE_URL = "https://dev.voice.ai"
# API_BASE_URL = "http://localhost:8000"  # Local/self-hosted override
API_KEY = "YOUR_API_KEY_HERE"

TEXT = "Hello from the voice.ai Lite HTTP streaming TTS inference example."
VOICE_ID = None  # Optional: set a voice ID to use a specific cloned voice
AUDIO_FORMAT = "mp3"
TEMPERATURE = 1.0
TOP_P = 0.8

# Lite model values:
# - "voiceai-tts-lite-v1-latest"
# - "voiceai-tts-lite-v1-2026-04-15"
MODEL = "voiceai-tts-lite-v1-latest"
LANGUAGE = "en"  # Lite is English-only

OUTPUT_FILE = "generated_speech_stream_lite.mp3"

headers = {
    "Authorization": f"Bearer {API_KEY}",
}


def build_payload() -> dict:
    """Build a streaming TTS request pinned to Lite."""
    payload = {
        "text": TEXT,
        "audio_format": AUDIO_FORMAT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "model": MODEL,
        "language": LANGUAGE,
    }
    if VOICE_ID is not None:
        payload["voice_id"] = VOICE_ID
    return payload


def main():
    print("=" * 60)
    print("voice.ai TTS Example: HTTP Streaming Speech with Lite")
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

        print(f"Wrote streamed Lite audio to {output_path} ({output_path.stat().st_size} bytes)")

    except requests.exceptions.HTTPError as exc:
        print(f"HTTP Error: {exc}")
        if exc.response is not None:
            print(f"  Response: {exc.response.text}")
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
