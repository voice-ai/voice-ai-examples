"""
voice.ai TTS Example - Voice Management

This example demonstrates the public voice-management endpoints:
- `POST /api/v1/tts/clone-voice`
- `GET /api/v1/tts/voices`
- `GET /api/v1/tts/voice/{voice_id}`
- `PATCH /api/v1/tts/voice/{voice_id}`
- `DELETE /api/v1/tts/voice/{voice_id}`

What this file shows:
- how to create a cloned voice with the supported clone request params
- how to list voices (no server-side query params are currently supported)
- how to fetch one voice by ID
- how to update `name` and `voice_visibility`
- how to optionally delete the created voice
"""

from pathlib import Path

import requests

# Configuration
API_BASE_URL = "https://dev.voice.ai"
# API_BASE_URL = "http://localhost:8000"  # Local/self-hosted override
API_KEY = "YOUR_API_KEY_HERE"

# Create /clone-voice request params
REFERENCE_AUDIO_FILE = "path/to/your/reference_audio.mp3"
CREATE_VOICE_NAME = "My Test Voice"

# Supported voice_visibility values:
# - "PUBLIC"
# - "PRIVATE"
CREATE_VOICE_VISIBILITY = "PUBLIC"

# Supported language values:
# - "en", "ca", "sv", "es", "fr", "de", "it", "pt", "pl", "ru", "nl"
CREATE_VOICE_LANGUAGE = "en"

# PATCH /voice/{voice_id} request params
UPDATE_VOICE_NAME = "Updated Voice Name"
UPDATE_VOICE_VISIBILITY = None  # Set to "PUBLIC" or "PRIVATE" to update visibility

DELETE_VOICE_AT_END = False

# Headers
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


def create_voice(audio_file: str, name: str, visibility: str = "PUBLIC", language: str = "en") -> dict:
    """Create (clone) a voice from reference audio using multipart/form-data."""
    print(f"Creating voice: {name}")
    
    # Read audio file and upload using multipart/form-data
    with open(audio_file, "rb") as f:
        files = {
            "file": (Path(audio_file).name, f, get_audio_content_type(audio_file))
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
    
    voice = response.json()
    print(f"✓ Created voice: {voice['voice_id']} (status: {voice['status']})")
    return voice


def list_voices() -> list:
    """List all voices accessible to the authenticated user."""
    print("Listing voices...")

    response = requests.get(
        f"{API_BASE_URL}/api/v1/tts/voices",
        headers=headers,
    )
    response.raise_for_status()
    
    voices = response.json()
    print(f"✓ Found {len(voices)} voice(s)")
    for voice in voices:
        print(f"  - {voice['voice_id']}: {voice.get('name', 'Unnamed')} ({voice.get('status')}, {voice.get('voice_visibility')})")
    
    return voices


def get_voice(voice_id: str) -> dict:
    """Get voice details by ID."""
    print(f"Getting voice: {voice_id}")
    
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tts/voice/{voice_id}",
        headers=headers,
    )
    response.raise_for_status()
    
    voice = response.json()
    print(f"✓ Voice details:")
    print(f"  ID: {voice['voice_id']}")
    print(f"  Name: {voice.get('name', 'Unnamed')}")
    print(f"  Status: {voice.get('status')}")
    print(f"  Visibility: {voice.get('voice_visibility')}")
    
    return voice


def update_voice(voice_id: str, name: str = None, visibility: str = None) -> dict:
    """
    Update voice metadata.
    
    Args:
        voice_id: Voice ID to update
        name: New name (optional)
        visibility: New visibility - "PUBLIC" or "PRIVATE" (optional)
    """
    print(f"Updating voice: {voice_id}")
    
    payload = {}
    if name is not None:
        payload["name"] = name
    if visibility is not None:
        payload["voice_visibility"] = visibility
    
    if not payload:
        print("  No updates provided")
        return get_voice(voice_id)
    
    response = requests.patch(
        f"{API_BASE_URL}/api/v1/tts/voice/{voice_id}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    
    voice = response.json()
    print(f"✓ Voice updated: {voice['voice_id']}")
    return voice


def delete_voice(voice_id: str) -> bool:
    """Delete (soft delete) a voice."""
    print(f"Deleting voice: {voice_id}")
    
    response = requests.delete(
        f"{API_BASE_URL}/api/v1/tts/voice/{voice_id}",
        headers=headers,
    )
    response.raise_for_status()
    
    print(f"✓ Voice deleted: {voice_id}")
    return True


def main():
    """Demonstrate all voice management operations"""
    print("=" * 60)
    print("voice.ai TTS Example: Voice Management")
    print("=" * 60)
    
    try:
        voice = create_voice(
            audio_file=REFERENCE_AUDIO_FILE,
            name=CREATE_VOICE_NAME,
            visibility=CREATE_VOICE_VISIBILITY,
            language=CREATE_VOICE_LANGUAGE,
        )
        voice_id = voice["voice_id"]
        
        list_voices()
        get_voice(voice_id)
        update_voice(
            voice_id=voice_id,
            name=UPDATE_VOICE_NAME,
            visibility=UPDATE_VOICE_VISIBILITY,
        )

        if DELETE_VOICE_AT_END:
            delete_voice(voice_id)
        
        print("\n" + "=" * 60)
        print("Voice management operations complete!")
        print("=" * 60)
        
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if e.response is not None:
            print(f"  Response: {e.response.text}")
    except FileNotFoundError:
        print(f"✗ Audio file not found: {REFERENCE_AUDIO_FILE}")
        print("  Please update REFERENCE_AUDIO_FILE at the top of the script")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    main()
