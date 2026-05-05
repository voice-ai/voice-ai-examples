"""
voice.ai WebSocket TTS Example - Single Context

This atomic example demonstrates the `/api/v1/tts/stream` protocol.
Use it when one WebSocket connection is dedicated to one single generation.

What this file shows:
- how to authenticate with a bearer token
- how to set the supported single-context init params at the top of the file
- how to send the required init message
- how to send optional text-only follow-up messages before the final flush
- how to collect audio chunks until `is_last`
- how to save the final response to a local audio file

Important behavior:
- `/api/v1/tts/stream` handles one completed generation per connection
- after the server finishes a flush, it sends `is_last` and closes the socket
- use `/api/v1/tts/multi-stream` for multiple completed generations on one connection

Usage:
    python tts_websocket_single_context.py
"""

import asyncio
import base64
import json
import time
from pathlib import Path

import websockets

# Configuration
VOICEAI_WS_URL = "wss://dev.voice.ai/api/v1/tts/stream"
# VOICEAI_WS_URL = "ws://localhost:8000/api/v1/tts/stream"  # Local/self-hosted override

# Your API credentials
API_KEY = "YOUR_API_KEY_HERE"

# Supported init params on /api/v1/tts/stream:
# - voice_id
# - text
# - language
# - model
# - dictionary_id
# - dictionary_version
# - audio_format
# - temperature
# - top_p
# - delivery_mode
# - flush
VOICE_ID = None  # Optional: set a voice ID to use a specific cloned voice

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
AUDIO_FORMAT = "mp3"
TEMPERATURE = 1.0
TOP_P = 0.8

# Supported model values:
# - "voiceai-tts-v1-latest"
# - "voiceai-tts-v1-2026-02-10"
# - "voiceai-tts-lite-v1-latest"
# - "voiceai-tts-lite-v1-2026-04-15"
# - "voiceai-tts-multilingual-v1-latest"
# - "voiceai-tts-multilingual-v1-2026-02-10"
MODEL = None  # Leave as None to let the server auto-select from LANGUAGE

# Supported language values:
# - "en", "ca", "sv", "es", "fr", "de", "it", "pt", "pl", "ru", "nl"
LANGUAGE = "en"

# Optional managed pronunciation dictionary settings:
# - dictionary_id: dictionary ID from /api/v1/tts/pronunciation-dictionaries
# - dictionary_version: optional saved version to pin; requires DICTIONARY_ID
DICTIONARY_ID = None
DICTIONARY_VERSION = None

# Supported delivery_mode values:
# - "raw"
# - "paced"  # Only meaningfully applied to PCM-style formats
DELIVERY_MODE = "raw"

OUTPUT_DIR = Path(".")
OUTPUT_FILE = "single_context_output.mp3"

INIT_TEXT = "Hello! This is the start of a single-context WebSocket test. "
INIT_FLUSH = False

# Supported follow-up message params after init:
# - text
# - flush
BUFFERED_TEXT_MESSAGES = [
    "This second message is buffered before generation on the same socket. ",
]
FINAL_TEXT = "This final message flushes the buffer and triggers generation."
FINAL_FLUSH = True


def build_headers() -> dict:
    """Build request headers for bearer token auth."""
    return {"Authorization": f"Bearer {API_KEY}"}


async def open_websocket(url: str, headers: dict):
    """Connect with compatibility across common websockets client versions."""
    try:
        return await websockets.connect(url, additional_headers=headers)
    except TypeError:
        return await websockets.connect(url, extra_headers=headers)


def save_audio(output_file: Path, audio_data: bytes) -> None:
    output_file.write_bytes(audio_data)
    print(f"  Saved audio to {output_file} ({len(audio_data)} bytes)")


def get_output_filename(audio_format: str) -> str:
    """Choose a simple file extension based on the configured audio format."""
    if audio_format.startswith("wav"):
        return "single_context_output.wav"
    if audio_format.startswith("pcm") or audio_format in {"alaw_8000", "ulaw_8000"}:
        return "single_context_output.pcm"
    if audio_format.startswith("opus"):
        return "single_context_output.opus"
    return OUTPUT_FILE


def build_init_payload() -> dict:
    """Build the init message from the top-level example constants."""
    payload = {
        "text": INIT_TEXT,
        "language": LANGUAGE,
        "audio_format": AUDIO_FORMAT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "delivery_mode": DELIVERY_MODE,
        "flush": INIT_FLUSH,
    }
    if VOICE_ID is not None:
        payload["voice_id"] = VOICE_ID
    if MODEL is not None:
        payload["model"] = MODEL
    if DICTIONARY_ID is not None:
        payload["dictionary_id"] = DICTIONARY_ID
    if DICTIONARY_VERSION is not None:
        payload["dictionary_version"] = DICTIONARY_VERSION
    return payload


def build_follow_up_payload(text: str, flush: bool) -> dict:
    """Build a text-only follow-up message."""
    return {
        "text": text,
        "flush": flush,
    }


async def receive_audio_until_complete(websocket) -> tuple[bytes, float, float]:
    """Read streamed audio until the server sends the final completion message."""
    audio_data = bytearray()
    request_start = time.time()
    ttfb_ms = None

    while True:
        message = await websocket.recv()
        msg_data = json.loads(message)

        if "audio" in msg_data:
            if ttfb_ms is None:
                ttfb_ms = (time.time() - request_start) * 1000
            audio_chunk = base64.b64decode(msg_data["audio"])
            audio_data.extend(audio_chunk)
            print(f"  Received {len(audio_chunk)} bytes")
            continue

        if msg_data.get("is_last"):
            total_ms = (time.time() - request_start) * 1000
            return bytes(audio_data), ttfb_ms or 0.0, total_ms

        if msg_data.get("error"):
            raise RuntimeError(msg_data["error"])


async def main():
    print("\n" + "=" * 60)
    print("voice.ai WebSocket TTS Example: Single Context")
    print("=" * 60)
    print(f"WebSocket URL: {VOICEAI_WS_URL}")
    print(f"Voice ID: {VOICE_ID}")

    websocket = None
    try:
        websocket = await open_websocket(VOICEAI_WS_URL, build_headers())
        print("✓ Connected to WebSocket\n")

        print(f"Init message: '{INIT_TEXT}'")
        await websocket.send(json.dumps(build_init_payload()))

        for text in BUFFERED_TEXT_MESSAGES:
            print(f"Buffered text-only message: '{text}'")
            await websocket.send(json.dumps(build_follow_up_payload(text, flush=False)))

        print(f"Final text-only message with flush: '{FINAL_TEXT}'")
        await websocket.send(json.dumps(build_follow_up_payload(FINAL_TEXT, FINAL_FLUSH)))

        audio_data, ttfb_ms, total_ms = await receive_audio_until_complete(websocket)
        print(f"  Complete: TTFB {ttfb_ms:.0f}ms, Total {total_ms:.0f}ms")
        save_audio(OUTPUT_DIR / get_output_filename(AUDIO_FORMAT), audio_data)
        print()

        print("✓ Single-context example complete")

    except Exception as exc:
        print(f"✗ Error: {exc}")
    finally:
        if websocket is not None:
            await websocket.close()


if __name__ == "__main__":
    asyncio.run(main())
