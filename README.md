# TTS API Examples and Reference

This repository contains public Voice.AI TTS examples aligned to the documented public API surface.

The top-level examples default to the public Voice.AI dev environment:
- HTTP: `https://dev.voice.ai`
- WebSocket: `wss://dev.voice.ai`

Each standalone script keeps editable constants at the top of the file and only exposes the public request fields documented for that endpoint.

## Files

- `tts_clone.py` - clone a voice with `/api/v1/tts/clone-voice`
- `tts_voice_crud.py` - create, list, get, update, and delete voices
- `tts_generate_speech.py` - non-streaming HTTP speech generation with `/api/v1/tts/speech`
- `tts_generate_speech_stream.py` - streaming HTTP speech generation with `/api/v1/tts/speech/stream`
- `tts_websocket_single_context.py` - single-generation WebSocket flow for `/api/v1/tts/stream`
- `tts_websocket_multi_context.py` - multi-context WebSocket flow for `/api/v1/tts/multi-stream`
- `telnyx_media_streams_tts/server_basic_example.py` - basic Telnyx relay using `/api/v1/tts/multi-stream`
- `telnyx_media_streams_tts/server_example.py` - more robust Telnyx relay using `/api/v1/tts/multi-stream`
- `webhook_receiver_server.py` - webhook receiver helper

## Quick Start

```bash
python tts_clone.py
python tts_voice_crud.py
python tts_generate_speech.py
python tts_generate_speech_stream.py
python tts_websocket_single_context.py
python tts_websocket_multi_context.py
```

## Prereqs

For curl and WebSocket examples:

```bash
export API_TOKEN="your-api-key-or-jwt-here"
export API_BASE_URL="https://dev.voice.ai"
export WS_BASE_URL="wss://dev.voice.ai"

# Local or self-hosted overrides:
# export API_BASE_URL="http://localhost:8000"
# export WS_BASE_URL="ws://localhost:8000"
```

Authentication for all public examples is:
- `Authorization: Bearer <API_TOKEN>`

## Supported Values

### Voice Visibility

- `PUBLIC`
- `PRIVATE`

### Voice Status Values

- `PENDING`
- `PROCESSING`
- `AVAILABLE`
- `FAILED`

### Supported Languages

- `en`
- `ca`
- `sv`
- `es`
- `fr`
- `de`
- `it`
- `pt`
- `pl`
- `ru`
- `nl`

### Supported Models

- `voiceai-tts-v1-latest`
- `voiceai-tts-v1-2026-02-10`
- `voiceai-tts-multilingual-v1-latest`
- `voiceai-tts-multilingual-v1-2026-02-10`

If `model` is omitted, the API auto-selects from `language`. English uses the English model family. Non-English languages use the multilingual family.

### Supported Audio Formats

- Basic: `mp3`, `wav`, `pcm`
- Telephony: `alaw_8000`, `ulaw_8000`
- MP3 variants: `mp3_22050_32`, `mp3_24000_48`, `mp3_44100_32`, `mp3_44100_64`, `mp3_44100_96`, `mp3_44100_128`, `mp3_44100_192`
- Opus variants: `opus_48000_32`, `opus_48000_64`, `opus_48000_96`, `opus_48000_128`, `opus_48000_192`
- PCM variants: `pcm_8000`, `pcm_16000`, `pcm_22050`, `pcm_24000`, `pcm_32000`, `pcm_44100`, `pcm_48000`
- WAV variants: `wav_16000`, `wav_22050`, `wav_24000`

### Supported Delivery Modes

- `raw`
- `paced`

`paced` is applied only to PCM-based outputs: `pcm`, `pcm_*`, `ulaw_8000`, and `alaw_8000`.

## HTTP Endpoints

### Clone Voice

**POST** `/api/v1/tts/clone-voice`

Reference script: `python tts_clone.py`

```bash
curl -X POST "${API_BASE_URL}/api/v1/tts/clone-voice" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -F "file=@./reference.wav" \
  -F "name=My Voice" \
  -F "voice_visibility=PUBLIC" \
  -F "language=en"
```

Example response:

```json
{
  "voice_id": "abc-123-def-456",
  "status": "PENDING"
}
```

### Get Voice

**GET** `/api/v1/tts/voice/{voice_id}`

```bash
curl -X GET "${API_BASE_URL}/api/v1/tts/voice/<VOICE_ID>" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

Example response:

```json
{
  "voice_id": "abc-123-def-456",
  "status": "AVAILABLE",
  "name": "My Voice",
  "voice_visibility": "PUBLIC"
}
```

### List Voices

**GET** `/api/v1/tts/voices`

There are currently no public query parameters on this endpoint.

```bash
curl -X GET "${API_BASE_URL}/api/v1/tts/voices" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

### Update Voice

**PATCH** `/api/v1/tts/voice/{voice_id}`

```bash
curl -X PATCH "${API_BASE_URL}/api/v1/tts/voice/<VOICE_ID>" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Voice Name",
    "voice_visibility": "PRIVATE"
  }'
```

### Delete Voice

**DELETE** `/api/v1/tts/voice/{voice_id}`

```bash
curl -X DELETE "${API_BASE_URL}/api/v1/tts/voice/<VOICE_ID>" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

### Generate Speech

**POST** `/api/v1/tts/speech`

Reference script: `python tts_generate_speech.py`

```bash
curl -X POST "${API_BASE_URL}/api/v1/tts/speech" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the Voice.AI HTTP speech example.",
    "voice_id": "your-voice-id",
    "audio_format": "mp3",
    "temperature": 1.0,
    "top_p": 0.8,
    "model": "voiceai-tts-v1-latest",
    "language": "en"
  }' \
  --output speech_output.mp3
```

Omit `voice_id` to use the default built-in voice.

### Generate Speech Stream

**POST** `/api/v1/tts/speech/stream`

Reference script: `python tts_generate_speech_stream.py`

```bash
curl -N -X POST "${API_BASE_URL}/api/v1/tts/speech/stream" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the Voice.AI HTTP streaming example.",
    "voice_id": "your-voice-id",
    "audio_format": "mp3",
    "temperature": 1.0,
    "top_p": 0.8,
    "model": "voiceai-tts-v1-latest",
    "language": "en"
  }' \
  --output speech_stream.mp3
```

Omit `voice_id` to use the default built-in voice.

## WebSocket Endpoints

### Single-Context WebSocket

**WS** `/api/v1/tts/stream`

Reference script: `python tts_websocket_single_context.py`

This is a single-generation protocol:
- first message is an init message
- optional follow-up messages are text-only
- once a flush completes, the server sends `is_last` and closes the socket

```bash
websocat \
  -H "Authorization: Bearer ${API_TOKEN}" \
  "${WS_BASE_URL}/api/v1/tts/stream"
```

Init message fields:

```json
{
  "voice_id": "your-voice-id",
  "text": "Hello ",
  "language": "en",
  "model": "voiceai-tts-v1-latest",
  "audio_format": "mp3",
  "temperature": 1.0,
  "top_p": 0.8,
  "delivery_mode": "raw",
  "flush": false
}
```

Follow-up message fields:

```json
{
  "text": "world",
  "flush": true
}
```

Server messages:
- `{"audio": "<base64>"}`
- `{"is_last": true}`

### Multi-Context WebSocket

**WS** `/api/v1/tts/multi-stream`

Reference script: `python tts_websocket_multi_context.py`

This protocol keeps one socket open for multiple independent contexts.

```bash
websocat \
  -H "Authorization: Bearer ${API_TOKEN}" \
  "${WS_BASE_URL}/api/v1/tts/multi-stream"
```

Init message fields:

```json
{
  "context_id": "ctx-1",
  "voice_id": "your-voice-id",
  "text": "Hello from ctx-1",
  "language": "en",
  "model": "voiceai-tts-v1-latest",
  "audio_format": "mp3",
  "temperature": 1.0,
  "top_p": 0.8,
  "delivery_mode": "raw",
  "flush": true,
  "auto_close": false
}
```

Follow-up message fields:

```json
{
  "context_id": "ctx-1",
  "text": "More text for ctx-1",
  "flush": true,
  "auto_close": false,
  "close_context": false,
  "close_socket": false
}
```

Server messages:
- `{"audio": "<base64>", "context_id": "ctx-1"}`
- `{"is_last": true, "context_id": "ctx-1"}`
- `{"context_closed": true, "context_id": "ctx-1"}` after an explicit or automatic context close

## Parameter Reference

### Clone Voice Request

- `file` required: MP3, WAV, or OGG reference audio, max 7.5 MB
- `name` optional: voice display name
- `voice_visibility` optional, default `PUBLIC`: `PUBLIC` or `PRIVATE`
- `language` optional, default `en`: one of the supported language codes listed above

### Update Voice Request

- `name` optional: new voice name
- `voice_visibility` optional: `PUBLIC` or `PRIVATE`

### GenerateSpeechRequest

- `text` required: non-empty text input
- `voice_id` optional: omit to use the default built-in voice
- `audio_format` optional, default `mp3`: one of the supported audio formats listed above
- `temperature` optional, default `1.0`: range `0.0` to `2.0`
- `top_p` optional, default `0.8`: range `0.0` to `1.0`
- `model` optional: one of the supported model IDs above; if omitted, the API selects from `language`
- `language` optional, default `en`: one of the supported language codes above

### Single-Context WebSocket Init Message

- `voice_id` optional
- `text` required
- `language` optional, default `en`
- `model` optional
- `audio_format` optional, default `mp3`
- `temperature` optional, default `1.0`
- `top_p` optional, default `0.8`
- `delivery_mode` optional, default `raw`
- `flush` optional, default `false`

### Single-Context WebSocket Text Message

- `text` required
- `flush` optional, default `false`

### Multi-Context WebSocket Init Message

- `context_id` optional: auto-generated if omitted
- `voice_id` optional
- `text` required
- `language` optional, default `en`
- `model` optional
- `audio_format` optional, default `mp3`
- `temperature` optional, default `1.0`
- `top_p` optional, default `0.8`
- `delivery_mode` optional, default `raw`
- `flush` optional, default `false`
- `auto_close` optional, default `false`

### Multi-Context WebSocket Text Message

- `context_id` required
- `text` optional, default empty string
- `flush` optional, default `false`
- `auto_close` optional, default `false`
- `close_context` optional, default `false`
- `close_socket` optional, default `false`

## Troubleshooting

### 404 on `voice_id`

- the voice may not exist
- the voice may still be `PENDING` or `PROCESSING`
- a private voice returns `404` to non-owners

### Validation errors

- `language`, `model`, `audio_format`, `delivery_mode`, and `voice_visibility` must come from the supported sets above
- `temperature` must be within `0.0` to `2.0`
- `top_p` must be within `0.0` to `1.0`

### WebSocket behavior

- `/api/v1/tts/stream` closes after one completed flush
- use `/api/v1/tts/multi-stream` if you need multiple completed generations on one connection
