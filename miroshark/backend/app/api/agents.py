"""
Agent-identity API — Know Your Agent (KYA) verification endpoints.

- GET  /api/agents/<did>/pubkey     -> returns the agent's ed25519 public key
                                       (decoded from the DID itself, no DB lookup needed)
- POST /api/verify                  -> verifies a {did, payload, signature} tuple
                                       so downstream consumers don't need to bundle
                                       an ed25519 library to validate MiroShark
                                       attestations.
"""

import traceback

from flask import Blueprint, jsonify, request

from ..services.agent_credentials import (
    DID_PREFIX,
    SimulationKeyring,
    did_to_pubkey_bytes,
    pubkey_to_did,
    verify_signature,
)
from ..utils.logger import get_logger

logger = get_logger("miroshark.api.agents")

agents_bp = Blueprint("agents", __name__)
verify_bp = Blueprint("verify", __name__)


@agents_bp.route("/<path:did>/pubkey", methods=["GET"])
def get_agent_pubkey(did: str):
    """Return the ed25519 public key for a MiroShark agent DID.

    The pubkey is embedded in the DID itself, so this is a pure decoding
    operation that succeeds for every well-formed DID ever minted by this
    service — no database lookup, no simulation state required.
    """
    try:
        if not did.startswith(DID_PREFIX):
            return jsonify({
                "success": False,
                "error": f"expected DID to start with {DID_PREFIX!r}",
            }), 400

        raw = did_to_pubkey_bytes(did)

        # Opportunistic metadata: if we happen to know which simulation this
        # agent belongs to (key cached in-memory), include a redacted pointer.
        cred = SimulationKeyring.find_credential_by_did(did)
        known_simulation_id = None
        if cred is not None:
            for sim_id, other_ring in SimulationKeyring._cache.items():
                if other_ring.get(cred.agent_id) is cred:
                    known_simulation_id = sim_id
                    break

        return jsonify({
            "success": True,
            "did": did,
            "public_key_b58": did[len(DID_PREFIX):],
            "public_key_length_bytes": len(raw),
            "algorithm": "ed25519",
            "known_simulation_id": known_simulation_id,
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:  # pragma: no cover
        logger.error("pubkey lookup failed for did=%s: %s\n%s", did, e, traceback.format_exc())
        return jsonify({"success": False, "error": "internal_error"}), 500


@verify_bp.route("", methods=["POST"])
def verify_attestation():
    """Verify an ed25519 signature produced by a MiroShark agent DID.

    Request body:
        {
            "did": "did:miroshark:...",
            "payload": <any JSON>,
            "signature": "ed25519:<base64url>"
        }

    Response:
        { "valid": true|false, "did": "...", "algorithm": "ed25519" }
    """
    try:
        body = request.get_json(silent=True) or {}
        did = body.get("did")
        payload = body.get("payload")
        signature = body.get("signature")

        if not did or signature is None or payload is None:
            return jsonify({
                "valid": False,
                "error": "missing required field(s): did, payload, signature",
            }), 400

        try:
            pub_bytes = did_to_pubkey_bytes(did)
        except ValueError as e:
            return jsonify({"valid": False, "did": did, "error": str(e)}), 400

        valid = verify_signature(pub_bytes, payload, signature)

        # Round-trip sanity: rebuild the DID from the extracted pubkey. If this
        # doesn't match the input, the DID is malformed even before touching
        # the signature itself.
        rebuilt = pubkey_to_did(pub_bytes)
        return jsonify({
            "valid": bool(valid),
            "did": did,
            "did_matches_pubkey": rebuilt == did,
            "algorithm": "ed25519",
        })
    except Exception as e:
        logger.error("verify failed: %s\n%s", e, traceback.format_exc())
        return jsonify({"valid": False, "error": "internal_error"}), 500
