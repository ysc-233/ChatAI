"""Authentication utilities (JWT-based auth replaces legacy API Key)."""
# All API Key verification has been removed in favor of JWT auth.
# JWT auth functions are in app/core/auth.py.
# WebSocket auth is handled directly in ws.py via verify_ws_token().
