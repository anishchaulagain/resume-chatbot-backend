import PyPDF2
import io
import re
from typing import Optional


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text content from a PDF file."""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text.strip())
    return "\n\n".join(text_parts)


def parse_resume_sections(raw_text: str) -> dict:
    """Parse raw resume text into structured sections."""
    section_patterns = [
        r"(?i)(summary|objective|about\s*me|profile)",
        r"(?i)(experience|work\s*experience|employment|professional\s*experience)",
        r"(?i)(education|academic|qualification)",
        r"(?i)(skills|technical\s*skills|core\s*competencies|technologies)",
        r"(?i)(projects|personal\s*projects|key\s*projects)",
        r"(?i)(certifications?|certificates?|licenses?)",
        r"(?i)(awards?|achievements?|honors?)",
        r"(?i)(languages?)",
        r"(?i)(interests?|hobbies?)",
        r"(?i)(references?|contact)",
        r"(?i)(publications?|research)",
        r"(?i)(volunteer|community)",
    ]

    sections = {}
    lines = raw_text.split("\n")
    current_section = "header"
    current_content = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            current_content.append("")
            continue

        matched = False
        for pattern in section_patterns:
            if re.match(pattern, line_stripped):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = re.sub(
                    r"[^a-z_]", "", line_stripped.lower().replace(" ", "_")
                )
                current_content = []
                matched = True
                break

        if not matched:
            current_content.append(line_stripped)

    # Save the last section
    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def get_resume_context(raw_text: str, sections: Optional[dict] = None) -> str:
    """Build a formatted context string from resume data for LLM consumption."""
    if sections:
        context_parts = []
        for section_name, content in sections.items():
            readable_name = section_name.replace("_", " ").title()
            context_parts.append(f"## {readable_name}\n{content}")
        return "\n\n".join(context_parts)
    return raw_text
