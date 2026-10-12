"""Compatibility shim for legacy imports that still use the project root config module."""

from backend.config import *  # noqa: F401,F403

# Re-export the active session helpers if older modules expect those names.
from backend.config import ACTIVE_CONTEXT, DEFAULT_SESSION, load_session, save_session  # noqa: F401
