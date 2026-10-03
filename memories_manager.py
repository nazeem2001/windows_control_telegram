import math
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


MEMORY_ROOT = Path("memories")
MEMORY_FILENAME = "conversation.md"
FACTS_HEADING_RE = re.compile(r"^# Facts & Preferences for (?P<name>.*)$")
FACT_RE = re.compile(r"^- \*\*(?P<key>.+?)\*\*: (?P<value>.*)$")
REMEMBER_PATTERNS = [
    re.compile(r"\bremember that (?P<fact>.+)", re.IGNORECASE),
    re.compile(r"\bplease remember (?P<fact>.+)", re.IGNORECASE),
    re.compile(r"\bremember (?P<fact>.+)", re.IGNORECASE),
    re.compile(r"\bi prefer (?P<fact>.+)", re.IGNORECASE),
    re.compile(r"\bmy preference is (?P<fact>.+)", re.IGNORECASE),
    re.compile(r"\bmy name is (?P<fact>.+)", re.IGNORECASE),
]


class UserMemory:
    """Markdown-backed per-user facts and conversation logs."""

    def __init__(self, memory_root=MEMORY_ROOT, model_name="all-MiniLM-L6-v2"):
        self.memory_root = Path(memory_root)
        self.model_name = model_name
        self._embedding_model = None
        self._embedding_available = None
        self._fact_index = {}

    def ensure_user_folder(self, chat_id, first_name=None):
        folder = self._folder(chat_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / MEMORY_FILENAME
        if not path.exists():
            display_name = (first_name or str(chat_id)).strip() or str(chat_id)
            path.write_text(self._template(display_name), encoding="utf-8")
        return folder

    def load_memory(self, chat_id):
        path = self._path(chat_id)
        if not path.exists():
            self.ensure_user_folder(chat_id)

        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        facts = {}
        in_log = False
        conversation_count = 0
        display_name = str(chat_id)

        for line in lines:
            heading = FACTS_HEADING_RE.match(line)
            if heading:
                display_name = heading.group("name").strip() or str(chat_id)
                continue
            if line.strip() == "## Conversation Log":
                in_log = True
                continue
            if in_log:
                if line.startswith("["):
                    conversation_count += 1
                continue
            match = FACT_RE.match(line)
            if match:
                facts[match.group("key")] = match.group("value")

        return {
            "facts": facts,
            "metadata": {
                "chat_id": str(chat_id),
                "display_name": display_name,
                "conversation_count": conversation_count,
                "memory_size": path.stat().st_size if path.exists() else 0,
                "path": str(path),
            },
        }

    def save_conversation(self, chat_id, sender, message, timestamp=None, first_name=None):
        self.ensure_user_folder(chat_id, first_name)
        timestamp = timestamp or datetime.now()
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        safe_message = str(message).replace("\r\n", "\n").replace("\r", "\n")
        safe_message = safe_message.replace("\n", "\n    ")
        with self._path(chat_id).open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {sender}: {safe_message}\n")

    def add_fact(self, chat_id, fact_text, first_name=None):
        self.ensure_user_folder(chat_id, first_name)
        key, value = self._fact_key_value(fact_text)
        data = self.load_memory(chat_id)
        facts = data["facts"]

        for existing_key in list(facts):
            if existing_key.lower() == key.lower():
                facts[existing_key] = value
                self._write_memory(chat_id, facts)
                self._reindex(chat_id, facts)
                return existing_key

        facts[key] = value
        self._write_memory(chat_id, facts)
        self._reindex(chat_id, facts)
        return key

    def remove_fact(self, chat_id, fact_key):
        data = self.load_memory(chat_id)
        facts = data["facts"]
        removed = None
        for key in list(facts):
            if key.lower() == fact_key.lower():
                removed = key
                del facts[key]
                break
        if removed is not None:
            self._write_memory(chat_id, facts)
            self._reindex(chat_id, facts)
        return removed

    def extract_facts_from_message(self, message):
        facts = []
        text = str(message).strip()
        for pattern in REMEMBER_PATTERNS:
            match = pattern.search(text)
            if match:
                fact = self._clean_fact(match.group("fact"))
                if fact:
                    facts.append(fact)
                break
        return list(dict.fromkeys(facts))

    def retrieve_relevant_facts(self, chat_id, query, top_k=5, min_score=0.2):
        data = self.load_memory(chat_id)
        facts = data["facts"]
        if not facts:
            return []
        if str(chat_id) not in self._fact_index:
            self._reindex(chat_id, facts)

        index = self._fact_index.get(str(chat_id), [])
        if not index:
            return []

        if self._load_embedding_model():
            query_vector = self._embedding_model.encode([query], normalize_embeddings=True)[0]
            scored = [
                (self._dot(query_vector, item["embedding"]), item["key"], item["value"])
                for item in index
            ]
        else:
            query_terms = self._terms(query)
            scored = [
                (self._lexical_score(query_terms, item["terms"]), item["key"], item["value"])
                for item in index
            ]

        return [
            {"key": key, "value": value, "score": score}
            for score, key, value in sorted(scored, reverse=True)[:top_k]
            if score >= min_score
        ]

    def get_stats(self, chat_id):
        return self.load_memory(chat_id)["metadata"] | {
            "facts_count": len(self.load_memory(chat_id)["facts"]),
            "embedding_backend": "sentence-transformers"
            if self._load_embedding_model()
            else "lexical fallback",
        }

    def clear_memory(self, chat_id):
        folder = self._folder(chat_id)
        if folder.exists():
            shutil.rmtree(folder)
        self._fact_index.pop(str(chat_id), None)

    def _folder(self, chat_id):
        safe_id = re.sub(r"[^A-Za-z0-9_.:-]", "_", str(chat_id))
        return self.memory_root / safe_id

    def _path(self, chat_id):
        return self._folder(chat_id) / MEMORY_FILENAME

    def _template(self, first_name):
        return f"# Facts & Preferences for {first_name}\n\n## Conversation Log\n\n"

    def _write_memory(self, chat_id, facts):
        data = self.load_memory(chat_id)
        path = self._path(chat_id)
        lines = path.read_text(encoding="utf-8").splitlines()
        log_index = next(
            (i for i, line in enumerate(lines) if line.strip() == "## Conversation Log"),
            len(lines),
        )
        log_lines = lines[log_index:] if log_index < len(lines) else ["## Conversation Log", ""]
        header = [f"# Facts & Preferences for {data['metadata']['display_name']}", ""]
        fact_lines = [f"- **{key}**: {value}" for key, value in sorted(facts.items())]
        content = "\n".join(header + fact_lines + [""] + log_lines).rstrip() + "\n"
        path.write_text(content, encoding="utf-8")

    def _fact_key_value(self, fact_text):
        fact = self._clean_fact(fact_text)
        if ":" in fact:
            key, value = fact.split(":", 1)
            return self._title_key(key), value.strip()
        words = fact.split()
        key = self._title_key(" ".join(words[:5]) if words else "Fact")
        return key, fact

    def _title_key(self, text):
        key = re.sub(r"\s+", " ", text.strip(" .,:;!?")).strip()
        return key[:80].title() or "Fact"

    def _clean_fact(self, text):
        return str(text).strip().strip(" .")

    def _reindex(self, chat_id, facts):
        fact_rows = [
            {"key": key, "value": value, "text": f"{key}: {value}"}
            for key, value in facts.items()
        ]
        if self._load_embedding_model() and fact_rows:
            vectors = self._embedding_model.encode(
                [row["text"] for row in fact_rows], normalize_embeddings=True
            )
            for row, vector in zip(fact_rows, vectors):
                row["embedding"] = vector
        else:
            for row in fact_rows:
                row["terms"] = self._terms(row["text"])
        self._fact_index[str(chat_id)] = fact_rows

    def _load_embedding_model(self):
        if self._embedding_available is not None:
            return self._embedding_available
        try:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self.model_name)
            self._embedding_available = True
        except Exception:
            self._embedding_available = False
        return self._embedding_available

    def _terms(self, text):
        return set(re.findall(r"[a-z0-9]+", str(text).lower()))

    def _lexical_score(self, query_terms, fact_terms):
        if not query_terms or not fact_terms:
            return 0.0
        return len(query_terms & fact_terms) / math.sqrt(len(query_terms) * len(fact_terms))

    def _dot(self, a, b):
        return float(sum(x * y for x, y in zip(a, b)))


default_memory = UserMemory()
