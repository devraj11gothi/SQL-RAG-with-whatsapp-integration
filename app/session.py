HISTORY_TURNS = 5


class Session:
    def __init__(self):
        self.turns: list[dict] = []

    def add_turn(self, question: str, sql: str, answer: str) -> None:
        self.turns.append({"question": question, "sql": sql, "answer": answer})

    def context_text(self) -> str:
        recent = self.turns[-HISTORY_TURNS:]
        if not recent:
            return ""
        lines = [
            f"Q: {t['question']}\nSQL: {t['sql']}\nA: {t['answer']}" for t in recent
        ]
        return "Previous conversation:\n" + "\n\n".join(lines) + "\n\n"
