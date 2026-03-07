# Voice AI Examples and Reference

This repository is a small set of standalone voice.ai example scripts.

Each example is meant to be readable on its own:
- the purpose of the file is explained in the header comment or docstring
- editable constants live at the top of the file
- the scripts default to the public `dev.voice.ai` environment unless noted otherwise

For product documentation and the full API reference, use:
- [voice.ai/docs](https://voice.ai/docs)
- [voice.ai/docs/api-reference](https://voice.ai/docs/api-reference)

## Files

- `tts_clone.py` - clone a voice from reference audio
- `tts_voice_crud.py` - create, list, get, update, and delete voices
- `tts_generate_speech.py` - generate one complete audio response over HTTP
- `tts_generate_speech_stream.py` - stream audio over HTTP as it is generated
- `tts_websocket_single_context.py` - one-generation WebSocket example
- `tts_websocket_multi_context.py` - multi-context WebSocket example
- `webhook_receiver_server.py` - agent webhook receiver example
- `telnyx_media_streams_tts/server_basic_example.py` - basic Telnyx relay example
- `telnyx_media_streams_tts/server_example.py` - more advanced Telnyx relay example

## Running The Examples

Edit the constants at the top of the file you want to run, then execute it directly:

```bash
python tts_clone.py
python tts_generate_speech.py
python tts_websocket_multi_context.py
```

Some integration examples have extra setup requirements. See the file header or the local README in that example folder when present.
