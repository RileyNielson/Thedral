import os
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel
from backend.publishing import (
    generate_narrator_pack, 
    generate_authorship_certificate, 
    generate_query_synopsis,
    generate_manuscript_genome
)
from backend.compiler import compile_book_to_docx
from backend.config import ENABLE_AI

router = APIRouter(tags=["Publishing"])

class SynopsisRequest(BaseModel):
    book_id: str | None = None

@router.get("/api/publishing/narrator-pack", response_class=PlainTextResponse)
def get_narrator_pack(book_id: str | None = None):
    return generate_narrator_pack(book_id)

@router.get("/api/publishing/authorship-proof")
def get_authorship_proof(book_id: str | None = None):
    return generate_authorship_certificate(book_id)

@router.post("/api/publishing/synopsis")
def get_synopsis(payload: SynopsisRequest):
    if not ENABLE_AI:
        return {"synopsis": "Query Synopsis requires local AI (Pure Math Mode active)."}
    return {"synopsis": generate_query_synopsis(payload.book_id)}

@router.get("/api/publishing/genome")
def get_genome(book_id: str | None = None):
    """Macro full-manuscript Reader Genome and Comps DNA analysis."""
    return generate_manuscript_genome(book_id)

@router.get("/api/compile/docx")
def download_manuscript(book_id: str | None = None):
    out_path = compile_book_to_docx(book_id)
    return FileResponse(out_path, filename="Thedral_Manuscript.docx")
