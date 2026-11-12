# M5 — Baseline LLM + RAG (expérimentale)

Ce répertoire reprend le **prototype technique sur une histoire fictive**, sans prétendre disposer d’un corpus alimentaire réel ni être intégré aux sorties M1–M4.

- LLM provisoire : `qwen2.5:1.5b`, Ollama local.
- Embeddings : `nomic-embed-text` ; stockage : ChromaDB.
- RAG : `ingest.py` découpe `story.txt`, `rag.py` effectue la récupération et `api.py` expose FastAPI.
- Le benchmark original et les 15 questions sont dans le dépôt de l’équipe [`example-rag`](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag) : fichiers `benchmark_ollama.py`, `benchmark_questions.json`, `benchmark_llm.pdf`.
- Une réussite sur des données fictives n’établit **aucune performance sur documents métier Givaudan**.

**Restant :** corpus alimentaire sourcé, connexion réelle aux sorties ML M1–M4, tests d’hallucinations/citations et comparatif LLMs.
