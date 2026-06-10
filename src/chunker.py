from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size=1000, overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ".", " "]
        )

    def chunk_sections(self, sections: dict) -> list:
        """
        Chunk each section independently to preserve context.
        Returns list of dicts with section + chunk content.
        """
        chunks = []
        for section_title, content in sections.items():
            if not content.strip():
                continue

            sub_chunks = self.splitter.split_text(content)
            for i, chunk in enumerate(sub_chunks):
                chunks.append({
                    "section": section_title,
                    "chunk_index": i,
                    "content": chunk.strip()
                })
        return chunks