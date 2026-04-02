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
| Dictionaries | [`Pronunciation Dictionary CRUD`](tts_pronunciation_dictionary_crud.py) | Create, import, list, rename, version, download, and delete pronunciation dictionaries |
| Inference | [`HTTP Speech`](tts_generate_speech.py) | Generate one complete audio response over HTTP |
| Inference | [`HTTP Speech Streaming`](tts_generate_speech_stream.py) | Stream audio over HTTP as it is generated |
| Inference | [`Single-Context WebSocket`](tts_websocket_single_context.py) | Single-generation WebSocket example |
| Inference | [`Multi-Context WebSocket`](tts_websocket_multi_context.py) | Multi-context WebSocket example |

The inference examples above also include optional `dictionary_id` and `dictionary_version`
constants so you can attach a managed pronunciation dictionary to direct TTS requests.

## Voice Agents

| Example | Description |
| --- | --- |
| [`Agent Webhook Receiver`](webhook_receiver_server.py) | Simple server for receiving event, inbound-call, and tool webhooks |
| [`Widget Browser Demo`](voice_agent_widget_browser_sdk_demo.html) | Browser SDK widget example using the packaged web SDK |
| [`Managed Tools Browser Demo`](managed_tools_browser_sdk_demo.html) | Browser SDK example for the shared Google managed-tools connection and per-tool readiness |

## Integrations

| Example | Description |
| --- | --- |
| [`Telnyx Media Streams TTS`](telnyx_media_streams_tts) | Telnyx relay examples with setup instructions |
| [`LiveKit Plugins VoiceAI`](https://github.com/voice-ai/livekit-plugins-voiceai-example) | LiveKit Agents example repo using the voice.ai TTS plugin |

## Running The Examples

Edit the constants at the top of the file you want to run, then execute it directly:

```bash
python tts_clone.py
python tts_pronunciation_dictionary_crud.py
python tts_generate_speech.py
python tts_websocket_multi_context.py
```

Some integration examples have extra setup requirements. See the file header or the setup instructions in that example folder when needed.

## Browser SDK Demos

Browser SDK demos:

- [`voice_agent_widget_browser_sdk_demo.html`](voice_agent_widget_browser_sdk_demo.html)
- [`managed_tools_browser_sdk_demo.html`](managed_tools_browser_sdk_demo.html)
- [`sdk/web/demo/README.md`](../sdk/web/demo/README.md)
