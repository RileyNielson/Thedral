import uvicorn

if __name__ == "__main__":
    print("🚀 Thedral Studio Server starting on http://0.0.0.0:8000")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
