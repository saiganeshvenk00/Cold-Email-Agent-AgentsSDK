import json
import os
from typing import Dict, Optional


STORE_PATH = os.environ.get("THREAD_STORE_PATH", "thread_store.json")


def _load_store() -> Dict:
    if not os.path.exists(STORE_PATH):
        return {"contacts": {}}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"contacts": {}}


def _save_store(store: Dict) -> None:
    directory = os.path.dirname(STORE_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def record_outbound_message(to_email: str, message_id: Optional[str], kind: str = "cold", relates_to: Optional[str] = None, references: Optional[str] = None) -> None:
    email = _normalize_email(to_email)
    if not email or not message_id:
        return
    store = _load_store()
    contacts = store.setdefault("contacts", {})
    contact = contacts.setdefault(email, {"outbound": [], "inbound": [], "last_outbound_message_id": None})
    contact["outbound"].append({
        "message_id": message_id,
        "kind": kind,
        "relates_to": relates_to,
        "references": references,
    })
    contact["last_outbound_message_id"] = message_id
    _save_store(store)


def record_inbound_message(from_email: str, message_id: Optional[str], references: Optional[str] = None) -> None:
    email = _normalize_email(from_email)
    if not email or not message_id:
        return
    store = _load_store()
    contacts = store.setdefault("contacts", {})
    contact = contacts.setdefault(email, {"outbound": [], "inbound": [], "last_outbound_message_id": None})
    contact["inbound"].append({
        "message_id": message_id,
        "references": references,
    })
    _save_store(store)


def get_last_outbound_message_id(email: str) -> Optional[str]:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None
    store = _load_store()
    try:
        return store["contacts"][email_norm].get("last_outbound_message_id")
    except KeyError:
        return None


def build_reply_headers(to_email: Optional[str] = None, inbound_message_id: Optional[str] = None, references: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if inbound_message_id:
        headers["In-Reply-To"] = inbound_message_id

    refs_tokens = []
    if references and isinstance(references, str):
        refs_tokens.append(references)
    elif to_email:
        original = get_last_outbound_message_id(to_email)
        if original:
            refs_tokens.append(original)
    if inbound_message_id:
        refs_tokens.append(inbound_message_id)
    if refs_tokens:
        # Avoid duplicates while preserving order
        seen = set()
        ordered = []
        for token in refs_tokens:
            if token and token not in seen:
                seen.add(token)
                ordered.append(token)
        headers["References"] = " ".join(ordered)
    return headers


