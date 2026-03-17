#!/usr/bin/env python3
"""
Example Webhook Receiver Server

A simple HTTP server that receives and validates Voice.ai webhooks for both:
- Event notifications (webhooks.events)
- inbound call webhook (webhooks.inbound_call)
- Webhook tools (webhooks.tools outbound API calls)

Usage:
    # Start the server (default port 8888)
    python webhook_receiver_server.py
    
    # Custom port
    python webhook_receiver_server.py --port 9000
    
    # With HMAC secret for event/inbound-call signature validation
    python webhook_receiver_server.py --secret your-webhook-secret
    
    # Expose via ngrok for testing deployed environments
    ngrok http 8888

The server will:
- Accept GET/POST/PUT/PATCH/DELETE on receiver paths
- Detect whether inbound request is an event webhook, inbound call webhook, or tool webhook
- Validate HMAC signatures for event and inbound call webhooks if --secret is provided
- Log metadata headers for tool webhooks:
  X-VoiceAI-Request-Id, X-VoiceAI-Tool-Name, X-VoiceAI-Agent-Id, X-VoiceAI-Call-Id
- Return JSON echo responses for event/tool webhooks
- Return example personalization data for inbound call webhooks
"""

import argparse
import hashlib
import hmac
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global config
webhook_secret: Optional[str] = None
received_requests: list = []


def _flatten_query_params(query_params: dict) -> dict:
    """Convert parse_qs output to a simpler dict."""
    flattened = {}
    for key, values in query_params.items():
        if len(values) == 1:
            flattened[key] = values[0]
        else:
            flattened[key] = values
    return flattened


def _mask_secret(value: Optional[str]) -> Optional[str]:
    """Mask sensitive header values in logs."""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-2:]}"


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhooks."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        pass  # Handled in request handlers
    
    def _send_json(self, status_code: int, payload: dict) -> None:
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2, default=str).encode())

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            return b""
        return self.rfile.read(content_length)

    def _parse_body(self, raw_body: bytes):
        """Parse body content; return parsed payload or text."""
        if not raw_body:
            return None, None
        content_type = self.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                return json.loads(raw_body.decode()), None
            except json.JSONDecodeError as e:
                return None, f"Invalid JSON: {e}"
        return raw_body.decode(errors='replace'), None

    def _determine_request_type(self, path: str, payload) -> str:
        """Classify inbound request as event/inbound_call/tool/unknown."""
        if self.headers.get('X-VoiceAI-Tool-Name'):
            return "tool"
        if path.startswith('/webhooks/tools'):
            return "tool"
        if path.startswith('/webhooks/inbound-call'):
            return "inbound_call"
        if isinstance(payload, dict) and 'event' in payload:
            return "event"
        if self.headers.get('X-Webhook-Signature') or self.headers.get('X-Webhook-Timestamp'):
            if isinstance(payload, dict) and {"agent_id", "call_id", "from_number", "to_number"}.issubset(payload.keys()):
                return "inbound_call"
            return "event"
        if isinstance(payload, dict) and {"agent_id", "call_id"}.issubset(payload.keys()):
            return "inbound_call"
        return "unknown"

    def _validate_signed_webhook(self, raw_body: bytes):
        """Validate event/inbound_call webhook signature when secret is configured."""
        if not webhook_secret:
            return None, None

        timestamp = self.headers.get('X-Webhook-Timestamp')
        signature = self.headers.get('X-Webhook-Signature')
        if not timestamp or not signature:
            return False, "Missing X-Webhook-Timestamp or X-Webhook-Signature headers"

        message = f"{timestamp}.{raw_body.decode(errors='replace')}"
        expected = hmac.new(
            webhook_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        is_valid = hmac.compare_digest(expected, signature)
        if not is_valid:
            return False, "Invalid webhook signature"
        return True, None

    def _log_received_request(
        self,
        request_type: str,
        method: str,
        path: str,
        query_params: dict,
        payload,
        signature_valid: Optional[bool]
    ) -> None:
        """Structured logging for inbound requests."""
        logger.info("=" * 60)
        logger.info(f"📨 RECEIVED {request_type.upper()} REQUEST")
        logger.info("=" * 60)
        logger.info(f"  Method: {method}")
        logger.info(f"  Path: {path}")
        if query_params:
            logger.info(f"  Query: {json.dumps(query_params)}")

        if request_type == "event":
            event_type = payload.get('event', 'unknown') if isinstance(payload, dict) else 'unknown'
            logger.info(f"  Event: {event_type}")
            if signature_valid is None:
                logger.info("  Signature: (not configured)")
            else:
                logger.info(f"  Signature: {'✓ valid' if signature_valid else '✗ invalid'}")
        elif request_type == "inbound_call":
            logger.info(f"  Agent ID: {payload.get('agent_id', '(missing)') if isinstance(payload, dict) else '(missing)'}")
            logger.info(f"  Call ID: {payload.get('call_id', '(missing)') if isinstance(payload, dict) else '(missing)'}")
            logger.info(f"  From: {payload.get('from_number', '(missing)') if isinstance(payload, dict) else '(missing)'}")
            logger.info(f"  To: {payload.get('to_number', '(missing)') if isinstance(payload, dict) else '(missing)'}")
            if signature_valid is None:
                logger.info("  Signature: (not configured)")
            else:
                logger.info(f"  Signature: {'✓ valid' if signature_valid else '✗ invalid'}")
        elif request_type == "tool":
            logger.info(f"  Tool Name: {self.headers.get('X-VoiceAI-Tool-Name', '(missing)')}")
            logger.info(f"  Request ID: {self.headers.get('X-VoiceAI-Request-Id', '(missing)')}")
            logger.info(f"  Agent ID: {self.headers.get('X-VoiceAI-Agent-Id', '(missing)')}")
            logger.info(f"  Call ID: {self.headers.get('X-VoiceAI-Call-Id', '(missing)')}")
            logger.info(f"  Authorization: {_mask_secret(self.headers.get('Authorization')) or '(none)'}")
            logger.info(f"  X-API-Key: {_mask_secret(self.headers.get('X-API-Key')) or '(none)'}")

        if payload is not None:
            try:
                payload_preview = json.dumps(payload, indent=2, default=str)
            except TypeError:
                payload_preview = str(payload)
            logger.info(f"  Payload: {payload_preview}")
        logger.info("-" * 60)

    def _handle_incoming_request(self) -> None:
        """Handle event, inbound_call, and tool webhooks in a generic way."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = _flatten_query_params(parse_qs(parsed_url.query, keep_blank_values=True))

        raw_body = b""
        if self.command in {"POST", "PUT", "PATCH", "DELETE"}:
            raw_body = self._read_body()

        payload, parse_error = self._parse_body(raw_body)
        if parse_error:
            logger.error(parse_error)
            self._send_json(400, {"error": parse_error})
            return

        if self.command == "GET":
            payload = query_params

        request_type = self._determine_request_type(path, payload)
        signature_valid = None

        # Signature validation applies to signed webhooks only.
        if request_type in {"event", "inbound_call"}:
            signature_valid, signature_error = self._validate_signed_webhook(raw_body)
            if webhook_secret and not signature_valid:
                logger.warning(f"❌ {request_type} webhook signature validation failed: {signature_error}")
                self._send_json(401, {"error": signature_error})
                return

        self._log_received_request(
            request_type=request_type,
            method=self.command,
            path=path,
            query_params=query_params,
            payload=payload,
            signature_valid=signature_valid
        )

        received_requests.append({
            "received_at": datetime.now().isoformat(),
            "request_type": request_type,
            "method": self.command,
            "path": path,
            "query": query_params,
            "headers": {k: v for k, v in self.headers.items()},
            "signature_valid": signature_valid,
            "payload": payload
        })

        if request_type == "inbound_call":
            response_payload = {
                "dynamic_variables": {
                    "source": "example-inbound-call-webhook",
                    "caller_number": payload.get("from_number") if isinstance(payload, dict) else "",
                    "dialed_number": payload.get("to_number") if isinstance(payload, dict) else "",
                },
            }
            self._send_json(200, response_payload)
            return

        self._send_json(200, {
            "status": "ok",
            "request_type": request_type,
            "method": self.command,
            "path": path,
            "tool_name": self.headers.get('X-VoiceAI-Tool-Name'),
            "event": payload.get('event') if isinstance(payload, dict) else None,
            "received_at": datetime.now().isoformat()
        })

    def do_GET(self):
        """Health/debug endpoints plus GET webhook-tool handling."""
        parsed_url = urlparse(self.path)
        has_tool_header = bool(self.headers.get('X-VoiceAI-Tool-Name'))

        if parsed_url.path == '/health' and not has_tool_header:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "requests_received": len(received_requests)
            }).encode())
        elif parsed_url.path == '/webhooks' and not has_tool_header and not parsed_url.query:
            # Debug endpoint: list received requests
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "count": len(received_requests),
                "requests": received_requests[-50:]  # Last 50
            }, indent=2, default=str).encode())
        else:
            self._handle_incoming_request()
    
    def do_POST(self):
        self._handle_incoming_request()

    def do_PUT(self):
        self._handle_incoming_request()

    def do_PATCH(self):
        self._handle_incoming_request()

    def do_DELETE(self):
        self._handle_incoming_request()


def main():
    global webhook_secret
    
    parser = argparse.ArgumentParser(
        description='Example Webhook Server for Voice.ai webhooks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8888,
        help='Port to listen on (default: 8888)'
    )
    parser.add_argument(
        '--secret', '-s',
        type=str,
        default=None,
        help='HMAC secret for signature validation'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    args = parser.parse_args()
    webhook_secret = args.secret
    
    # Print startup info
    print("=" * 60)
    print("  Voice.ai Example Webhook Server")
    print("=" * 60)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Secret: {'configured' if webhook_secret else 'not configured'}")
    print()
    print("  Endpoints:")
    print(f"    GET  /health       - Health check")
    print(f"    GET  /webhooks     - List received requests (debug; no query)")
    print(f"    Any  /webhooks...           - Receive event/tool webhooks")
    print(f"    POST /webhooks/inbound-call - Example inbound_call webhook")
    print()
    print("  Supported webhook methods:")
    print(f"    GET, POST, PUT, PATCH, DELETE")
    print()
    print("  To expose publicly, use ngrok:")
    print(f"    ngrok http {args.port}")
    print()
    print("  Configure your agent webhook URL(s) to:")
    print(f"    events/tools: http://localhost:{args.port}/webhooks")
    print(f"    inbound_call: http://localhost:{args.port}/webhooks/inbound-call")
    print("    (or your ngrok URL equivalents)")
    print("=" * 60)
    print()
    print("Waiting for webhooks...")
    print()
    
    # Start server
    server = HTTPServer((args.host, args.port), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        print(f"Total requests received: {len(received_requests)}")
        server.shutdown()


if __name__ == '__main__':
    main()
