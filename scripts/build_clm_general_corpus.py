#!/usr/bin/env python3
"""Build a 200M-token general-language CLM pretraining mixture.

Design goals:
- exact 200,000,000 SentencePiece tokens (uint16 binary)
- broad + educational + mathematical + textbook/story + dialogue mixture
- no benchmark datasets deliberately mixed into training
- exact cross-source document deduplication
- source-level provenance and SHA256 manifest
- streaming download: never materialize the remote corpora in RAM

This script is meant to run on a GitHub Actions runner with internet access.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import unicodedata
from array import array
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Iterator, List

from datasets import load_dataset
import sentencepiece as spm

OUT = Path("clm_general_200m")
OUT.mkdir(parents=True, exist_ok=True)
SAMPLE = OUT / "tokenizer_sample.txt"
TOKENIZER_PREFIX = OUT / "clm_general_16k"
VOCAB_SIZE = 16_384
TOTAL_TARGET = 200_000_000
EOD = "<|eod|>"
USER = "<|user|>"
ASSISTANT = "<|assistant|>"

# Fixed before data is read. 200M total.
SOURCES = [
    {"name": "dclm", "dataset": "mlfoundations/dclm-baseline-1.0", "config": None, "split": "train", "target": 90_000_000, "kind": "text", "sample_chars": 8_000_000, "license": "CC-BY-4.0"},
    {"name": "fineweb_edu", "dataset": "HuggingFaceFW/fineweb-edu", "config": "sample-10BT", "split": "train", "target": 55_000_000, "kind": "text", "sample_chars": 8_000_000, "license": "ODC-By"},
    {"name": "openwebmath", "dataset": "open-web-math/open-web-math", "config": None, "split": "train", "target": 20_000_000, "kind": "text", "sample_chars": 4_000_000, "license": "ODC-By-1.0"},
    {"name": "cosmo_openstax", "dataset": "HuggingFaceTB/cosmopedia", "config": "openstax", "split": "train", "target": 5_000_000, "kind": "text", "sample_chars": 1_500_000, "license": "Apache-2.0"},
    {"name": "cosmo_khan", "dataset": "HuggingFaceTB/cosmopedia", "config": "khanacademy", "split": "train", "target": 5_000_000, "kind": "text", "sample_chars": 1_500_000, "license": "Apache-2.0"},
    {"name": "cosmo_stories", "dataset": "HuggingFaceTB/cosmopedia", "config": "stories", "split": "train", "target": 5_000_000, "kind": "text", "sample_chars": 1_500_000, "license": "Apache-2.0"},
    {"name": "ultrachat", "dataset": "HuggingFaceH4/ultrachat_200k", "config": None, "split": "train_sft", "target": 20_000_000, "kind": "chat", "sample_chars": 4_000_000, "license": "MIT"},
]
assert sum(s["target"] for s in SOURCES) == TOTAL_TARGET

_ws = re.compile(r"[ \t\f\v]+")
_blank = re.compile(r"\n{3,}")
_wordish = re.compile(r"[A-Za-z]{2,}")


def normalize_text(x: str) -> str:
    x = unicodedata.normalize("NFKC", x or "")
    x = x.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    x = "".join(ch if ch in "\n\t" or unicodedata.category(ch)[0] != "C" else " " for ch in x)
    x = "\n".join(_ws.sub(" ", line).strip() for line in x.splitlines())
    x = _blank.sub("\n\n", x).strip()
    return x


def quality_ok(text: str, kind: str) -> bool:
    if len(text) < (80 if kind == "chat" else 180):
        return False
    printable = sum(c.isprintable() or c in "\n\t" for c in text)
    if printable / max(1, len(text)) < 0.985:
        return False
    alpha = sum(c.isalpha() for c in text)
    if kind != "chat" and alpha / max(1, len(text)) < 0.38:
        return False
    if len(_wordish.findall(text)) < 20 and kind != "chat":
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 8:
        counts = Counter(lines)
        repeated = sum(n - 1 for n in counts.values() if n > 1)
        if repeated / len(lines) > 0.35:
            return False
    return True


def flatten_row(row: Dict, kind: str) -> str:
    if kind == "chat":
        msgs = row.get("messages") or []
        out: List[str] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "")).lower()
            content = normalize_text(str(m.get("content", "")))
            if not content:
                continue
            if role == "user":
                out.append(f"{USER}\n{content}")
            elif role == "assistant":
                out.append(f"{ASSISTANT}\n{content}")
            else:
                out.append(content)
        return "\n".join(out)
    return normalize_text(str(row.get("text", "")))


def stream_source(src: Dict) -> Iterable[Dict]:
    kwargs = dict(path=src["dataset"], split=src["split"], streaming=True)
    if src["config"] is not None:
        kwargs["name"] = src["config"]
    try:
        return load_dataset(**kwargs, trust_remote_code=False)
    except TypeError:
        kwargs.pop("trust_remote_code", None)
        return load_dataset(**kwargs)


def iter_chunks(text: str, max_chars: int = 24_000) -> Iterator[str]:
    if len(text) <= max_chars:
        yield text
        return
    paras = text.split("\n\n")
    buf: List[str] = []
    n = 0
    for p in paras:
        if not p:
            continue
        if len(p) > max_chars:
            if buf:
                yield "\n\n".join(buf)
                buf, n = [], 0
            for i in range(0, len(p), max_chars):
                piece = p[i:i + max_chars].strip()
                if piece:
                    yield piece
            continue
        extra = len(p) + (2 if buf else 0)
        if buf and n + extra > max_chars:
            yield "\n\n".join(buf)
            buf, n = [], 0
        buf.append(p)
        n += extra
    if buf:
        yield "\n\n".join(buf)


def collect_tokenizer_sample() -> None:
    print("[sample] collecting diverse tokenizer sample", flush=True)
    with SAMPLE.open("w", encoding="utf-8") as f:
        for src in SOURCES:
            chars = 0
            docs = 0
            for row in stream_source(src):
                text = flatten_row(row, src["kind"])
                if not quality_ok(text, src["kind"]):
                    continue
                for chunk in iter_chunks(text):
                    if not quality_ok(chunk, src["kind"]):
                        continue
                    remain = src["sample_chars"] - chars
                    if remain <= 0:
                        break
                    piece = chunk[:remain]
                    f.write(piece)
                    f.write(f"\n{EOD}\n")
                    chars += len(piece)
                    docs += 1
                    if chars >= src["sample_chars"]:
                        break
                if chars >= src["sample_chars"]:
                    break
            print(f"[sample] {src['name']}: {chars:,} chars from {docs:,} chunks", flush=True)
            if chars < src["sample_chars"] * 0.8:
                raise RuntimeError(f"Tokenizer sample source {src['name']} exhausted too early: {chars}")


def train_tokenizer() -> None:
    print("[tokenizer] training 16,384-piece BPE with byte fallback", flush=True)
    spm.SentencePieceTrainer.train(
        input=str(SAMPLE),
        model_prefix=str(TOKENIZER_PREFIX),
        vocab_size=VOCAB_SIZE,
        model_type="bpe",
        character_coverage=1.0,
        byte_fallback=True,
        normalization_rule_name="identity",
        split_digits=True,
        allow_whitespace_only_pieces=True,
        remove_extra_whitespaces=False,
        input_sentence_size=2_000_000,
        shuffle_input_sentence=True,
        unk_id=0,
        bos_id=-1,
        eos_id=-1,
        pad_id=-1,
        user_defined_symbols=[EOD, USER, ASSISTANT],
        train_extremely_large_corpus=True,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_u16(f, ids: List[int]) -> None:
    if not ids:
        return
    if max(ids) >= 65536:
        raise RuntimeError("Tokenizer ID exceeds uint16")
    a = array("H", ids)
    if sys.byteorder != "little":
        a.byteswap()
    a.tofile(f)


def build_binary_corpus() -> Dict:
    sp = spm.SentencePieceProcessor(model_file=str(TOKENIZER_PREFIX) + ".model")
    eod_id = sp.piece_to_id(EOD)
    print(f"[build] tokenizer pieces={sp.get_piece_size():,} eod_id={eod_id}", flush=True)

    seen_hashes = set()
    manifest_sources = []
    grand = 0

    for src in SOURCES:
        target = int(src["target"])
        out_path = OUT / f"{src['name']}.u16"
        accepted_tokens = 0
        raw_rows = 0
        accepted_chunks = 0
        rejected_quality = 0
        rejected_duplicate = 0
        t0 = time.time()
        with out_path.open("wb") as fout:
            for row in stream_source(src):
                raw_rows += 1
                text = flatten_row(row, src["kind"])
                if not quality_ok(text, src["kind"]):
                    rejected_quality += 1
                    continue
                for chunk in iter_chunks(text):
                    if not quality_ok(chunk, src["kind"]):
                        rejected_quality += 1
                        continue
                    digest = hashlib.blake2b(chunk.encode("utf-8"), digest_size=16).digest()
                    if digest in seen_hashes:
                        rejected_duplicate += 1
                        continue
                    seen_hashes.add(digest)
                    ids = list(sp.encode(chunk, out_type=int))
                    ids.append(eod_id)
                    need = target - accepted_tokens
                    if len(ids) > need:
                        ids = ids[:need]
                    write_u16(fout, ids)
                    accepted_tokens += len(ids)
                    accepted_chunks += 1
                    if accepted_tokens >= target:
                        break
                if accepted_tokens >= target:
                    break
                if raw_rows % 10_000 == 0:
                    print(f"[build] {src['name']}: {accepted_tokens:,}/{target:,} tokens rows={raw_rows:,}", flush=True)

        if accepted_tokens != target:
            raise RuntimeError(f"{src['name']} exhausted at {accepted_tokens:,}, expected {target:,}")
        sec = time.time() - t0
        info = {
            "name": src["name"],
            "dataset": src["dataset"],
            "config": src["config"],
            "split": src["split"],
            "license": src["license"],
            "tokens": accepted_tokens,
            "raw_rows_seen": raw_rows,
            "accepted_chunks": accepted_chunks,
            "quality_rejections": rejected_quality,
            "exact_duplicate_rejections": rejected_duplicate,
            "file": out_path.name,
            "bytes": out_path.stat().st_size,
            "sha256": sha256_file(out_path),
            "seconds": round(sec, 3),
        }
        manifest_sources.append(info)
        grand += accepted_tokens
        print(f"[build] DONE {src['name']}: {accepted_tokens:,} tokens in {sec:.1f}s", flush=True)

    if grand != TOTAL_TARGET:
        raise RuntimeError(f"Grand total {grand:,} != {TOTAL_TARGET:,}")

    model_path = Path(str(TOKENIZER_PREFIX) + ".model")
    manifest = {
        "format": "CLM general corpus v1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tokens": grand,
        "token_dtype": "little-endian uint16",
        "vocab_size": sp.get_piece_size(),
        "tokenizer_model": model_path.name,
        "tokenizer_sha256": sha256_file(model_path),
        "document_separator": EOD,
        "mixture_frozen_before_download": True,
        "benchmark_data_intentionally_added": False,
        "sources": manifest_sources,
        "notes": [
            "Training text is streamed from public Hugging Face datasets by GitHub Actions.",
            "Each source is capped to a fixed SentencePiece-token quota; quotas sum to exactly 200M.",
            "Documents are normalized and exact-deduplicated across sources before tokenization.",
            "No evaluation benchmark (e.g. GSM8K/MMLU/ARC) is intentionally included as a training source.",
            "Web corpora can still contain incidental benchmark-like material; downstream benchmark evaluation must run an explicit contamination scan."
        ]
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "CLM GENERAL 200M\n"
        "================\n"
        "Exactly 200,000,000 tokenizer IDs across the *.u16 source files.\n"
        "Use clm_general_16k.model to encode/decode. IDs are uint16 little-endian.\n"
        "Do not concatenate sources in giant source blocks during training: shuffle fixed-size blocks\n"
        "across sources according to the manifest mixture, preserving local token order inside blocks.\n",
        encoding="utf-8",
    )
    try:
        SAMPLE.unlink()
    except FileNotFoundError:
        pass
    return manifest


def main() -> None:
    t0 = time.time()
    print("[config] frozen mixture:", flush=True)
    for s in SOURCES:
        print(f"  {s['name']:18s} {s['target']:>12,} ({100*s['target']/TOTAL_TARGET:5.1f}%)", flush=True)
    collect_tokenizer_sample()
    train_tokenizer()
    manifest = build_binary_corpus()
    print(json.dumps({"total_tokens": manifest["total_tokens"], "elapsed_seconds": round(time.time()-t0, 2)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
