#!/usr/bin/env python3
"""Verify a Liyagent audit evidence bundle with no access to the instance.

An evidence bundle (Audit Log -> Evidence bundle, or GET
/api/audit/export?fmt=bundle) is a zip of the hash-chained audit log
(audit.jsonl), any sealed archive segments (archive/*.jsonl.gz), the frozen
agents' evidence files (evidence/) and a manifest (manifest.json) that names
every file's sha256, the row count, the chain head and the checkpoints.

This script checks, on its own:

* the Ed25519 attestation on the manifest — and so, through the hashes the
  manifest names, everything in the bundle — against the instance's
  published audit signing keys (GET /api/audit/signing-key, or
  /.well-known/liyagent-audit-key.json, saved as JSON and passed with
  --keys) or a pinned key fingerprint (--fingerprint);
* the hash chain: every row's hash, every row linking to the one before
  it, ids ascending, archive segments continuing each other from the
  genesis hash, and the chain passing through the checkpoint anchored
  outside the database;
* the manifest's claims: the rows file's sha256 and count, the chain head,
  the checkpoints, and each evidence file's sha256.

What it cannot check: the HMAC signatures on checkpoints, segment seals and
redaction tombstones, made with a key only the instance holds. A row an
erasure redacted in place is therefore reported "unverified" here, as the
instance's own verifier reports it without its key; run
``python -m ticketiq.cli audit verify --local-key`` on the host for those.

Needs Python 3.9+ and the ``cryptography`` package; nothing else.

Usage:
    python verify_audit_bundle.py bundle.zip --keys audit-keys.json
    python verify_audit_bundle.py bundle.zip --fingerprint <sha256 hex>
    python verify_audit_bundle.py bundle.zip --json

Exit codes:
    0  intact, and signed by a published (or pinned) key
    2  a finding: altered, incomplete, or signed by a key that is not trusted
    3  intact and the signature verifies, but against the key the bundle
       carries — no published keys or fingerprint were given to trust it by
    1  the bundle or the keys file could not be read
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from typing import Any, Iterable

BUNDLE_FORMAT = "ticketiq-audit-bundle"
SEGMENT_FORMAT = "ticketiq-audit-segment"
MANIFEST_FILE = "manifest.json"
ROWS_FILE = "audit.jsonl"
GENESIS = "0" * 64
HASHED_FIELDS = ("id", "ts", "action", "actor", "detail")
CHECKPOINT_ACTION = "audit.checkpoint"
REDACTED_KEY = "_redacted"
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_LISTED = 200


# ---- the instance's byte forms, reproduced ----

def canonical(value: Any) -> bytes:
    """Sorted keys, no whitespace, ASCII escapes: the one form the instance
    hashes and signs."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def row_hash(row: dict[str, Any], prev_hash: str) -> str:
    body = {k: row.get(k) for k in HASHED_FIELDS}
    body["id"] = int(body["id"])
    body["prev_hash"] = prev_hash
    return hashlib.sha256(canonical(body)).hexdigest()


def _b64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _when(value: Any) -> datetime | None:
    try:
        got = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return got if got.tzinfo else got.replace(tzinfo=timezone.utc)


# ---- the report ----

class Report:
    def __init__(self) -> None:
        self.findings: list[dict[str, Any]] = []
        self.count = 0

    def find(self, kind: str, row_id: Any, message: str) -> None:
        self.count += 1
        if len(self.findings) < MAX_LISTED:
            self.findings.append({"kind": kind, "id": row_id, "message": message})


# ---- the attestation ----

def published_keys(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, dict) and isinstance(doc.get("keys"), list):
        doc = doc["keys"]
    elif isinstance(doc, dict):
        doc = [doc]
    return [k for k in (doc or []) if isinstance(k, dict) and isinstance(k.get("fingerprint"), str)]


def check_attestation(manifest: dict[str, Any], keys: list[dict[str, Any]] | None
                      ) -> dict[str, Any]:
    """valid / unpinned / invalid / untrusted / revoked / malformed / absent."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    att = manifest.get("attestation")
    out = {"state": "absent", "kid": "", "fingerprint": "",
           "detail": "the bundle carries no Ed25519 attestation (made before attestations "
                     "existed, or stripped)"}
    if att is None:
        return out
    if not (isinstance(att, dict) and att.get("alg") == "Ed25519"
            and all(isinstance(att.get(k), str) for k in ("public_key", "sig", "fingerprint"))):
        return {**out, "state": "malformed", "detail": "the attestation cannot be read"}
    out.update(kid=str(att.get("kid") or ""), fingerprint=att["fingerprint"])
    try:
        raw, sig = _b64url(att["public_key"]), _b64url(att["sig"])
    except (ValueError, TypeError):
        return {**out, "state": "malformed", "detail": "the attestation is not base64url"}
    if hashlib.sha256(raw).hexdigest() != att["fingerprint"]:
        return {**out, "state": "malformed",
                "detail": "the attestation's fingerprint is not its key's"}
    body = {k: v for k, v in manifest.items() if k not in ("signature", "attestation")}
    try:
        Ed25519PublicKey.from_public_bytes(raw).verify(sig, canonical(body))
    except (InvalidSignature, ValueError):
        return {**out, "state": "invalid",
                "detail": "the manifest's Ed25519 signature does not verify — the bundle was "
                          "altered after it was signed"}
    if keys is None:
        return {**out, "state": "unpinned",
                "detail": f"the signature verifies against the key the bundle carries "
                          f"(fingerprint {att['fingerprint']}); pass --keys or --fingerprint "
                          "to check that key is the instance's"}
    match = next((k for k in keys if k["fingerprint"] == att["fingerprint"]), None)
    if match is None:
        return {**out, "state": "untrusted",
                "detail": "signed by a key the published keys you gave do not list"}
    if match.get("status") == "revoked":
        return {**out, "state": "revoked",
                "detail": f"signed by key {match.get('kid')}, which the instance revoked at "
                          f"{match.get('revoked_at')} ({match.get('revoke_reason') or 'no reason given'})"}
    made = _when(manifest.get("created_at"))
    start, end = _when(match.get("valid_from")), _when(match.get("valid_until"))
    if made is None or (start and made < start) or (end and made > end):
        return {**out, "state": "untrusted",
                "detail": f"the bundle is dated {manifest.get('created_at')}, outside key "
                          f"{match.get('kid')}'s validity ({match.get('valid_from')} to "
                          f"{match.get('valid_until') or 'now'})"}
    return {**out, "state": "valid",
            "detail": f"signed by key {match.get('kid') or match['fingerprint'][:16]}"}


# ---- the chain ----

class Chain:
    """Walks rows in order; records every break as a finding."""

    def __init__(self, report: Report, anchor: Any) -> None:
        self.r = report
        self.expected: str | None = GENESIS
        self.last_id: int | None = None
        self.head: str | None = None
        self.rows = 0
        self.checkpoints = 0
        self.redacted = 0
        self.anchor = anchor if (isinstance(anchor, dict) and isinstance(anchor.get("id"), int)
                                 and isinstance(anchor.get("row_hash"), str)) else None
        self.anchor_state = "pending" if self.anchor else ""

    def resume(self, prev_hash: Any, last_id: Any) -> None:
        self.expected = prev_hash
        self.last_id = last_id if isinstance(last_id, int) else self.last_id
        if self.anchor_state == "pending" and isinstance(last_id, int) \
                and self.anchor["id"] <= last_id:
            self.anchor_state = "archived"

    def _anchor_at(self, rid: int, stated: Any) -> None:
        if rid == self.anchor["id"] and stated == self.anchor["row_hash"]:
            self.anchor_state = "matched"
            return
        self.anchor_state = "broken"
        self.r.find("anchor", self.anchor["id"],
                    f"the chain no longer passes through checkpoint #{self.anchor['id']}, "
                    "anchored outside the database — the history before it was rewritten")

    def feed(self, row: Any, where: str) -> None:
        if not isinstance(row, dict) or not isinstance(row.get("id"), int):
            self.r.find("edited", None, f"{where} holds a line that is not an audit row")
            return
        rid = row["id"]
        if self.last_id is not None and rid <= self.last_id:
            self.r.find("reordered", rid, f"#{rid} appears after #{self.last_id}")
        prev, stated = row.get("prev_hash"), row.get("row_hash")
        if not prev or not stated:
            self.r.find("unchained", rid, f"#{rid} carries no hash")
        else:
            if self.expected is not None and prev != self.expected:
                at = f"#{self.last_id}" if self.last_id is not None else "the start of the chain"
                self.r.find("missing", rid, f"#{rid} does not link to {at} — a row was "
                                            "deleted, inserted or moved here")
            detail = row.get("detail")
            red = detail.get(REDACTED_KEY) if isinstance(detail, dict) else None
            if isinstance(red, dict):
                self.redacted += 1
                if red.get("row_hash") != stated:
                    self.r.find("edited", rid, f"#{rid}'s redaction tombstone names a hash "
                                               "the row was not written with")
                else:
                    self.r.find("unverified", rid, f"#{rid} was redacted in place (an erasure); "
                                                   "its tombstone is signed with the instance's "
                                                   "key, which this check does not have")
            elif row_hash(row, prev) != stated:
                self.r.find("edited", rid, f"#{rid} was changed after it was written — its "
                                           "content no longer matches its hash")
        if row.get("action") == CHECKPOINT_ACTION:
            self.checkpoints += 1
            d = row.get("detail") if isinstance(row.get("detail"), dict) else {}
            if d.get("head_hash") != row.get("prev_hash"):
                self.r.find("checkpoint", rid, f"checkpoint #{rid} signed a different chain "
                                               "head — the history before it was rewritten")
        if self.anchor_state == "pending" and rid >= self.anchor["id"]:
            self._anchor_at(rid, stated)
        self.expected, self.last_id, self.head = stated, rid, stated
        self.rows += 1

    def finish(self) -> None:
        if self.anchor_state == "pending":
            self._anchor_at(-1, None)


def _read_segment(data: bytes) -> tuple[dict[str, Any], list[Any]]:
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as g:
        text = g.read(MAX_FILE_BYTES + 1)
    if len(text) > MAX_FILE_BYTES:
        raise ValueError("it unpacks to more than any segment the instance writes")
    lines = text.decode("ascii").splitlines()
    header = json.loads(lines[0]) if lines else {}
    if header.get("format") != SEGMENT_FORMAT:
        raise ValueError("not an audit archive segment")
    return header, [json.loads(x) for x in lines[1:] if x]


def _lines(data: Iterable[bytes]) -> Iterable[tuple[int, Any]]:
    for n, raw in enumerate(data, 1):
        line = raw.strip()
        if not line:
            continue
        try:
            yield n, json.loads(line)
        except ValueError:
            yield n, None


def verify(path: str, keys: list[dict[str, Any]] | None) -> dict[str, Any]:
    report = Report()
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ValueError(f"not a readable zip file: {e}") from None
    with z:
        names = set(z.namelist())
        if MANIFEST_FILE not in names or ROWS_FILE not in names:
            raise ValueError("not an audit evidence bundle (no manifest.json / audit.jsonl)")
        if z.getinfo(MANIFEST_FILE).file_size > MAX_MANIFEST_BYTES:
            raise ValueError("manifest.json is larger than any bundle the instance issues")
        try:
            manifest = json.loads(z.read(MANIFEST_FILE))
        except ValueError:
            raise ValueError("manifest.json is not readable — altered or truncated") from None
        if not isinstance(manifest, dict) or manifest.get("format") != BUNDLE_FORMAT:
            raise ValueError("not an audit evidence bundle")

        att = check_attestation(manifest, keys)
        if att["state"] in ("invalid", "malformed", "untrusted", "revoked", "absent"):
            report.find("forged" if att["state"] in ("invalid", "malformed") else att["state"],
                        None, att["detail"])

        def section(name: str, kind: type, parent: dict[str, Any] = manifest) -> Any:
            value = parent.get(name)
            if value is None:
                return kind()
            if not isinstance(value, kind):
                report.find("manifest", None, f"the manifest's {name!r} is malformed")
                return kind()
            return value

        chain = Chain(report, manifest.get("anchor"))
        archive = section("archive", dict)
        files = section("files", dict, archive)
        segments = sorted((s for s in section("segments", list, archive)
                           if isinstance(s, dict) and isinstance(s.get("first_id"), int)),
                          key=lambda s: s["first_id"])
        for digest in section("missing", list, archive):
            report.find("missing", None, f"archive segment {str(digest)[:12]}… was sealed but "
                                         "missing when this bundle was made")
        expected = GENESIS
        included = 0
        for seg in segments:
            first, last = seg.get("first_id"), seg.get("last_id")
            if seg.get("intact") is not True:
                report.find("archived-broken", first, f"archive segment #{first}–#{last} was "
                                                      "sealed with a broken chain")
            if seg.get("first_prev_hash") != expected:
                report.find("missing", first, f"archive segment #{first}–#{last} does not "
                                              "continue the one before it")
            expected = seg.get("last_hash")
            name = files.get(seg.get("digest") or "")
            if name and name in names and z.getinfo(name).file_size <= MAX_FILE_BYTES:
                data = z.read(name)
                if hashlib.sha256(data).hexdigest() != seg.get("digest"):
                    report.find("edited", first, f"archive file {name} is not the segment "
                                                 "that was sealed")
                try:
                    header, rows = _read_segment(data)
                except Exception as e:  # noqa: BLE001 - any unreadable file is a finding
                    report.find("edited", first, f"archive file {name} cannot be read ({e})")
                    header, rows = {}, []
                for row in rows:
                    chain.feed(row, name)
                if len(rows) != seg.get("count") or header.get("last_hash") != seg.get("last_hash"):
                    report.find("edited", first, f"archive file {name} does not hold the rows "
                                                 "its seal names")
                included += 1
            chain.resume(seg.get("last_hash"), last)
        archived_rows, archived_cps = chain.rows, chain.checkpoints

        sha = hashlib.sha256()
        with z.open(ROWS_FILE) as fh:
            def read() -> Iterable[bytes]:
                for raw in fh:
                    sha.update(raw)
                    yield raw
            for n, row in _lines(read()):
                chain.feed(row, f"{ROWS_FILE} line {n}")
        chain.finish()
        live = chain.rows - archived_rows

        rows_meta, head = section("rows", dict), section("chain", dict)
        if sha.hexdigest() != rows_meta.get("sha256"):
            report.find("manifest", None, f"{ROWS_FILE} is not the file this bundle was "
                                          "issued with")
        if live != rows_meta.get("count"):
            report.find("manifest", None, f"the manifest lists {rows_meta.get('count')} rows "
                                          f"but {ROWS_FILE} holds {live}")
        if live and (chain.last_id != head.get("head_id") or chain.head != head.get("head_hash")):
            report.find("missing", chain.last_id, "the chain does not end at the head the "
                                                  "manifest names — rows were removed from "
                                                  "the end")
        listed = len(section("checkpoints", list))
        if listed != chain.checkpoints - archived_cps:
            report.find("manifest", None, f"the manifest lists {listed} checkpoints but the "
                                          f"rows hold {chain.checkpoints - archived_cps}")
        evidence = section("evidence", dict)
        ev_files = section("files", dict, evidence)
        for name, digest in sorted(ev_files.items()):
            if name not in names:
                report.find("missing", None, f"evidence file {name} is listed but not in the "
                                             "bundle")
            elif z.getinfo(name).file_size > MAX_FILE_BYTES or \
                    hashlib.sha256(z.read(name)).hexdigest() != digest:
                report.find("edited", None, f"evidence file {name} is not the file this bundle "
                                            "was issued with")
        for name in sorted(n for n in names if n.startswith("evidence/")
                           and not n.endswith("/") and n not in ev_files):
            report.find("edited", None, f"evidence file {name} is not listed in the manifest "
                                        "— added after the bundle was issued")
    return {"ok": report.count == 0, "trusted": att["state"] == "valid",
            "attestation": att, "rows": live, "archived_rows_checked": archived_rows,
            "head_id": chain.last_id,
            "head_hash": chain.head, "checkpoints": chain.checkpoints,
            "redactions": chain.redacted,
            "archive": {"segments": len(segments), "included": included},
            "anchor": chain.anchor_state or None,
            "created_at": manifest.get("created_at"), "generator": manifest.get("generator"),
            "finding_count": report.count, "findings": report.findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify a Liyagent audit evidence bundle offline.")
    ap.add_argument("bundle")
    ap.add_argument("--keys", metavar="FILE",
                    help="the instance's published audit signing keys, as JSON (GET "
                         "/api/audit/signing-key or /.well-known/liyagent-audit-key.json)")
    ap.add_argument("--fingerprint", action="append", default=[], metavar="HEX",
                    help="trust the key with this sha256 fingerprint (repeatable)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)
    keys: list[dict[str, Any]] | None = None
    if args.keys:
        try:
            with open(args.keys, encoding="utf-8") as fh:
                keys = published_keys(json.load(fh))
        except (OSError, ValueError) as e:
            print(f"{args.keys}: cannot be read as JSON ({e})", file=sys.stderr)
            return 1
    if args.fingerprint:
        keys = (keys or []) + [{"fingerprint": f.strip().lower().replace(":", ""),
                                "kid": "pinned"} for f in args.fingerprint]
    try:
        out = verify(args.bundle, keys)
    except ValueError as e:
        print(f"{args.bundle}: {e}", file=sys.stderr)
        return 1
    code = 2 if not out["ok"] else (0 if out["trusted"] else 3)
    if args.json:
        print(json.dumps(out, indent=2))
        return code
    att = out["attestation"]
    print(f"bundle       {args.bundle}")
    print(f"issued       {out['created_at'] or '?'} by {out['generator'] or '?'}")
    print(f"rows         {out['rows']:,} live, {out['archived_rows_checked']:,} archived "
          f"checked; head #{out['head_id']} {str(out['head_hash'] or '')[:16]}")
    print(f"archive      {out['archive']['segments']} segment(s), "
          f"{out['archive']['included']} included")
    print(f"checkpoints  {out['checkpoints']} (their HMAC needs the instance's key)")
    print(f"signature    {att['state']}: {att['detail']}")
    if code == 0:
        print("result       INTACT — signed by the instance's published key")
    elif code == 3:
        print("result       INTACT, SIGNER NOT PINNED — compare the fingerprint above with "
              "the instance's published audit keys")
    else:
        print(f"result       FAILED — {out['finding_count']} finding(s)")
        for f in out["findings"]:
            print(f"  {f['kind']:<12} {f['message']}")
        if out["finding_count"] > len(out["findings"]):
            print(f"  … and {out['finding_count'] - len(out['findings'])} more")
    return code


if __name__ == "__main__":
    sys.exit(main())
