# 1GiB RAG Upload Decisions

- Scope is `RAG collection` uploads only in this phase.
- `project-service` uploads remain on the smaller limit because that path still buffers uploads and proxies through `storage-service`.
- Text-like RAG files are the large-file target in this phase: `.txt`, `.md`, `.markdown`, `.json`, `.csv`.
- Worker download now streams objects to a temp file before indexing.
- Text-like indexing now uses incremental parsing, chunking, embedding, and batched inserts instead of materializing the whole document in memory.
- PDF is explicitly not a `1GiB` format in the current design.
- PDF uploads remain on a lower configured cap because the current PDF parser still joins extracted text into one in-memory string.
