"""Benchmark reproductible de LLM Ollama sur le RAG example-rag (G22 Auralis).

"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import statistics
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import api
import config
import rag

ROOT = Path(__file__).resolve().parent


def normalize(value: str) -> str:
    s = unicodedata.normalize("NFD", value.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def approx_match(answer: str, testcase: dict) -> bool:
    """Heuristique de présence des mots attendus, PAS une note de vérité."""
    a = normalize(answer)
    if testcase["absent"]:
        signals = (
            "ne precise pas", "n'est pas precise", "pas precise", "pas indique",
            "pas mentionne", "n'en parle pas", "ne dit pas", "ne donne pas",
            "on ne sait pas", "je ne sais pas", "impossible de savoir",
            "aucune information", "aucune date", "ne peut pas savoir",
            "aucun detail", "n'est pas indique", "n'est pas mentionne",
            "information n'est pas", "non specifie", "pas specifie",
        )
        return any(s in a for s in signals)
    return all(any(normalize(term) in a for term in group) for group in testcase["required_groups"])


def number(resp, field, default=0):
    val = getattr(resp, field, None)
    if val is None and isinstance(resp, dict):
        val = resp.get(field, default)
    return val if val is not None else default


def get_answer(resp) -> str:
    msg = getattr(resp, "message", None)
    if msg is None and isinstance(resp, dict):
        msg = resp.get("message", {})
    if isinstance(msg, dict):
        return (msg.get("content") or "").strip()
    return (getattr(msg, "content", "") or "").strip()


def get_thinking(resp) -> str:
    msg = getattr(resp, "message", None)
    if msg is None and isinstance(resp, dict):
        msg = resp.get("message", {})
    if isinstance(msg, dict):
        return msg.get("thinking") or ""
    return getattr(msg, "thinking", "") or ""


def chat_call(client, model, messages, options, think):
    """Appel Ollama ; think=False coupe le mode reflexion (Qwen3.5...).
    Les modeles sans mode reflexion (qwen2.5...) refusent le parametre : on relance sans."""
    kwargs = {} if think is None else {"think": think}
    try:
        return client.chat(model=model, messages=messages, options=options, **kwargs)
    except Exception as exc:
        if kwargs and "think" in str(exc).lower():
            return client.chat(model=model, messages=messages, options=options)
        raise


def gpu_info() -> str:
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return p.stdout.strip() if p.returncode == 0 else "Non detecte / CPU"
    except (OSError, subprocess.TimeoutExpired):
        return "Non detecte / CPU"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Ollama du RAG example-rag")
    parser.add_argument("--models", nargs="+", default=["qwen2.5:1.5b"],
                        help="Noms EXACTS des modeles Ollama installes")
    parser.add_argument("--questions", default="benchmark_questions.json")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--out", default="benchmark_results")
    parser.add_argument("--think", choices=["off", "on", "default"], default="off",
                        help="Mode reflexion des modeles qui le gerent (defaut : off, usage reel de Sillage)")
    args = parser.parse_args()
    if args.repeats < 1 or args.top_k < 1:
        parser.error("--repeats et --top-k doivent etre >= 1")

    questions = json.loads((ROOT / args.questions).read_text(encoding="utf-8"))
    collection = rag.get_collection()
    if collection.count() == 0:
        raise SystemExit("ChromaDB est vide. Execute d'abord : python ingest.py")
    corpus_model = (collection.metadata or {}).get("embed_model")
    if corpus_model and corpus_model != config.EMBED_MODEL:
        raise SystemExit(f"Embeddings incompatibles: base={corpus_model}, env={config.EMBED_MODEL}")

    think = {"off": False, "on": True, "default": None}[args.think]
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "gpu": gpu_info(),
        "python": platform.python_version(),
        "ollama_host": config.OLLAMA_HOST,
        "embedding_model": config.EMBED_MODEL,
        "corpus_file": "story.txt",
        "chunks_indexed": collection.count(),
        "top_k": args.top_k,
        "temperature": 0.2,
        "num_ctx": args.num_ctx,
        "repeats": args.repeats,
        "think": args.think,
        "models": args.models,
        "note": "Correspondance automatique = indicateur approximatif, a verifier humainement."
    }
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    # Les passages sont identiques pour chaque LLM : une seule recherche par question.
    contexts = {}
    print(f"Index ChromaDB : {collection.count()} passages, embeddings : {config.EMBED_MODEL}")
    for q in questions:
        start = time.perf_counter()
        sources = api.retrieve(q["question"], args.top_k)
        retrieve_s = time.perf_counter() - start
        context = "\n\n---\n\n".join(f"[{s.chapter}]\n{s.text}" for s in sources)
        chapters = [s.chapter for s in sources]
        expected = q.get("expected_chapters", [])
        chapter_hit = (sum(any(c.startswith(e) for c in chapters) for e in expected) / len(expected)) if expected else None
        messages = [
            {"role": "system", "content": api.SYSTEM_PROMPT},
            {"role": "user", "content": f"Extraits de l'histoire :\n\n{context}\n\nQuestion : {q['question']}"},
        ]
        contexts[q["id"]] = (messages, retrieve_s, chapters, chapter_hit)

    client = rag._ollama
    rows = []
    fields = [
        "model", "test_id", "category", "question", "reference", "answer",
        "auto_keyword_match_approx", "manual_quality_0_2", "manual_faithfulness_0_2",
        "manual_unsupported_claims", "manual_notes", "expected_chapters",
        "retrieved_chapters", "retrieval_chapter_coverage", "retrieval_s",
        "generation_s", "total_s", "load_s", "prompt_tokens", "generated_tokens",
        "tokens_per_s", "thinking_characters", "repeat", "error",
    ]
    for model in args.models:
        print(f"\n=== {model} ===")
        # Prechauffage pour ne pas compter le chargement initial dans la latence chaude.
        warmup = contexts[questions[0]["id"]][0]
        try:
            chat_call(client, model, warmup,
                      {"temperature": 0.2, "num_ctx": args.num_ctx}, think)
        except Exception as exc:
            print(f"ERREUR prechauffage ({model}): {exc}")
            for q in questions:
                rows.append({"model": model, "test_id": q["id"], "category": q["category"],
                             "question": q["question"], "reference": q["reference"],
                             "error": f"Echec prechauffage: {exc}"})
            continue
        for q in questions:
            messages, retrieval_s, chapters, chapter_coverage = contexts[q["id"]]
            for repeat in range(1, args.repeats + 1):
                row = {
                    "model": model, "test_id": q["id"], "category": q["category"],
                    "question": q["question"], "reference": q["reference"],
                    "expected_chapters": "; ".join(q.get("expected_chapters", [])),
                    "retrieved_chapters": "; ".join(chapters),
                    "retrieval_chapter_coverage": "" if chapter_coverage is None else round(chapter_coverage, 3),
                    "retrieval_s": round(retrieval_s, 4), "repeat": repeat,
                    "manual_quality_0_2": "", "manual_faithfulness_0_2": "",
                    "manual_unsupported_claims": "", "manual_notes": "", "error": "",
                }
                try:
                    start = time.perf_counter()
                    response = chat_call(client, model, messages,
                                         {"temperature": 0.2, "num_ctx": args.num_ctx}, think)
                    generation_s = time.perf_counter() - start
                    answer = get_answer(response)
                    generated = number(response, "eval_count")
                    eval_ns = number(response, "eval_duration")
                    row.update({
                        "answer": answer,
                        "auto_keyword_match_approx": int(approx_match(answer, q)),
                        "generation_s": round(generation_s, 3),
                        "total_s": round(retrieval_s + generation_s, 3),
                        "load_s": round(number(response, "load_duration") / 1e9, 3),
                        "prompt_tokens": number(response, "prompt_eval_count"),
                        "generated_tokens": generated,
                        "tokens_per_s": round(generated / (eval_ns / 1e9), 2) if eval_ns else "",
                        "thinking_characters": len(get_thinking(response)),
                    })
                    print(f" {q['id']} #{repeat}: {generation_s:.2f}s | heuristic={row['auto_keyword_match_approx']}")
                except Exception as exc:
                    row["error"] = str(exc)
                    print(f" {q['id']} #{repeat}: ERREUR {exc}")
                rows.append(row)
        # Libere le modele, utile pour les petites VRAM Colab.
        try:
            subprocess.run(["ollama", "stop", model], capture_output=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass

    write_csv(out / "results.csv", rows, fields)
    summary = []
    for model in args.models:
        rs = [r for r in rows if r.get("model") == model and not r.get("error")]
        times = [float(r["generation_s"]) for r in rs if r.get("generation_s") is not None]
        speeds = [float(r["tokens_per_s"]) for r in rs if isinstance(r.get("tokens_per_s"), (float, int))]
        summary.append({
            "model": model, "success_count": len(rs),
            "attempted_count": len([r for r in rows if r.get("model") == model]),
            "heuristic_matches": sum(r.get("auto_keyword_match_approx", 0) for r in rs),
            "heuristic_match_rate": round(sum(r.get("auto_keyword_match_approx", 0) for r in rs) / len(rs), 3) if rs else "",
            "median_generation_s": round(statistics.median(times), 3) if times else "",
            "median_tokens_per_s": round(statistics.median(speeds), 2) if speeds else "",
            "note": "Heuristique de mots cles uniquement ; evaluer les reponses manuellement",
        })
    write_csv(out / "summary.csv", summary, list(summary[0]))
    print("\nFichiers crees :")
    print(" -", out / "results.csv")
    print(" -", out / "summary.csv")
    print(" -", out / "metadata.json")
    print("ATTENTION : completer les colonnes manual_* avant de conclure sur la qualite !")


if __name__ == "__main__":
    main()
