from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitMiddleware:
    """Bound auth request bodies, including chunked requests without Content-Length."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        # CV uploads will get their own validated limit in phase 4.
        limit = 16 * 1024
        buffered = bytearray()
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                response = JSONResponse(
                    {"error": {"code": "BODY_TOO_LARGE", "message": "Request body too large"}},
                    status_code=413,
                )
                await response(scope, receive, send)
                return
            buffered.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        combined = bytes(buffered)
        consumed = False

        async def replay() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": combined, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
