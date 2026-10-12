from backend.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT

    print(f"🚀 Thedral Studio Server starting on http://{HOST}:{PORT}")
    uvicorn.run("backend.main:app", host=HOST, port=PORT)
