import asyncio
import base64
import contextlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect


# =============================================================================
# TELNYX TTS RELAY: ADVANCED EXAMPLE
# =============================================================================
# Slightly more robust example for a Telnyx <-> Voice.ai TTS relay.
# Strategy:
# - fixed 20 ms playout cadence
# - bounded jitter buffer with a short prebuffer
# - rolling carry buffer so partial upstream chunks are framed cleanly
#
# Recommended settings:
# - TTS_API_PARAMS["audio_format"] = "pcm_16000"
# - TTS_API_PARAMS["delivery_mode"] = "paced"
# - TELNYX_AUDIO_FORMAT = "l16_16000"

# =============================================================================
# CONFIGURATION
# =============================================================================

HOST = "0.0.0.0"
PORT = 8765
STREAM_START_DELAY_MS = 0.0
JITTER_BUFFER_PREBUFFER_MS = 100.0
JITTER_BUFFER_MAX_MS = 1000.0
SEND_SILENCE_ON_UNDERRUN = True

TTS_WS_URL = "wss://dev.voice.ai/api/v1/tts/multi-stream"
TTS_AUTH_TOKEN = ""

# Voice.ai multi-context WebSocket init params used by this example.
# Publicly documented init params for `/api/v1/tts/multi-stream` are:
# - context_id
# - voice_id
# - text
# - language
# - model
# - audio_format
# - temperature
# - top_p
# - delivery_mode
# - flush
# - auto_close
TTS_API_PARAMS = {
    "audio_format": "pcm_16000",
    "delivery_mode": "paced",
    "flush": True,
    "auto_close": True,
    # "voice_id": "",
    # "temperature": 1.0,
    # "top_p": 0.8,
    # "model": "voiceai-tts-v1-latest",
    # "language": "",
}

# Supported paths in this example:
#   ulaw_8000 -> ulaw_8000
#   pcm_16000 -> l16_16000
TELNYX_AUDIO_FORMAT = "l16_16000"

TELNYX_API_KEY = ""
TELNYX_WEBHOOK_URL = "https://yourdomain.com/telnyx/webhook"
ENABLE_CALL_RECORDING = True
DOWNLOAD_RECORDINGS = True

TTS_CONTEXT_PREFIX = "telnyx-call"
TTS_TEXTS = [
    "This is utterance one of the Voice AI websocket relay example.",
    "This is utterance two of the Voice AI websocket relay example.",
    "This is utterance three of the Voice AI websocket relay example.",
]


logger = logging.getLogger("tts_telnyx_test_example")
logging.basicConfig(level=logging.INFO)
app = FastAPI()
CURRENT_DIR = Path(__file__).resolve().parent
RECORDINGS_DIR = CURRENT_DIR / "recordings"

FRAME_DURATION_S = 0.02
CODEC_FRAME_BYTES = {
    "ulaw_8000": 160,
    "pcm_16000": 640,
    "l16_16000": 640,
}
CODEC_SAMPLE_RATE = {
    "ulaw_8000": 8000,
    "pcm_16000": 16000,
    "l16_16000": 16000,
}
TELNYX_CODEC_NAME = {
    "ulaw_8000": "PCMU",
    "l16_16000": "L16",
}
SUPPORTED_CODEC_PATHS = {
    ("ulaw_8000", "ulaw_8000"),
    ("pcm_16000", "l16_16000"),
}

TTS_AUDIO_FORMAT = TTS_API_PARAMS["audio_format"]
TELNYX_FRAME_BYTES = CODEC_FRAME_BYTES[TELNYX_AUDIO_FORMAT]
TELNYX_RTP_CODEC = TELNYX_CODEC_NAME[TELNYX_AUDIO_FORMAT]
TELNYX_RTP_SAMPLE_RATE = CODEC_SAMPLE_RATE[TELNYX_AUDIO_FORMAT]
SILENCE_BYTE = b"\xff" if TELNYX_AUDIO_FORMAT == "ulaw_8000" else b"\x00"
SILENCE_FRAME_B64 = base64.b64encode(SILENCE_BYTE * TELNYX_FRAME_BYTES).decode("ascii")
JITTER_BUFFER_PREBUFFER_FRAMES = max(0, int(round(JITTER_BUFFER_PREBUFFER_MS / (FRAME_DURATION_S * 1000.0))))
JITTER_BUFFER_MAX_FRAMES = max(1, int(round(JITTER_BUFFER_MAX_MS / (FRAME_DURATION_S * 1000.0))))


class NormalMediaDisconnect(Exception):
    pass


class RelayStats:
    def __init__(self) -> None:
        self.upstream_messages = 0
        self.frames_enqueued = 0
        self.frames_sent = 0
        self.frames_dropped = 0
        self.underruns = 0
        self.late_frames = 0
        self.max_late_ms = 0.0
        self.max_buffer_depth = 0


def _validate_config() -> None:
    if TTS_AUDIO_FORMAT not in CODEC_FRAME_BYTES:
        raise RuntimeError(f"Unsupported TTS audio_format={TTS_AUDIO_FORMAT!r}")
    if TELNYX_AUDIO_FORMAT not in TELNYX_CODEC_NAME:
        raise RuntimeError(f"Unsupported TELNYX_AUDIO_FORMAT={TELNYX_AUDIO_FORMAT!r}")
    if (TTS_AUDIO_FORMAT, TELNYX_AUDIO_FORMAT) not in SUPPORTED_CODEC_PATHS:
        raise RuntimeError(
            "Unsupported codec path for this example: "
            f"TTS audio_format={TTS_AUDIO_FORMAT}, TELNYX_AUDIO_FORMAT={TELNYX_AUDIO_FORMAT}."
        )
    if TTS_API_PARAMS.get("delivery_mode") not in {"raw", "paced"}:
        raise RuntimeError("TTS_API_PARAMS['delivery_mode'] must be 'raw' or 'paced'")


_validate_config()


def _safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "unknown"


def _is_normal_media_close(exc: Exception) -> bool:
    if isinstance(exc, WebSocketDisconnect):
        return True
    class_name = exc.__class__.__name__
    text = str(exc).lower()
    return class_name == "ConnectionClosedOK" or "after websocket.close" in text


def _convert_upstream_raw_for_telnyx(raw: bytes) -> bytes:
    if not raw:
        return raw
    if TTS_AUDIO_FORMAT == "ulaw_8000" and TELNYX_AUDIO_FORMAT == "ulaw_8000":
        return raw
    if TTS_AUDIO_FORMAT == "pcm_16000" and TELNYX_AUDIO_FORMAT == "l16_16000":
        return raw
    raise RuntimeError(
        f"No conversion implemented for TTS audio_format={TTS_AUDIO_FORMAT} -> TELNYX_AUDIO_FORMAT={TELNYX_AUDIO_FORMAT}"
    )


def _decode_upstream_audio(payload_b64: str) -> bytes:
    raw = _convert_upstream_raw_for_telnyx(base64.b64decode(payload_b64))
    return raw


def _take_complete_frames(pending_audio: bytearray) -> list[str]:
    frames: list[str] = []
    while len(pending_audio) >= TELNYX_FRAME_BYTES:
        frame = bytes(pending_audio[:TELNYX_FRAME_BYTES])
        del pending_audio[:TELNYX_FRAME_BYTES]
        frames.append(base64.b64encode(frame).decode("ascii"))
    return frames


def _flush_final_frame(pending_audio: bytearray) -> Optional[str]:
    if not pending_audio:
        return None
    frame = bytes(pending_audio) + (SILENCE_BYTE * (TELNYX_FRAME_BYTES - len(pending_audio)))
    pending_audio.clear()
    return base64.b64encode(frame).decode("ascii")


async def _sleep_with_deadline(next_deadline: float, interval_s: float, stats: RelayStats) -> float:
    target_deadline = next_deadline + interval_s
    remaining = target_deadline - time.monotonic()
    if remaining > 0:
        await asyncio.sleep(remaining)
        return target_deadline

    late_ms = -remaining * 1000.0
    stats.late_frames += 1
    stats.max_late_ms = max(stats.max_late_ms, late_ms)
    if -remaining > interval_s:
        return time.monotonic()
    return target_deadline


async def send_telnyx_media(websocket: WebSocket, payload_b64: str) -> None:
    try:
        await websocket.send_json({"event": "media", "media": {"payload": payload_b64}})
    except Exception as exc:
        if _is_normal_media_close(exc):
            raise NormalMediaDisconnect() from exc
        raise


async def open_tts_websocket():
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("The 'websockets' package is required for TTS relay") from exc

    headers = {}
    if TTS_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {TTS_AUTH_TOKEN}"

    try:
        return await websockets.connect(TTS_WS_URL, additional_headers=headers or None)
    except TypeError:
        return await websockets.connect(TTS_WS_URL, extra_headers=headers or None)


def make_tts_init_payload(text: str, context_id: str) -> dict:
    payload = dict(TTS_API_PARAMS)
    payload["context_id"] = context_id
    payload["text"] = text
    return payload


async def _reader(tts_ws, context_id: str, queue: asyncio.Queue[str], done_event: asyncio.Event, stats: RelayStats) -> None:
    pending_audio = bytearray()

    async def _enqueue_frame(frame_payload: str) -> None:
        if queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                queue.get_nowait()
            stats.frames_dropped += 1
        await queue.put(frame_payload)
        stats.frames_enqueued += 1
        stats.max_buffer_depth = max(stats.max_buffer_depth, queue.qsize())

    while True:
        raw = await tts_ws.recv()
        if isinstance(raw, bytes):
            raise RuntimeError("Unexpected binary payload from TTS websocket")

        msg = json.loads(raw)
        if msg.get("context_id") and msg.get("context_id") != context_id:
            continue
        if msg.get("error"):
            raise RuntimeError(f"TTS error: {msg['error']}")

        audio_payload = msg.get("audio")
        if audio_payload:
            stats.upstream_messages += 1
            pending_audio.extend(_decode_upstream_audio(audio_payload))
            for frame_payload in _take_complete_frames(pending_audio):
                await _enqueue_frame(frame_payload)

        if msg.get("is_last") or msg.get("context_closed"):
            final_frame = _flush_final_frame(pending_audio)
            if final_frame is not None:
                await _enqueue_frame(final_frame)
            done_event.set()
            return


async def _player(websocket: WebSocket, queue: asyncio.Queue[str], done_event: asyncio.Event, stats: RelayStats) -> None:
    while queue.qsize() < JITTER_BUFFER_PREBUFFER_FRAMES and not done_event.is_set():
        await asyncio.sleep(0.005)

    # Start the playout clock only after the initial prebuffer has filled.
    # Starting the deadline earlier compresses the first few frames of each
    # utterance because the player thinks it is already late before audio
    # playout has actually begun.
    deadline = time.monotonic()

    while True:
        if done_event.is_set() and queue.empty():
            return

        payload = None
        with contextlib.suppress(asyncio.QueueEmpty):
            payload = queue.get_nowait()

        if payload is None:
            stats.underruns += 1
            if SEND_SILENCE_ON_UNDERRUN:
                try:
                    await send_telnyx_media(websocket, SILENCE_FRAME_B64)
                except NormalMediaDisconnect:
                    return
        else:
            try:
                await send_telnyx_media(websocket, payload)
            except NormalMediaDisconnect:
                return
            stats.frames_sent += 1

        deadline = await _sleep_with_deadline(deadline, FRAME_DURATION_S, stats)


async def relay_tts_utterance(websocket: WebSocket, text: str, utterance_index: int) -> None:
    context_id = f"{TTS_CONTEXT_PREFIX}-{utterance_index}-{int(time.time() * 1000)}"
    tts_ws = await open_tts_websocket()
    stats = RelayStats()
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=JITTER_BUFFER_MAX_FRAMES)
    done_event = asyncio.Event()

    logger.info(
        "Starting utterance %s/%s delivery_mode=%s jitter_buffer_prebuffer_ms=%.0f jitter_buffer_max_ms=%.0f tts_audio_format=%s telnyx_audio_format=%s",
        utterance_index,
        len(TTS_TEXTS),
        TTS_API_PARAMS["delivery_mode"],
        JITTER_BUFFER_PREBUFFER_MS,
        JITTER_BUFFER_MAX_MS,
        TTS_AUDIO_FORMAT,
        TELNYX_AUDIO_FORMAT,
    )

    try:
        await tts_ws.send(json.dumps(make_tts_init_payload(text, context_id)))
        reader_task = asyncio.create_task(_reader(tts_ws, context_id, queue, done_event, stats))
        player_task = asyncio.create_task(_player(websocket, queue, done_event, stats))

        done, pending = await asyncio.wait({reader_task, player_task}, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, NormalMediaDisconnect):
                raise exc
    finally:
        with contextlib.suppress(Exception):
            await tts_ws.close()

    logger.info(
        "Completed utterance %s/%s frames_enqueued=%s frames_sent=%s frames_dropped=%s underruns=%s late_frames=%s max_late_ms=%.1f max_buffer_depth=%s upstream_messages=%s",
        utterance_index,
        len(TTS_TEXTS),
        stats.frames_enqueued,
        stats.frames_sent,
        stats.frames_dropped,
        stats.underruns,
        stats.late_frames,
        stats.max_late_ms,
        stats.max_buffer_depth,
        stats.upstream_messages,
    )


async def relay_tts_sequence(websocket: WebSocket) -> None:
    for index, text in enumerate(TTS_TEXTS, start=1):
        await relay_tts_utterance(websocket, text, index)


def _extract_telnyx_event(body: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    event_type = data.get("event_type") or body.get("event_type")
    call_control_id = payload.get("call_control_id") or data.get("call_control_id")
    event_id = data.get("id") or body.get("id")
    return event_type, call_control_id, event_id


def _extract_telnyx_payload(body: dict) -> dict:
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    payload = data.get("payload")
    return payload if isinstance(payload, dict) else {}


def _derive_telnyx_stream_url(request: Request) -> str:
    parsed = urlparse(TELNYX_WEBHOOK_URL)
    if parsed.netloc:
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{ws_scheme}://{parsed.netloc}/media"

    forwarded_proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    ws_scheme = "wss" if forwarded_proto == "https" else "ws"
    if not forwarded_host:
        raise RuntimeError("Unable to determine public host for Telnyx stream URL")
    return f"{ws_scheme}://{forwarded_host}/media"


def _post_telnyx_call_control(call_control_id: str, action: str, payload: dict) -> dict:
    req = UrlRequest(
        url=f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/{action}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req) as response:
            raw = response.read()
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telnyx {action} failed: {exc.code} {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Telnyx {action} failed: {exc}") from exc

    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _download_recording_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = UrlRequest(url=url, headers={"Accept": "audio/wav"})
    with urlopen(req) as response:
        output_path.write_bytes(response.read())


async def _handle_recording_saved(payload: dict) -> None:
    if not DOWNLOAD_RECORDINGS:
        return
    recording_id = payload.get("recording_id", "unknown")
    call_control_id = payload.get("call_control_id", "unknown")
    recording_urls = payload.get("recording_urls") if isinstance(payload.get("recording_urls"), dict) else {}
    wav_url = recording_urls.get("wav")
    if not wav_url:
        logger.warning("call.recording.saved missing wav URL for recording_id=%s", recording_id)
        return

    safe_call_control_id = _safe_filename_component(str(call_control_id))
    safe_recording_id = _safe_filename_component(str(recording_id))
    output_path = RECORDINGS_DIR / f"{safe_call_control_id}_{safe_recording_id}.wav"
    try:
        await asyncio.to_thread(_download_recording_file, wav_url, output_path)
        logger.info("Saved Telnyx recording to %s", output_path)
    except Exception:
        logger.exception("Failed to download Telnyx recording recording_id=%s", recording_id)


async def _answer_call_and_start_stream(call_control_id: str, command_id: str, stream_url: str) -> None:
    payload = {
        "stream_url": stream_url,
        "stream_track": "inbound_track",
        "stream_codec": TELNYX_RTP_CODEC,
        "stream_bidirectional_mode": "rtp",
        "stream_bidirectional_codec": TELNYX_RTP_CODEC,
        "stream_bidirectional_sampling_rate": TELNYX_RTP_SAMPLE_RATE,
        "stream_bidirectional_target_legs": "self",
        "command_id": command_id,
    }
    if ENABLE_CALL_RECORDING:
        payload["record"] = "record-from-answer"
        payload["record_format"] = "wav"
        payload["record_channels"] = "dual"

    logger.info(
        "Answering Telnyx call call_control_id=%s stream_url=%s codec=%s sample_rate=%s",
        call_control_id,
        stream_url,
        TELNYX_RTP_CODEC,
        TELNYX_RTP_SAMPLE_RATE,
    )
    response = await asyncio.to_thread(_post_telnyx_call_control, call_control_id, "answer", payload)
    logger.info("Telnyx answer accepted for call_control_id=%s response=%s", call_control_id, response)


@app.post("/telnyx/webhook")
async def telnyx_webhook(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_type, call_control_id, event_id = _extract_telnyx_event(body)
    payload = _extract_telnyx_payload(body)
    logger.info("Received Telnyx webhook event_type=%s call_control_id=%s", event_type, call_control_id)

    if event_type == "call.recording.saved":
        asyncio.create_task(_handle_recording_saved(payload))
        return {"received": True, "event_type": event_type, "action": "download_recording"}

    if event_type != "call.initiated":
        return {"received": True, "event_type": event_type}

    if not call_control_id:
        raise HTTPException(status_code=400, detail="Missing call_control_id in Telnyx webhook payload")

    stream_url = _derive_telnyx_stream_url(request)
    command_id = f"answer-{event_id or call_control_id}"
    asyncio.create_task(_answer_call_and_start_stream(call_control_id, command_id, stream_url))
    return {"received": True, "action": "answer_with_stream", "call_control_id": call_control_id, "stream_url": stream_url}


@app.websocket("/media")
async def media(websocket: WebSocket):
    await websocket.accept()
    relay_task: Optional[asyncio.Task] = None

    try:
        while True:
            text = await websocket.receive_text()
            event = json.loads(text)
            event_type = event.get("event")

            if event_type == "start":
                if STREAM_START_DELAY_MS > 0:
                    await asyncio.sleep(STREAM_START_DELAY_MS / 1000.0)
                if relay_task and not relay_task.done():
                    relay_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await relay_task
                relay_task = asyncio.create_task(relay_tts_sequence(websocket))
            elif event_type == "media":
                continue
            elif event_type == "stop":
                break
    except WebSocketDisconnect:
        logger.info("Telnyx media websocket disconnected")
    except Exception:
        logger.exception("Error in /media handler")
        with contextlib.suppress(Exception):
            await websocket.close(code=1011)
    finally:
        if relay_task and not relay_task.done():
            relay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await relay_task


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
