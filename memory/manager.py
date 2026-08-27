"""
High-level memory operations for Astra.

Turns raw requests into database work: remembering, recalling,
forgetting, searching, and summarizing.  Sensitive content is
rejected outright.
"""

import re

from memory.database import MemoryDatabase


SENSITIVE_PATTERNS = re.compile(
    r"password|passcode|secret|credential|token|api ?key|credit ?card|"
    r"social ?security|pin\b|private ?key|login",
    re.IGNORECASE,
)


class MemoryManager:

    SHORT_TERM_LIMIT = 50
    DEFAULT_CATEGORY = "long_term"

    def __init__(self, db_path, enabled=True):
        self.enabled = enabled
        self.database = MemoryDatabase(db_path) if enabled else None

    def is_sensitive(self, content):
        return bool(SENSITIVE_PATTERNS.search(content))

    def remember(self, content, category=None):
        """Store a memory.  Returns (ok, message, item)."""

        if not self.enabled:
            return False, "Memory is disabled.", None

        if not content or not content.strip():
            return False, "I did not catch what you want me to remember.", None

        content = content.strip()

        if self.is_sensitive(content):
            return False, "I will not store sensitive information like that.", None

        category = category or self.DEFAULT_CATEGORY

        if category not in MemoryDatabase.CATEGORIES:
            category = self.DEFAULT_CATEGORY

        entry_id = self.database.add_entry(category, content)

        if category == "short_term":
            self.database.prune_category(
                "short_term", self.SHORT_TERM_LIMIT
            )

        item = {
            "id": entry_id,
            "category": category,
            "content": content,
        }

        return True, "Remembered.", item

    def recall(self, query=None, category=None, limit=5):
        """Retrieve matching memories.  Returns (ok, message, items).

        When a query is given, durable memories (long_term,
        preferences, facts) rank above short-term conversation
        history.
        """

        if not self.enabled:
            return False, "Memory is disabled.", []

        if query and query.strip():

            query = query.strip()

            if category is not None:

                rows = self.database.search_entries(
                    query, category=category, limit=limit
                )

            else:

                durable = self.database.search_entries(
                    query,
                    categories=("long_term", "preferences", "facts"),
                    limit=limit,
                )

                transcript = self.database.search_entries(
                    query, category="short_term", limit=limit
                )

                seen = {row["id"] for row in durable}

                rows = durable + [
                    row for row in transcript if row["id"] not in seen
                ]

                rows = rows[:limit]

        else:

            rows = self.database.list_entries(
                category=category, limit=limit
            )

        if not rows:
            return False, "I have nothing matching that in memory.", []

        return True, f"I found {len(rows)} matching memory item(s).", rows

    def forget(self, query=None, category=None):
        """Remove matching memories.  Returns (ok, message, count)."""

        if not self.enabled:
            return False, "Memory is disabled.", 0

        if not query or not query.strip():
            return False, "Forget what?  Tell me what to forget.", 0

        count = self.database.delete_entries(
            category=category, content=query.strip()
        )

        if count == 0:
            return False, "I found nothing to forget.", 0

        return True, f"Forgot {count} matching memory item(s).", count

    def summarize(self, category="short_term", limit=20):
        """Return the most recent memories as one compact text."""

        if not self.enabled:
            return "Memory is disabled."

        rows = self.database.list_entries(
            category=category, limit=limit
        )

        if not rows:
            return "I have no memories stored yet."

        lines = [f"- {row['content']}" for row in rows]

        return "\n".join(lines)

    def store_task_record(self, goal, status, detail=""):
        """Remember a task outcome in the tasks category."""

        if not self.enabled:
            return False

        content = f"Task ({status}): {goal}"

        if detail:
            content = f"{content} | {detail}"

        ok, message, item = self.remember(content, category="tasks")

        return ok

    def recent_tasks(self, limit=3):
        """Return the most recent task records."""

        if not self.enabled:
            return []

        return self.database.list_entries(
            category="tasks", limit=limit
        )

    # ==============================================
    # RELEVANCE
    # ==============================================

    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "is", "are", "was",
        "were", "be", "been", "to", "of", "in", "on", "at", "for",
        "with", "from", "by", "about", "as", "it", "its", "this",
        "that", "what", "when", "where", "who", "which", "how",
        "why", "do", "does", "did", "i", "you", "me", "my", "your",
        "we", "our", "they", "their", "he", "she", "his", "her",
        "so", "just", "not", "no", "yes", "tell", "have", "has",
    }

    RELEVANCE_POOL = (
        "long_term",
        "preferences",
        "facts",
        "tasks",
        "instructions",
    )

    def _significant_tokens(self, text):

        return {
            token
            for token in re.findall(r"[a-z]+", text.lower())
            if len(token) > 2 and token not in self.STOPWORDS
        }

    def retrieve_relevant(self, text, top=3, min_score=0.25):
        """Selectively pull memories relevant to a request.

        Returns a list of entries, best match first.  Short-term
        conversation history is deliberately excluded so that past
        utterances do not shadow durable knowledge.
        """

        if not self.enabled:
            return []

        tokens = self._significant_tokens(text)

        if len(tokens) < 2:
            return []

        rows = self.database.list_entries(
            categories=self.RELEVANCE_POOL, limit=200
        )

        scored = []

        for row in rows:

            entry_tokens = self._significant_tokens(row["content"])

            overlap = len(tokens & entry_tokens)

            if overlap < 1:
                continue

            score = overlap / len(tokens)

            if score >= min_score:
                scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [row for _score, row in scored[:top]]

    def close(self):

        if self.database:
            self.database.close()
