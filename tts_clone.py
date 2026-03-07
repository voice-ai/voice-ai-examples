"""
Voice.AI TTS Example - Clone Voice

This atomic example demonstrates the `/api/v1/tts/clone-voice` endpoint.
Use it when you want to create a new cloned voice from reference audio.

What this file shows:
- how to authenticate with a bearer token
- how to upload MP3, WAV, or OGG reference audio
- how to send voice metadata such as name, visibility, and language
- how to read the initial clone response and print the new `voice_id`
- how to optionally poll `/api/v1/tts/voice/{voice_id}` until the voice is available

Usage:
    python tts_clone.py
"""

import time
from pathlib import Path

import requests

# Configuration
API_BASE_URL = "https://dev.voice.ai"
# API_BASE_URL = "http://localhost:8000"  # Local/self-hosted override
API_KEY = "YOUR_API_KEY_HERE"

# Reference audio file (must be MP3, WAV, or OGG, max 7.5MB)
AUDIO_FILE = "path/to/your/reference_audio.mp3"
VOICE_NAME = "My Voice"

# Supported voice_visibility values:
# - "PUBLIC"
# - "PRIVATE"
VOICE_VISIBILITY = "PUBLIC"

# Supported language values:
# - "en", "ca", "sv", "es", "fr", "de", "it", "pt", "pl", "ru", "nl"
VOICE_LANGUAGE = "en"

# Polling is optional but useful because clone jobs are asynchronous.
WAIT_FOR_AVAILABLE = True
MAX_WAIT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2

headers = {
    "Authorization": f"Bearer {API_KEY}",
}

SUPPORTED_AUDIO_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}


def get_audio_content_type(audio_file: str) -> str:
    """Return the multipart content type for supported reference audio files."""
    suffix = Path(audio_file).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_CONTENT_TYPES:
        raise ValueError("Reference audio must use a .mp3, .wav, or .ogg file.")
    return SUPPORTED_AUDIO_CONTENT_TYPES[suffix]


def clone_voice(audio_file: str, name: str, visibility: str, language: str) -> tuple[str, str]:
    """Create a cloned voice and return its voice_id plus initial status."""
    print(f"Cloning voice from {audio_file}...")
    file_size = Path(audio_file).stat().st_size

    with open(audio_file, "rb") as file_handle:
        files = {
            "file": (Path(audio_file).name, file_handle, get_audio_content_type(audio_file))
        }
        data = {
            "name": name,
            "voice_visibility": visibility,
            "language": language,
        }
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tts/clone-voice",
            headers=headers,
            files=files,
            data=data,
        )

    response.raise_for_status()
    result = response.json()
    voice_id = result["voice_id"]
    status = result["status"]

    print(f"✓ Voice created: {voice_id}")
    print(f"  Initial status: {status}")
    print(f"  File size: {file_size} bytes")
    return voice_id, status


def wait_for_voice_available(voice_id: str, max_wait_seconds: int, poll_interval_seconds: int) -> bool:
    """Poll voice status until it becomes AVAILABLE, fails, or times out."""
    print(f"Waiting for voice {voice_id} to become available...")
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tts/voice/{voice_id}",
            headers=headers,
        )
        response.raise_for_status()

        voice_data = response.json()
        status = voice_data["status"]

        if status == "AVAILABLE":
            print("✓ Voice is available")
            return True
        if status == "FAILED":
            print("✗ Voice creation failed")
            return False

        print(f"  Status: {status} (waiting...)")
        time.sleep(poll_interval_seconds)

    print("✗ Timed out waiting for voice to become available")
    return False


def main():
    print("=" * 60)
    print("Voice.AI TTS Example: Clone Voice")
    print("=" * 60)

    try:
        voice_id, status = clone_voice(
            audio_file=AUDIO_FILE,
            name=VOICE_NAME,
            visibility=VOICE_VISIBILITY,
            language=VOICE_LANGUAGE,
        )

        print(f"\nVoice ID: {voice_id}")
        print(f"Current status: {status}")

        if WAIT_FOR_AVAILABLE:
            print()
            wait_for_voice_available(
                voice_id=voice_id,
                max_wait_seconds=MAX_WAIT_SECONDS,
                poll_interval_seconds=POLL_INTERVAL_SECONDS,
            )

    except requests.exceptions.HTTPError as exc:
        print(f"✗ HTTP Error: {exc}")
        if exc.response is not None:
            print(f"  Response: {exc.response.text}")
    except Exception as exc:
        print(f"✗ Error: {exc}")


if __name__ == "__main__":
    main()
