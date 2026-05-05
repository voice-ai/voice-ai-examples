"""
voice.ai WebSocket TTS Example - Multi Context

This atomic example demonstrates the `/api/v1/tts/multi-stream` protocol.
Use it when one WebSocket connection needs to handle multiple independent
TTS contexts at the same time.

What this file shows:
- how to authenticate with a bearer token
- how to set the supported multi-context init and follow-up params at the top of the file
- how to initialize multiple context IDs on the same socket
- how to receive interleaved audio responses by `context_id`
- how to send a text-only follow-up to an existing context
- how to save each context's audio to a local file

Usage:
    python tts_websocket_multi_context.py
"""

import asyncio
import base64
import json
import time
from pathlib import Path

import websockets

# Configuration
VOICEAI_WS_MULTI_URL = "wss://dev.voice.ai/api/v1/tts/multi-stream"
# VOICEAI_WS_MULTI_URL = "ws://localhost:8000/api/v1/tts/multi-stream"  # Local/self-hosted override

# Your API credentials
API_KEY = "YOUR_API_KEY_HERE"

# Supported init params on /api/v1/tts/multi-stream:
# - context_id
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
# - auto_close
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
INIT_FLUSH = True
INIT_AUTO_CLOSE = False

OUTPUT_DIR = Path(".")

INITIAL_CONTEXT_REQUESTS = [
    {
        "context_id": "ctx-1",
        "text": "Hello from context one on the shared WebSocket connection.",
    },
    {
        "context_id": "ctx-2",
        "text": "Hello from context two on the same shared connection.",
    },
]

FOLLOW_UP_CONTEXT_ID = "ctx-1"
FOLLOW_UP_TEXT = "This follow-up request reuses the existing ctx-1 context."

# Supported follow-up message params after init:
# - context_id
# - text
# - flush
# - auto_close
# - close_context
# - close_socket
FOLLOW_UP_FLUSH = True
FOLLOW_UP_AUTO_CLOSE = False
FOLLOW_UP_CLOSE_CONTEXT = False
FOLLOW_UP_CLOSE_SOCKET = False


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


def get_output_suffix(audio_format: str) -> str:
    """Choose a simple file suffix based on the configured audio format."""
    if audio_format.startswith("wav"):
        return ".wav"
    if audio_format.startswith("pcm") or audio_format in {"alaw_8000", "ulaw_8000"}:
        return ".pcm"
    if audio_format.startswith("opus"):
        return ".opus"
    return ".mp3"


def build_init_payload(context_id: str, text: str) -> dict:
    """Build one multi-context init message from the top-level constants."""
    payload = {
        "context_id": context_id,
        "text": text,
        "language": LANGUAGE,
        "audio_format": AUDIO_FORMAT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "delivery_mode": DELIVERY_MODE,
        "flush": INIT_FLUSH,
        "auto_close": INIT_AUTO_CLOSE,
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


def build_follow_up_payload() -> dict:
    """Build a text-only follow-up message for an existing context."""
    return {
        "context_id": FOLLOW_UP_CONTEXT_ID,
        "text": FOLLOW_UP_TEXT,
        "flush": FOLLOW_UP_FLUSH,
        "auto_close": FOLLOW_UP_AUTO_CLOSE,
        "close_context": FOLLOW_UP_CLOSE_CONTEXT,
        "close_socket": FOLLOW_UP_CLOSE_SOCKET,
    }


async def receive_contexts_until_complete(
    websocket,
    request_start_by_context: dict[str, float],
) -> dict[str, tuple[bytes, float, float]]:
    """Collect interleaved context responses until every requested context is complete."""
    audio_by_context = {
        context_id: bytearray() for context_id in request_start_by_context
    }
    ttfb_by_context = {context_id: None for context_id in request_start_by_context}
    completed = set()

    while len(completed) < len(request_start_by_context):
        message = await websocket.recv()
        msg_data = json.loads(message)
        context_id = msg_data.get("context_id")

        if context_id not in request_start_by_context:
            continue

        if "audio" in msg_data:
            if ttfb_by_context[context_id] is None:
                ttfb_by_context[context_id] = (
                    time.time() - request_start_by_context[context_id]
                ) * 1000
            audio_chunk = base64.b64decode(msg_data["audio"])
            audio_by_context[context_id].extend(audio_chunk)
            print(f"  {context_id}: received {len(audio_chunk)} bytes")
            continue

        if msg_data.get("is_last"):
            completed.add(context_id)
            continue

        if msg_data.get("error"):
            raise RuntimeError(f"{context_id}: {msg_data['error']}")

    results = {}
    for context_id, audio_data in audio_by_context.items():
        total_ms = (time.time() - request_start_by_context[context_id]) * 1000
        results[context_id] = (
            bytes(audio_data),
            ttfb_by_context[context_id] or 0.0,
            total_ms,
        )
    return results


async def main():
    print("\n" + "=" * 60)
    print("voice.ai WebSocket TTS Example: Multi Context")
    print("=" * 60)
    print(f"WebSocket URL: {VOICEAI_WS_MULTI_URL}")
    print(f"Voice ID: {VOICE_ID}")

    websocket = None
    try:
        websocket = await open_websocket(VOICEAI_WS_MULTI_URL, build_headers())
        print("✓ Connected to WebSocket\n")

        request_start_by_context = {}
        for request in INITIAL_CONTEXT_REQUESTS:
            context_id = request["context_id"]
            text = request["text"]
            print(f"Init {context_id}: '{text}'")
            request_start_by_context[context_id] = time.time()
            await websocket.send(json.dumps(build_init_payload(context_id, text)))

        initial_results = await receive_contexts_until_complete(
            websocket, request_start_by_context
        )
        output_suffix = get_output_suffix(AUDIO_FORMAT)
        for context_id, (audio_data, ttfb_ms, total_ms) in initial_results.items():
            print(
                f"  {context_id}: complete, TTFB {ttfb_ms:.0f}ms, Total {total_ms:.0f}ms"
            )
            save_audio(OUTPUT_DIR / f"multi_context_{context_id}{output_suffix}", audio_data)
        print()

        print(f"Follow-up {FOLLOW_UP_CONTEXT_ID} (text-only): '{FOLLOW_UP_TEXT}'")
        follow_up_start = {FOLLOW_UP_CONTEXT_ID: time.time()}
        await websocket.send(json.dumps(build_follow_up_payload()))

        follow_up_results = await receive_contexts_until_complete(
            websocket, follow_up_start
        )
        follow_up_audio, ttfb_ms, total_ms = follow_up_results[FOLLOW_UP_CONTEXT_ID]
        print(
            f"  {FOLLOW_UP_CONTEXT_ID}: follow-up complete, TTFB {ttfb_ms:.0f}ms, Total {total_ms:.0f}ms"
        )
        save_audio(
            OUTPUT_DIR / f"multi_context_{FOLLOW_UP_CONTEXT_ID}_follow_up{output_suffix}",
            follow_up_audio,
        )
        print()

        print("✓ Multi-context example complete")

    except Exception as exc:
        print(f"✗ Error: {exc}")
    finally:
        if websocket is not None:
            await websocket.close()


if __name__ == "__main__":
    asyncio.run(main())
