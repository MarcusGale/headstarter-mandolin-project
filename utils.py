import fitz
import json
from pathlib import Path
from fpdf import FPDF
import os
import google.generativeai as genai
import asyncio
from dotenv import load_dotenv

#loading variables from .env into os.environ
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Choose a model
model_name = "gemini-pro"

# Clean markdown-formatted JSON
def clean_markdown_json(text: str) -> str:
    return re.sub(r'^```(?:json)?\n?|\n?```$', '', text.strip(), flags=re.IGNORECASE)

async def query_gemini_async(prompt: str, file_path: str) -> str:
    model = genai.GenerativeModel(model_name)
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    response = model.generate_content([prompt, pdf_bytes])

    result = response.text
    print("📦 Raw result from Gemini:", result[:300])  # log preview
    return clean_markdown_json(result)
def extract_fields_with_positions(pdf_path):
    doc = fitz.open(pdf_path)
    fields = []
    for page_num, page in enumerate(doc, start=1):
        for w in page.widgets() or []:
            fields.append({
                "name": w.field_name,
                "type": "checkbox" if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX else "text",
                "value": w.field_value,
                "page": page_num,
                "field_label": w.field_label,
            })
    fields_by_page = {}
    for field in fields:
        fields_by_page.setdefault(field["page"], []).append(field)
    return fields_by_page

def form_pa_prompt(fields_by_page):
    fields_json = json.dumps(fields_by_page, indent=2)
    return f"""
<ROLE_AND_TASK>
You are an expert medical document processing assistant specializing in Prior Authorization (PA) form analysis.
</ROLE_AND_TASK>
<FORM_FIELD_DATA>
{fields_json}
</FORM_FIELD_DATA>
<OUTPUT_REQUIREMENTS>
Return a JSON array where each item includes:
- name, type, page, field_label, question, context
</OUTPUT_REQUIREMENTS>
"""
def configure_genai():
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

async def query_gemini_async(prompt, pdf_path, model="gemini-1.5-flash-latest"):
    configure_genai()
    file_bytes = Path(pdf_path).read_bytes()

    model = genai.GenerativeModel(model)

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: model.generate_content(
        [
                {"mime_type": "application/pdf", "data": file_bytes},
            prompt
        ]
    ))

    return response.text

def generate_summary_pdf(summary_data, original_filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Summary of: {original_filename}", ln=True)

    pdf.set_font("Arial", size=11)
    for field in summary_data:
        pdf.ln(4)
        pdf.cell(0, 10, f"Field: {field['field_label']}", ln=True)
        pdf.multi_cell(0, 10, f"Question: {field['question']}")
        pdf.multi_cell(0, 10, f"Context: {field['context']}")
        pdf.ln(3)

    output_path = f"generated/summary_{Path(original_filename).stem}.pdf"
    Path("generated").mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path
