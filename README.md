# Voice AI Examples and Reference

This repository contains voice.ai example scripts.

For product documentation and the full API reference, use:
- [voice.ai/docs](https://voice.ai/docs)
- [voice.ai/docs/api-reference](https://voice.ai/docs/api-reference)

## Text to Speech

| Category | Example | Description |
| --- | --- | --- |
| Voice cloning | [`TTS Clone`](tts_clone.py) | Clone a voice from reference audio |
| Voice cloning | [`Voice CRUD`](tts_voice_crud.py) | Create, list, get, update, and delete voices |
| Inference | [`HTTP Speech`](tts_generate_speech.py) | Generate one complete audio response over HTTP |
| Inference | [`HTTP Speech Streaming`](tts_generate_speech_stream.py) | Stream audio over HTTP as it is generated |
| Inference | [`Single-Context WebSocket`](tts_websocket_single_context.py) | Single-generation WebSocket example |
| Inference | [`Multi-Context WebSocket`](tts_websocket_multi_context.py) | Multi-context WebSocket example |

## Voice Agents

| Example | Description |
| --- | --- |
| [`Agent Webhook Receiver`](webhook_receiver_server.py) | Simple server for receiving agent webhooks |

## Integrations

| Example | Description |
| --- | --- |
| [`Telnyx Media Streams TTS`](telnyx_media_streams_tts) | Telnyx relay examples with setup script and local README |
| [`LiveKit Plugins VoiceAI`](https://github.com/voice-ai/livekit-plugins-voiceai-example) | LiveKit Agents example repo using the voice.ai TTS plugin |

## Running The Examples

Edit the constants at the top of the file you want to run, then execute it directly:

```bash
python tts_clone.py
python tts_generate_speech.py
python tts_websocket_multi_context.py
```

Some integration examples have extra setup requirements. See the file header or the local README in that example folder when present.
