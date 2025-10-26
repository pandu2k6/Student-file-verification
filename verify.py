import os
import PyPDF2

def get_pdf_text(filepath):
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join([page.extract_text() or '' for page in reader.pages])
    except:
        return ""

def check_conditions(filepath, conditions):
    filename = os.path.basename(filepath).lower()
    file_ext = os.path.splitext(filepath)[1].lower()
    text = get_pdf_text(filepath)

    word_count = len(text.split())
    line_count = len(text.splitlines())
    file_size_kb = os.path.getsize(filepath) / 1024  # Size in KB

    for cond in conditions:
        cond = cond.strip().lower()

        if cond.startswith("words>"):
            try:
                limit = int(cond.split(">")[1])
                if word_count <= limit:
                    return False, f"Word count must be greater than {limit}"
            except:
                continue

        elif cond.startswith("lines>"):
            try:
                limit = int(cond.split(">")[1])
                if line_count <= limit:
                    return False, f"Line count must be greater than {limit}"
            except:
                continue

        elif cond.startswith("size<"):
            try:
                limit = float(cond.split("<")[1])
                if file_size_kb >= limit:
                    return False, f"File size must be less than {limit} KB"
            except:
                continue

        elif cond.startswith("size>"):
            try:
                limit = float(cond.split(">")[1])
                if file_size_kb <= limit:
                    return False, f"File size must be greater than {limit} KB"
            except:
                continue

        elif cond.startswith("type:"):
            required_type = cond.split(":")[1].strip()
            if required_type == "pdf" and file_ext != ".pdf":
                return False, f"File must be a PDF"

        else:
            if cond not in filename:
                return False, f"Missing keyword in filename: {cond}"

    return True, ""
