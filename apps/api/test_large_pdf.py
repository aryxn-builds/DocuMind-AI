import sys
import uuid
from pathlib import Path

from fpdf import FPDF
from app.ai.adapters.pdf_adapter import PdfAdapter
from app.ai.chunker import Chunker

def generate_pdf(pages: int, path: str):
    pdf = FPDF()
    for i in range(pages):
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"This is page {i+1} of the test document.", ln=1, align="C")
        pdf.cell(200, 10, txt=f"Some random methodology text on page {i+1}.", ln=2, align="L")
        for j in range(10):
            pdf.cell(200, 10, txt=f"Line {j} of content on page {i+1} to add some text volume.", ln=j+3, align="L")
    pdf.output(path)
    print(f"Generated PDF with {pages} pages at {path}")

def test_pipeline(pages: int):
    path = f"test_{pages}.pdf"
    generate_pdf(pages, path)
    
    with open(path, "rb") as f:
        file_bytes = f.read()
    
    adapter = PdfAdapter("doc_1", "user_1", path, "application/pdf", "test")
    doc = adapter.parse(file_bytes)
    
    print(f"[DOC_AUDIT] pages={pages}")
    print(f"[DOC_AUDIT] extracted_pages={doc.page_count}")
    print(f"[DOC_AUDIT] blocks={len(doc.blocks)}")
    
    chunker = Chunker()
    chunks = chunker.chunk(doc)
    
    import asyncio
    from app.ai.summarization_service import SummarizationService
    sum_service = SummarizationService()
    summary_chunks = asyncio.run(sum_service.summarize_document(doc, chunks))
    
    if summary_chunks:
        chunks.extend(summary_chunks)
        print(f"[DOC_AUDIT] added {len(summary_chunks)} summary chunks")
        for sc in summary_chunks:
            print(f"Summary chunk: {sc.chunk_type} (length {len(sc.content)})")

    print(f"[DOC_AUDIT] total_chunks={len(chunks)}")
    


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pages = int(sys.argv[1])
    else:
        pages = 50
    test_pipeline(pages)
