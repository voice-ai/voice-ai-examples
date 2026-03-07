# Telnyx Media Streams + Voice AI TTS

This example answers an inbound Telnyx call, opens a bidirectional media stream, requests speech from the voice.ai TTS WebSocket API, and streams that audio back to the caller.

It serves:
- `POST /telnyx/webhook` for Telnyx call-control events
- `WS /media` for the Telnyx bidirectional media stream

By default, both examples connect to `wss://dev.voice.ai/api/v1/tts/multi-stream`.

## Files

- `server_basic_example.py`: simplest working relay with fixed 20 ms playout and a small startup prebuffer
- `server_example.py`: advanced relay with a basic jitter buffer and rolling repacketization across upstream chunks
- `telnyx_setup.py`: one-time Telnyx app / DID provisioning script
- `requirements.txt`: example runtime dependencies

## Which example to use

Use `server_basic_example.py` for the clearest end-to-end example.

Use `server_example.py` if you want a slightly more robust relay that:
- keeps a bounded jitter buffer
- starts playout after a short prebuffer
- carries partial upstream bytes across chunk boundaries before framing

## Configuration

Runtime settings are hardcoded at the top of:
- `server_basic_example.py`
- `server_example.py`
- `telnyx_setup.py`

## Install

```bash
cd telnyx_media_streams_tts
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## Provision Telnyx

This wires the configured DID to the configured Telnyx Call Control app and webhook URL:

```bash
.venv/bin/python telnyx_setup.py
```

## Run

Run the basic example:

```bash
.venv/bin/python server_basic_example.py
```

It will listen on `http://localhost:8765` and serve:
- `POST /telnyx/webhook`
- `WS /media`

Run the advanced example:

```bash
.venv/bin/python server_example.py
```

It will listen on `http://localhost:8765` and serve:
- `POST /telnyx/webhook`
- `WS /media`

## Call flow

1. Telnyx sends an inbound webhook to `/telnyx/webhook`.
2. The example answers the call and starts bidirectional RTP streaming to `/media`.
3. `/media` opens a voice.ai TTS WebSocket request.
4. TTS audio is framed into 20 ms packets and streamed back to the caller.
