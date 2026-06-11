from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size=800, overlap=150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "; ", ", ", " "]
        )

    def chunk_sections(self, sections: dict) -> list:
        chunks = []
        for section_path, content in sections.items():
            if not content or len(content.strip()) < 20:
                continue

            if len(content) <= self.splitter._chunk_size:
                # Short enough — keep as single chunk
                chunks.append({
                    "section": section_path,
                    "chunk_index": 0,
                    "content": content.strip()
                })
            else:
                # Split long content
                sub_chunks = self.splitter.split_text(content)
                for i, chunk in enumerate(sub_chunks):
                    if chunk.strip():
                        chunks.append({
                            "section": section_path,
                            "chunk_index": i,
                            "content": chunk.strip()
                        })
        return chunks