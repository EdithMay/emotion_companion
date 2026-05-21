"""Backfill existing SQLite memories into ChromaDB.

Run from the backend directory:
    python backfill_rag.py
"""

import json
from datetime import date

from app.database import SessionLocal
from app.models.db_models import MemorySummary, MoodEntry
from app.services.rag_service import get_rag_service


def main():
    db = SessionLocal()
    rag = get_rag_service()
    indexed = 0

    try:
        summaries = db.query(MemorySummary).all()
        for summary in summaries:
            if rag.index(
                text=summary.summary_text,
                metadata={
                    "type": "memory_summary",
                    "date": summary.created_at.strftime("%Y-%m-%d")
                    if summary.created_at else date.today().strftime("%Y-%m-%d"),
                    "conversation_id": str(summary.conversation_id),
                    "summary_id": str(summary.id),
                },
            ):
                indexed += 1

        entries = db.query(MoodEntry).all()
        for entry in entries:
            try:
                keywords = json.loads(entry.keywords) if entry.keywords else []
            except json.JSONDecodeError:
                keywords = []

            text = entry.summary_text
            if keywords:
                text = f"{text} 情绪关键词：{'、'.join(keywords)}"

            if rag.index(
                text=text,
                metadata={
                    "type": "mood_entry",
                    "date": entry.date,
                    "score": str(entry.score),
                    "entry_id": str(entry.id),
                },
            ):
                indexed += 1

        print(f"Backfill complete. Indexed {indexed} records.")
        print(f"RAG count: {rag.count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
