import base64
import json
from typing import Any, Dict, Optional

import streamlit as st

STATE_QUERY_KEY = "auth_state"


def _encode_state(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_state(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _minimal_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "grade": profile.get("grade"),
    }


def persist_state(token: Optional[str] = None, profile: Optional[Dict[str, Any]] = None) -> None:
    """Store token/profile in the URL so refreshes can restore session."""
    payload: Dict[str, Any] = {}
    token_value = token if token is not None else st.session_state.get("token")
    profile_value = profile if profile is not None else st.session_state.get("selected_profile")

    if token_value:
        payload["token"] = token_value
    if profile_value:
        payload["profile"] = _minimal_profile(profile_value)

    params = dict(st.query_params)
    if payload:
        params[STATE_QUERY_KEY] = _encode_state(payload)
    else:
        params.pop(STATE_QUERY_KEY, None)

    st.query_params.clear()
    st.query_params.update(params)


def hydrate_persisted_state() -> None:
    token = st.query_params.get(STATE_QUERY_KEY)
    if not token:
        return
    if isinstance(token, list):
        token = token[0]
    data = _decode_state(token)
    if not data:
        return

    if "token" in data and "token" not in st.session_state:
        st.session_state["token"] = data["token"]
    profile_data = data.get("profile")
    if profile_data and "selected_profile" not in st.session_state:
        st.session_state["selected_profile"] = profile_data


def clear_persisted_state() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("selected_profile", None)
    params = dict(st.query_params)
    if STATE_QUERY_KEY in params:
        params.pop(STATE_QUERY_KEY, None)
        st.query_params.clear()
        st.query_params.update(params)
