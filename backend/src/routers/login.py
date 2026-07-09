"""Login endpoints consumed by the frontend's login page.

Contract (see frontend/src/components/login/body.py):
- GET  C_login/get_session?param=<username> -> {"tok": "<token>"}
- POST C_login/login (form data: username, password, totp, _tok, client_type)
  -> 200 with an empty body on success (the frontend's HttpClient treats an empty,
     non-JSON 200 response as {"status_code": 200}), 401 on any credential/TOTP/token
     mismatch. A `session` cookie is set on success via SessionMiddleware.
"""

from fastapi import APIRouter, Form, HTTPException, Request, Response

from core.session_token import get_session_token, is_valid_session_token
from services.auth_service import authenticate

router = APIRouter(prefix="/C_login", tags=["login"])


def _client_ips(request: Request) -> tuple[str, str]:
    ip_1 = request.client.host if request.client else ""
    ip_2 = request.headers.get("x-forwarded-for", "")
    return ip_1, ip_2


@router.get("/get_session")
def get_session(request: Request, param: str) -> dict:
    """Issue a short-lived pre-auth token bound to the client IP and username."""
    ip_1, ip_2 = _client_ips(request)
    return {"tok": get_session_token(param, ip_1, ip_2)}


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp: str = Form(...),
    tok: str = Form(..., alias="_tok"),
    client_type: str = Form(None),
) -> Response:
    """Verify the pre-auth token, password, and TOTP, then start a session."""
    ip_1, ip_2 = _client_ips(request)
    if not is_valid_session_token(username, ip_1, ip_2, tok):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    authenticate(username, password, totp)

    request.session["username"] = username
    return Response(status_code=200)
