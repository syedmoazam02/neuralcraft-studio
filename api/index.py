import sys
from pathlib import Path

# Add the project root directory to sys.path so modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run import app


class VercelPathMiddleware:
    """Normalize request paths when Vercel rewrites requests to serverless functions."""

    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            for prefix in ("/api/index.py", "/api/index", "/api"):
                if path == prefix:
                    scope["path"] = "/"
                    break
                elif path.startswith(prefix + "/"):
                    scope["path"] = path[len(prefix):]
                    break
        await self.inner_app(scope, receive, send)


# Export the wrapped ASGI app instance for Vercel
app = VercelPathMiddleware(app)
