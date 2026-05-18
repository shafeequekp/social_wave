from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        print(request.url.path)
        print('yesssssssssssssss')

        response = await call_next(request)

        return response
