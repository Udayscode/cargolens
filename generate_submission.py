"""Builds TDD.docx and packages cargolens_submission.zip for final submission."""
import os
import zipfile
import xml.sax.saxutils as saxutils

def create_docx(text_content, docx_path):
    # Minimal valid OpenXML docx structure
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    paragraphs_xml = []
    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            paragraphs_xml.append("<w:p/>")
            continue
        
        is_h1 = line.startswith("# ")
        is_h2 = line.startswith("## ")
        is_h3 = line.startswith("### ")
        
        if is_h1:
            clean = saxutils.escape(line[2:])
            p = f"""<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:spacing w:before="240" w:after="120"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="1E293B"/></w:rPr><w:t>{clean}</w:t></w:r></w:p>"""
        elif is_h2:
            clean = saxutils.escape(line[3:])
            p = f"""<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="2563EB"/></w:rPr><w:t>{clean}</w:t></w:r></w:p>"""
        elif is_h3:
            clean = saxutils.escape(line[4:])
            p = f"""<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:spacing w:before="160" w:after="80"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="24"/><w:color w:val="334155"/></w:rPr><w:t>{clean}</w:t></w:r></w:p>"""
        else:
            clean = saxutils.escape(line)
            p = f"""<w:p><w:pPr><w:spacing w:after="100"/></w:pPr><w:r><w:rPr><w:sz w:val="22"/><w:color w:val="1E293B"/></w:rPr><w:t>{clean}</w:t></w:r></w:p>"""
        paragraphs_xml.append(p)

    body_content = "".join(paragraphs_xml)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_content}
  </w:body>
</w:document>"""

    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    tdd_md_path = os.path.join(root, "TDD.md")
    dep_md_path = os.path.join(root, "deployment.md")
    tdd_docx_path = os.path.join(root, "Technical_Design_Document.docx")
    zip_path = os.path.join(root, "cargolens_submission.zip")

    with open(tdd_md_path, "r", encoding="utf-8") as f:
        tdd_text = f.read()

    print("Generating Technical_Design_Document.docx...")
    create_docx(tdd_text, tdd_docx_path)

    print("Packaging cargolens_submission.zip...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tdd_docx_path, arcname="Technical_Design_Document.docx")
        z.write(dep_md_path, arcname="deployment.md")
        z.write(tdd_md_path, arcname="TDD.md")

    print(f"SUCCESS: Submission zip created at: {zip_path}")
    print(f"ZIP contents: Technical_Design_Document.docx, deployment.md, TDD.md")

if __name__ == "__main__":
    main()
