# Voice AI Examples and Reference

This repository contains voice.ai example scripts.

For product documentation and the full API reference, use:
- [voice.ai/docs](https://voice.ai/docs)
- [voice.ai/docs/api-reference](https://voice.ai/docs/api-reference)

## Examples

| Example | Description |
| --- | --- |
| `TTS Clone` | Clone a voice from reference audio |
| `Voice CRUD` | Create, list, get, update, and delete voices |
| `HTTP Speech` | Generate one complete audio response over HTTP |
| `HTTP Speech Streaming` | Stream audio over HTTP as it is generated |
| `Single-Context WebSocket` | One-generation WebSocket example |
| `Multi-Context WebSocket` | Multi-context WebSocket example |
| `Agent Webhook Receiver` | Simple server for receiving agent webhooks |
| `Telnyx Media Streams TTS` | Telnyx relay examples with setup script and local README |
| `LiveKit Plugins VoiceAI` | LiveKit Agents example repo using the voice.ai TTS plugin |

## Running The Examples

Edit the constants at the top of the file you want to run, then execute it directly:

```bash
python tts_clone.py
python tts_generate_speech.py
python tts_websocket_multi_context.py
```

Some integration examples have extra setup requirements. See the file header or the local README in that example folder when present.
