"""
Agent Credentials — ed25519 signing for Know Your Agent (KYA) attestations.

Mint a per-agent ed25519 keypair (plus a per-simulation "root" keypair), expose
canonical JSON / content-hash / sign / verify helpers, and persist keys inside a
simulation-scoped JSON file. Private keys stay inside the MiroShark process
boundary — they are written to disk only under the simulation's run-state
directory and never sent to Neo4j or included in API responses.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ..utils.logger import get_logger

logger = get_logger("miroshark.agent_credentials")


DID_PREFIX = "did:miroshark:"
SIGNATURE_PREFIX = "ed25519:"
ROOT_AGENT_ID = "_sim_root"
KEYRING_FILENAME = "agent_keys.json"


# ---------------------------------------------------------------------------
# Base58 (Bitcoin / Solana alphabet) — pure-Python implementation
# ---------------------------------------------------------------------------
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58_ALPHABET)}


def b58encode(data: bytes) -> str:
    if not data:
        return ""
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58_ALPHABET[r] + out
    # preserve leading zero bytes as leading '1'
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + out


def b58decode(s: str) -> bytes:
    if not s:
        return b""
    n = 0
    for ch in s:
        if ch not in _B58_INDEX:
            raise ValueError(f"invalid base58 character: {ch!r}")
        n = n * 58 + _B58_INDEX[ch]
    # count leading '1's -> leading zero bytes
    pad = 0
    for ch in s:
        if ch == "1":
            pad += 1
        else:
            break
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    return (b"\x00" * pad) + body


# ---------------------------------------------------------------------------
# Core key helpers
# ---------------------------------------------------------------------------
def _priv_to_bytes(priv: Ed25519PrivateKey) -> bytes:
    return priv.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )


def _pub_to_bytes(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)


def generate_keypair() -> Tuple[bytes, bytes]:
    """Return (private_key_bytes, public_key_bytes) — 32 bytes each."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return _priv_to_bytes(priv), _pub_to_bytes(pub)


def pubkey_to_did(pub_bytes: bytes) -> str:
    return DID_PREFIX + b58encode(pub_bytes)


def did_to_pubkey_bytes(did: str) -> bytes:
    if not did.startswith(DID_PREFIX):
        raise ValueError(f"expected did to start with {DID_PREFIX!r}, got {did!r}")
    raw = b58decode(did[len(DID_PREFIX):])
    if len(raw) != 32:
        raise ValueError(f"expected 32-byte ed25519 pubkey, got {len(raw)} bytes")
    return raw


def canonical_json_bytes(payload: Any) -> bytes:
    """Deterministic JSON serialization used for hashing and signing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(payload: Any) -> str:
    """sha256 of canonical JSON, returned as 'sha256:<hex>'."""
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def sign_bytes(priv_bytes: bytes, message: bytes) -> str:
    priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    sig = priv.sign(message)
    return SIGNATURE_PREFIX + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")


def sign_payload(priv_bytes: bytes, payload: Any) -> str:
    return sign_bytes(priv_bytes, canonical_json_bytes(payload))


def verify_signature(pub_bytes: bytes, message_or_payload: Any, signature: str) -> bool:
    """Verify an ed25519 signature. Accepts either a raw bytes message or a JSON-serializable payload."""
    if not signature.startswith(SIGNATURE_PREFIX):
        return False
    try:
        raw_sig = base64.urlsafe_b64decode(_pad_b64(signature[len(SIGNATURE_PREFIX):]))
    except Exception:
        return False
    if isinstance(message_or_payload, (bytes, bytearray)):
        msg = bytes(message_or_payload)
    else:
        msg = canonical_json_bytes(message_or_payload)
    try:
        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(raw_sig, msg)
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


def _pad_b64(s: str) -> str:
    return s + "=" * (-len(s) % 4)


# ---------------------------------------------------------------------------
# Per-simulation keyring (on-disk, sim-scoped)
# ---------------------------------------------------------------------------
@dataclass
class AgentCredential:
    agent_id: str  # string form; original is usually an int user_id
    did: str
    public_key_b58: str
    private_key_b64: str  # raw 32-byte key, base64url-encoded (no padding)
    created_at: str

    def public_bytes(self) -> bytes:
        return b58decode(self.public_key_b58)

    def private_bytes(self) -> bytes:
        return base64.urlsafe_b64decode(_pad_b64(self.private_key_b64))

    def public_dict(self) -> Dict[str, Any]:
        """Redacted view — never includes private key."""
        return {
            "agent_id": self.agent_id,
            "did": self.did,
            "public_key_b58": self.public_key_b58,
            "algorithm": "ed25519",
            "created_at": self.created_at,
        }


class SimulationKeyring:
    """Per-simulation keyring. Thread-safe, persisted to sim_dir/agent_keys.json."""

    _lock = threading.RLock()
    _cache: Dict[str, "SimulationKeyring"] = {}
    # Global DID index so /api/verify can resolve arbitrary DIDs across sims.
    _did_index: Dict[str, Tuple[str, str]] = {}  # did -> (simulation_id, agent_id)

    def __init__(self, simulation_id: str, sim_dir: str):
        self.simulation_id = simulation_id
        self.sim_dir = sim_dir
        self.path = os.path.join(sim_dir, KEYRING_FILENAME)
        self._creds: Dict[str, AgentCredential] = {}
        self._load()

    # --- Construction ------------------------------------------------------
    @classmethod
    def for_simulation(cls, simulation_id: str, sim_dir: str) -> "SimulationKeyring":
        with cls._lock:
            if simulation_id in cls._cache:
                return cls._cache[simulation_id]
            os.makedirs(sim_dir, exist_ok=True)
            ring = cls(simulation_id, sim_dir)
            cls._cache[simulation_id] = ring
            return ring

    @classmethod
    def lookup(cls, simulation_id: str) -> Optional["SimulationKeyring"]:
        with cls._lock:
            return cls._cache.get(simulation_id)

    # --- Persistence -------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning("failed to load keyring %s: %s", self.path, e)
            return
        for agent_id, entry in data.get("agents", {}).items():
            cred = AgentCredential(
                agent_id=str(agent_id),
                did=entry["did"],
                public_key_b58=entry["public_key_b58"],
                private_key_b64=entry["private_key_b64"],
                created_at=entry.get("created_at", _now_iso()),
            )
            self._creds[str(agent_id)] = cred
            SimulationKeyring._did_index[cred.did] = (self.simulation_id, str(agent_id))

    def _persist(self) -> None:
        payload = {
            "simulation_id": self.simulation_id,
            "created_at": _now_iso(),
            "agents": {
                aid: {
                    "did": c.did,
                    "public_key_b58": c.public_key_b58,
                    "private_key_b64": c.private_key_b64,
                    "created_at": c.created_at,
                }
                for aid, c in self._creds.items()
            },
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.path)

    # --- Minting -----------------------------------------------------------
    def mint(self, agent_id: Any) -> AgentCredential:
        """Mint a fresh ed25519 keypair for agent_id if one doesn't exist."""
        key = str(agent_id)
        with SimulationKeyring._lock:
            if key in self._creds:
                return self._creds[key]
            priv, pub = generate_keypair()
            cred = AgentCredential(
                agent_id=key,
                did=pubkey_to_did(pub),
                public_key_b58=b58encode(pub),
                private_key_b64=base64.urlsafe_b64encode(priv).rstrip(b"=").decode("ascii"),
                created_at=_now_iso(),
            )
            self._creds[key] = cred
            SimulationKeyring._did_index[cred.did] = (self.simulation_id, key)
            self._persist()
            return cred

    def mint_batch(self, agent_ids: List[Any]) -> Dict[str, AgentCredential]:
        out: Dict[str, AgentCredential] = {}
        with SimulationKeyring._lock:
            for aid in agent_ids:
                out[str(aid)] = self.mint(aid)
        return out

    def root_credential(self) -> AgentCredential:
        """Return (minting if absent) the per-simulation root credential."""
        return self.mint(ROOT_AGENT_ID)

    # --- Lookup ------------------------------------------------------------
    def get(self, agent_id: Any) -> Optional[AgentCredential]:
        return self._creds.get(str(agent_id))

    def all_credentials(self) -> Dict[str, AgentCredential]:
        # Copy so callers can't mutate internals.
        return dict(self._creds)

    # --- Convenience sign --------------------------------------------------
    def sign_for_agent(self, agent_id: Any, payload: Any) -> Optional[Dict[str, str]]:
        cred = self.get(agent_id)
        if not cred:
            return None
        return {
            "did": cred.did,
            "content_hash": content_hash(payload),
            "signature": sign_payload(cred.private_bytes(), payload),
        }

    # --- Class-level helpers ----------------------------------------------
    @classmethod
    def find_credential_by_did(cls, did: str) -> Optional[AgentCredential]:
        with cls._lock:
            entry = cls._did_index.get(did)
            if not entry:
                return None
            sim_id, agent_id = entry
            ring = cls._cache.get(sim_id)
            if not ring:
                return None
            return ring.get(agent_id)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
