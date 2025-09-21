from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
from typing import List
import tempfile

app = FastAPI(title="PDF to CSV Converter API", version="1.0.0")

# CORS middleware to allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PDF to CSV Converter API is running!"}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file to extract credit card statement data
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # TODO: Implement PDF processing logic
    # This is a placeholder response
    return {
        "message": "PDF received successfully",
        "filename": file.filename,
        "size": file.size,
        "status": "processing"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-to-csv-backend"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)