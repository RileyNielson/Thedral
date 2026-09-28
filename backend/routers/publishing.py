import os
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel
from backend.publishing import generate_narrator_pack, generate_authorship_certificate, generate_query_synopsis
from backend.compiler import compile_book_to_docx

router = APIRouter(tags=["Publishing"])

class SynopsisRequest(BaseModel):
    book_id: str | None = None

@router.get("/api/publishing/narrator-pack", response_class=PlainTextResponse)
def get_narrator_pack(book_id: str | None = None):
    """Generates official voice actor pronunciation guide and character vocal profiles."""
    return generate_narrator_pack(book_id)

@router.get("/api/publishing/authorship-proof")
def get_authorship_proof(book_id: str | None = None):
    """Returns official cryptographic audit certificate of organic human drafting."""
    return generate_authorship_certificate(book_id)

@router.post("/api/publishing/synopsis")
def get_synopsis(payload: SynopsisRequest):
    """Compiles an agent-ready 1-page query synopsis from the causal plot spine."""
    return {"synopsis": generate_query_synopsis(payload.book_id)}

@router.get("/api/compile/docx")
def download_manuscript(book_id: str | None = None):
    """Compiles publication-grade formatted Word document with epigraphs."""
    out_path = compile_book_to_docx(book_id)
    return FileResponse(out_path, filename="Thedral_Manuscript.docx")
