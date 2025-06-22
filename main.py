from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.utils import extract_fields_with_positions, form_pa_prompt, query_gemini_async, generate_summary_pdf
import json
import os
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse

@app.post("/upload")
async def upload_pdf(pdf_file: UploadFile = File(...)):
    upload_path = Path("uploads")
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / pdf_file.filename
    with open(file_path, "wb") as f:
        f.write(await pdf_file.read())

    fields = extract_fields_with_positions(str(file_path))
    prompt = form_pa_prompt(fields)
    result = await query_gemini_async(prompt, str(file_path))
    print("Raw result from Gemini:", result)
    if result:
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            print("❌ Failed to decode JSON:", result)
            return HTMLResponse(content="Internal Error: Failed to parse model response", status_code=500)
    else:
        print("❌ Empty response from Gemini model")
        return HTMLResponse(content="Internal Error: Empty response from model", status_code=500)

    data = json.loads(result)

    output_pdf_path = generate_summary_pdf(data, pdf_file.filename)
    return FileResponse(output_pdf_path, media_type="application/pdf", filename="PA_summary.pdf")
