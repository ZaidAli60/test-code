from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class ServerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length:
            if int(content_length) > self.max_bytes:
                return JSONResponse(status_code=413, content={"error": "Request too large"})
        
        body = await request.body()
        if len(body) > self.max_bytes:
            return JSONResponse(status_code=413, content={"error": "Request too large"})
        
        response = await call_next(request)
        return response