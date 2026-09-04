import os
from pathlib import Path
from typing import Optional

class RAGRetriever:
    def __init__(self, persist_dir: str | Path | None = None):
        configured_dir = persist_dir or os.environ.get("VTT_RAG_DIR")
        if not configured_dir:
            raise RuntimeError(
                "VTT RAG storage is not configured. Pass persist_dir or set VTT_RAG_DIR."
            )
        self.persist_dir = str(Path(configured_dir).expanduser().resolve())

        # We wrap in try-except in case it hasn't been ingested yet
        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings

            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            if os.path.exists(self.persist_dir):
                self.vector_store = Chroma(
                    persist_directory=self.persist_dir,
                    embedding_function=self.embeddings
                )
            else:
                self.vector_store = None
        except ImportError as exc:
            raise RuntimeError(
                "RAG dependencies are not installed. "
                "Install the package with the 'rag' extra: pip install 'vtt[rag]'."
            ) from exc
        except Exception as e:
            print(f"RAG init error: {e}")
            self.vector_store = None

    def query_knowledge(
        self,
        query: str,
        k: int = 3,
        source: Optional[str] = None,
        section: Optional[str] = None,
    ) -> str:
        """
        Search the ingested module text. If `section` (and optionally
        `source`) is given, the search is scoped to that room/entry only --
        chunks are tagged with these at ingest time (see rag/ingest.py). This
        is what keeps a query about the current room from pulling in text
        from unrelated rooms elsewhere in the module.
        """
        if not self.vector_store:
            return "Knowledge base not initialized. No modules ingested."

        where = None
        if source and section:
            where = {"$and": [{"source": source}, {"section": section}]}
        elif source:
            where = {"source": source}
        elif section:
            where = {"section": section}

        results = self.vector_store.similarity_search(query, k=k, filter=where)
        if not results:
            if where:
                return (
                    f"No relevant information found for section '{section or ''}'"
                    f"{f' in {source}' if source else ''}. "
                    "Try omitting section for a broader (whole-module) search."
                )
            return "No relevant information found in the adventure modules."

        combined_text = "\n\n--- MODULE EXCERPT ---\n\n".join(
            f"[{doc.metadata.get('source', '?')} / {doc.metadata.get('section', '?')}]\n{doc.page_content}"
            for doc in results
        )
        return combined_text
