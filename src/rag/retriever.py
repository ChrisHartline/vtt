import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class RAGRetriever:
    def __init__(self, persist_dir: str = "data/chroma"):
        self.persist_dir = persist_dir
        
        # We wrap in try-except in case it hasn't been ingested yet
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            if os.path.exists(self.persist_dir):
                self.vector_store = Chroma(
                    persist_directory=self.persist_dir,
                    embedding_function=self.embeddings
                )
            else:
                self.vector_store = None
        except Exception as e:
            print(f"RAG init error: {e}")
            self.vector_store = None
            
    def query_knowledge(self, query: str, k: int = 3) -> str:
        if not self.vector_store:
            return "Knowledge base not initialized. No modules ingested."
            
        results = self.vector_store.similarity_search(query, k=k)
        if not results:
            return "No relevant information found in the adventure modules."
            
        combined_text = "\n\n--- MODULE EXCERPT ---\n\n".join([doc.page_content for doc in results])
        return combined_text
