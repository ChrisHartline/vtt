import os
import glob
import re

# These TSR modules render (via Docling) with '## ' markdown headers for every
# room/entry/section -- e.g. "## 12. OAKEN CABINET", "## ENTRY 5.",
# "## PART 4: SECOND DUNGEON LEVEL" (verified against real Docling output).
# Splitting on these instead of blind character counts means every chunk can
# be tagged with the room it actually came from, so retrieval can be scoped
# to "only what's in the current room" instead of the whole module.
_SECTION_HEADER_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def split_by_section(markdown: str):
    """Split module markdown into (text, section_label) pairs on '## ' headers.

    Falls back to a single ("unknown"-labeled) section if no headers are
    found, so ingestion never silently drops content for a module that
    doesn't follow the same header convention.
    """
    matches = list(_SECTION_HEADER_RE.finditer(markdown))
    if not matches:
        return [(markdown, "unknown")]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        label = m.group(1).strip()
        text = markdown[start:end].strip()
        if text:
            sections.append((text, label))
    return sections


# Purchased PDFs (DriveThruRPG and similar) stamp every page footer with the
# buyer's name and order number, e.g. "Jane Doe (Order #12345678)". That line
# is noise for retrieval and is personal data that would otherwise travel to
# whatever model reads the chunks, so drop it before splitting.
_WATERMARK_RE = re.compile(r"^[^\n]*\(Order #\d+\)[^\n]*\n?", re.MULTILINE)


def strip_watermarks(markdown: str) -> str:
    """Remove store watermark lines ("Name (Order #123)") from Docling output."""
    return _WATERMARK_RE.sub("", markdown)


# Some modules (e.g. FRQ1) key their rooms inline -- "1.  Owlbear Lair: These
# dark passages..." -- under one big "Dungeon Key" header instead of a '## '
# header per room. Without this, every room in the key shares one section tag
# and room-scoped retrieval cannot find "room 12". Room names come from the
# body text, which OCRs far more cleanly than the decorative header fonts.
_INLINE_ROOM_RE = re.compile(r"^\**\s*(\d{1,3})\.\s+([^:\n.]{2,60}):", re.MULTILINE)


def split_inline_rooms(text: str, label: str):
    """Split a section on inline numbered room entries ("12. Name: ...").

    Only splits when there are at least three entries, no number repeats,
    and at least 70% of neighbouring entries go up. Two-column page layouts
    shuffle a few rooms (FRQ1 parses as ... 4, 6, 7, 5, 8 ...), so strict
    order is too strict, but ordinary numbered lists still fail the test.
    Text before the first entry keeps the parent label.
    """
    matches = list(_INLINE_ROOM_RE.finditer(text))
    numbers = [int(m.group(1)) for m in matches]
    if len(matches) < 3 or len(set(numbers)) != len(numbers):
        return [(text, label)]
    rising = sum(b > a for a, b in zip(numbers, numbers[1:]))
    if rising < 0.7 * (len(numbers) - 1):
        return [(text, label)]

    pieces = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        pieces.append((preamble, label))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        name = " ".join(m.group(2).split())
        pieces.append((text[m.start():end].strip(), f"Room {m.group(1)}: {name}"))
    return pieces


def load_source_info(source_dir: str) -> dict:
    """Read optional per-PDF metadata from <source_dir>/sources.json.

    Maps a filename prefix to extra metadata, e.g.
    {"FRQ1": {"era": "c. 1360 DR", "edition": "AD&D 2e"}}. Every chunk from a
    matching PDF carries those fields, so a narrator or lore-keeper can tell
    which year a source describes and weigh it against the campaign's year.
    """
    import json

    path = os.path.join(source_dir, "sources.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def source_metadata(filename: str, info: dict) -> dict:
    """Metadata for one PDF: the longest matching prefix in info wins."""
    best = max((k for k in info if filename.startswith(k)), key=len, default=None)
    meta = {"era": "unknown", "edition": "unknown"}
    if best is not None:
        meta.update({k: str(v) for k, v in info[best].items()})
    return meta


def ingest_pdfs(source_dir: str = "knowledge_base/dnd", persist_dir: str = "data/chroma"):
    try:
        from docling.document_converter import DocumentConverter
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_text_splitters import MarkdownTextSplitter
    except ImportError as exc:
        raise RuntimeError(
            "PDF ingestion dependencies are not installed. "
            "Install the package with the 'ingest' extra: pip install 'vtt[ingest]'."
        ) from exc

    print(f"Starting ingestion from {source_dir}...")
    converter = DocumentConverter()

    # 1. Parse PDFs with Docling
    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {source_dir}")
        return

    # Sub-splitter for sections still too long for one chunk -- keeps the
    # section tag attached to every resulting piece.
    sub_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)

    source_info = load_source_info(source_dir)

    all_chunks = []
    for pdf_path in pdf_files:
        source = os.path.basename(pdf_path)
        print(f"Parsing: {pdf_path} using Docling (Layout Preserving)...")
        result = converter.convert(pdf_path)
        markdown_content = strip_watermarks(result.document.export_to_markdown())
        extra = source_metadata(source, source_info)

        sections = [
            piece
            for text, label in split_by_section(markdown_content)
            for piece in split_inline_rooms(text, label)
        ]
        print(f"  {source}: {len(sections)} sections found")

        for section_text, section_label in sections:
            pieces = (
                sub_splitter.split_text(section_text)
                if len(section_text) > 1000
                else [section_text]
            )
            for piece in pieces:
                all_chunks.append(Document(
                    page_content=piece,
                    metadata={"source": source, "section": section_label, **extra},
                ))

    # 2. Embed and store
    print(f"Embedding {len(all_chunks)} section-tagged chunks locally using HuggingFace...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Saving to Chroma DB at {persist_dir}...")
    # Chroma.from_documents() ADDS to whatever's already at persist_dir rather
    # than replacing it -- re-running ingestion (e.g. after a chunking-scheme
    # change, or just adding a new module) silently doubles up on old data
    # instead of rebuilding clean. Reset the collection first so re-running
    # this is idempotent.
    vector_store = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    existing_ids = vector_store.get(limit=1_000_000)["ids"]
    if existing_ids:
        print(f"Clearing {len(existing_ids)} existing chunks before re-ingesting...")
        vector_store.delete(ids=existing_ids)

    vector_store.add_documents(all_chunks)
    print("Ingestion complete!")

def main():
    ingest_pdfs()


if __name__ == "__main__":
    main()
