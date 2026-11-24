#!/usr/bin/env python3
"""把结构化解析结果组织成可编辑学术 PPTX，并可选渲染 PDF/PNG 预览。

自包含：优先使用 python-pptx（若已安装，输出更完整），否则回退到仅用标准库的
最小 OOXML 生成器（保证在无第三方库的环境也能产出可编辑 PPTX）。

用法:
    python3 build_slides.py <parse_result.json> <out.pptx> [--render]
    python3 build_slides.py <parse_result.json> <out.pptx> --render-pdf <out.pdf>

输入 JSON 建议包含（字段缺失会安全跳过）:
    document.title / document.authors / document.abstract
    document.sections[] = {level, number, title, page}
    tables[] = {id, page, caption}
    formulas[] = {id, page}
    figures[] = {id, page, caption}
    references[] = {id, text, page}
    blocks[] = {type, page, text}   # 用于逐页讲稿要点

每张幻灯片的备注（notes）写入:
    "证据: page=N"  以及 讲稿要点（该单元的一句话概括 + 来源定位）。

渲染: 实际探测 soffice 或 libreoffice 并调用同一路径；不可用或 OSError 时明确
跳过而不中断。--render 使用 PPTX 同名 PDF；--render-pdf 的移动后路径必须生效。
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile


def _xml_escape(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# --------------------------------------------------------------------------
# 路径 A：python-pptx（更完整，含主题/版式/备注）
# --------------------------------------------------------------------------
def build_with_pptx(data, out_path):
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    doc = data.get("document", {})

    # 封面
    s = prs.slides.add_slide(blank)
    title = s.shapes.title if s.shapes.title is not None else None
    if title is None:
        box = s.shapes.add_textbox(Inches(0.6), Inches(1.0), Inches(12), Inches(1.2))
        title = box.text_frame
    title.text = doc.get("title", "Untitled")
    authors = doc.get("authors", "")
    if authors:
        box = s.shapes.add_textbox(Inches(0.6), Inches(2.2), Inches(12), Inches(0.8))
        box.text_frame.text = authors
    _set_notes(s, _cover_notes(data))

    # 摘要
    abstract = doc.get("abstract", "")
    if abstract:
        s = prs.slides.add_slide(blank)
        _fill_title(s, "Abstract")
        box = s.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(12), Inches(5.5))
        tf = box.text_frame
        tf.text = abstract
        tf.word_wrap = True
        _set_notes(s, _unit_notes("abstract", 1, abstract))

    # 章节
    for sec in doc.get("sections", []):
        s = prs.slides.add_slide(blank)
        label = sec.get("title") or sec.get("number", "")
        if sec.get("number"):
            label = f"{sec['number']} {sec.get('title','')}".strip()
        _fill_title(s, label)
        body = sec.get("summary") or sec.get("body") or ""
        if body:
            box = s.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(12), Inches(5.5))
            box.text_frame.text = body
            box.text_frame.word_wrap = True
        _set_notes(s, _unit_notes(sec.get("id", label), sec.get("page"), body or label))

    # 表格 / 公式 / 图注
    for t in data.get("tables", []):
        s = prs.slides.add_slide(blank)
        _fill_title(s, f"{t.get('id','Table')} · {t.get('caption','')}".strip(" ·"))
        html = t.get("html") or t.get("markdown") or ""
        if html:
            box = s.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(12), Inches(5.5))
            box.text_frame.text = html
        _set_notes(s, _unit_notes(t.get("id"), t.get("page"), t.get("caption", "")))

    for f in data.get("formulas", []):
        s = prs.slides.add_slide(blank)
        _fill_title(s, f.get("id", "Formula"))
        latex = f.get("latex") or f.get("original", "")
        if latex:
            box = s.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(12), Inches(2.0))
            box.text_frame.text = latex
        _set_notes(s, _unit_notes(f.get("id"), f.get("page"), latex))

    for fig in data.get("figures", []):
        s = prs.slides.add_slide(blank)
        _fill_title(s, f"{fig.get('id','Fig.')} · {fig.get('caption','')}".strip(" ·"))
        _set_notes(s, _unit_notes(fig.get("id"), fig.get("page"), fig.get("caption", "")))

    # 参考文献
    refs = doc.get("references", [])
    if refs:
        s = prs.slides.add_slide(blank)
        _fill_title(s, "References")
        box = s.shapes.add_textbox(Inches(0.6), Inches(1.3), Inches(12), Inches(5.7))
        tf = box.text_frame
        tf.text = "\n".join(r.get("id", "") + " " + r.get("text", "") for r in refs)
        tf.word_wrap = True
        _set_notes(s, _unit_notes("references", refs[0].get("page") if refs else None, ""))

    prs.save(out_path)


def _fill_title(slide, text):
    try:
        slide.shapes.title.text = text
    except Exception:
        from pptx.util import Inches
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), Inches(12), Inches(0.9))
        box.text_frame.text = text


def _set_notes(slide, text):
    try:
        slide.notes_slide.notes_text_frame.text = text
    except Exception:
        pass


def _cover_notes(data):
    doc = data.get("document", {})
    return (
        f"证据: 封面（标题页）\n"
        f"讲稿: 本演示由论文解析结果自动生成；标题 {doc.get('title','')}，"
        f"作者 {doc.get('authors','')}。逐页备注含来源页码。"
    )


def _unit_notes(uid, page, text):
    p = f"page={page}" if page is not None else "page=?"
    snippet = (text or "").strip().replace("\n", " ")[:120]
    return f"证据: {p}\n讲稿要点: {uid}\n来源内容: {snippet}"


# --------------------------------------------------------------------------
# 路径 B：最小 OOXML 生成器（仅标准库，保证可编辑 PPTX）
# --------------------------------------------------------------------------
def build_minimal_pptx(data, out_path):
    slides = _make_slide_models(data)

    def content_types():
        parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        ]
        for i in range(1, len(slides) + 1):
            parts.append(
                f'<Override PartName="/ppt/slides/slide{i}.xml" '
                f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            )
        parts.append('</Types>')
        return "\n".join(parts)

    def rels_root():
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
            '</Relationships>'
        )

    def presentation_xml(n):
        sids = "".join(
            f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(n)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:sldIdLst>{sids}</p:sldIdLst>'
            '<p:sldSz cx="12192000" cy="6858000"/>'
            '<p:notesSz cx="6858000" cy="9144000"/>'
            '</p:presentation>'
        )

    def presentation_rels(n):
        rows = []
        for i in range(n):
            rows.append(
                f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                f'Target="slides/slide{i + 1}.xml"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rows)
            + "</Relationships>"
        )

    def slide_xml(i, model):
        title = model["title"]
        body_lines = model["body"]
        # 文本框：标题 + 正文
        shapes = [
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
            '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="685800" y="274320"/><a:ext cx="11506200" cy="731520"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            '<p:txBody><a:bodyPr/><a:lstStyle/>'
            '<a:p><a:r><a:rPr lang="en-US" sz="2400" b="1"/><a:t>'
            + _xml_escape(title)
            + '</a:t></a:r></a:p></p:txBody></p:sp>'
        ]
        if body_lines:
            paras = "".join(
                f'<a:p><a:r><a:rPr lang="en-US" sz="1400"/><a:t>{_xml_escape(l)}</a:t></a:r></a:p>'
                for l in body_lines
            )
            shapes.append(
                '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Body"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
                '<p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
                '<p:spPr><a:xfrm><a:off x="685800" y="1097280"/><a:ext cx="11506200" cy="5212080"/></a:xfrm>'
                '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
                '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>'
                + paras
                + '</p:txBody></p:sp>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
            '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            + "".join(shapes)
            + "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types())
        z.writestr("_rels/.rels", rels_root())
        z.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(len(slides)))
        for i, m in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i, m))
            z.writestr(
                f"ppt/slides/_rels/slide{i}.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                'Target="../slideLayouts/slideLayout1.xml"/>'
                "</Relationships>",
            )
        # 最小 slideLayout + slideMaster（供引用）
        z.writestr(
            "ppt/slideLayouts/slideLayout1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">'
            '<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>",
        )
        z.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
            'Target="../slideMasters/slideMaster1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/slideMasters/slideMaster1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            "</p:spTree></p:cSld><p:clrMap><a:bg1 lang=\"\"/><a:tx1/><a:bg2/><a:tx2/><a:accent1/><a:accent2/><a:accent3/>"
            "<a:accent4/><a:accent5/><a:accent6/><a:hlink/><a:folHlink/></p:clrMap>"
            '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>',
        )
        z.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
            'Target="../slideLayouts/slideLayout1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/theme/theme1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office"><a:themeElements>'
            '<a:clrScheme name="Office"><a:dk1/><a:lt1/><a:dk2/><a:lt2/><a:accent1/><a:accent2/><a:accent3/>'
            '<a:accent4/><a:accent5/><a:accent6/><a:hlink/><a:folHlink/></a:clrScheme>'
            '<a:fontScheme name="Office"><a:majorFont/><a:minorFont/></a:fontScheme>'
            '<a:fmtScheme name="Office"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>'
            "</a:themeElements></a:theme>",
        )
    # 备注文件（简单讲稿，存为可读 txt 而非 notesSlide，保证可编辑）
    notes_path = os.path.splitext(out_path)[0] + ".notes.txt"
    with open(notes_path, "w", encoding="utf-8") as fh:
        for m in slides:
            fh.write(f"### {m['title']}\n{m['notes']}\n\n")
    print(f"[build_slides] notes written: {notes_path}")


def _make_slide_models(data):
    doc = data.get("document", {})
    models = [{"title": doc.get("title", "Untitled"), "body": [], "notes": _cover_notes(data)}]

    abstract = doc.get("abstract", "")
    if abstract:
        models.append({"title": "Abstract", "body": _wrap(abstract, 90), "notes": _unit_notes("abstract", 1, abstract)})

    for sec in doc.get("sections", []):
        label = sec.get("title") or sec.get("number", "")
        if sec.get("number"):
            label = f"{sec['number']} {sec.get('title','')}".strip()
        body = sec.get("summary") or sec.get("body") or ""
        models.append({"title": label, "body": _wrap(body, 90) if body else [], "notes": _unit_notes(sec.get("id", label), sec.get("page"), body or label)})

    for t in data.get("tables", []):
        models.append({"title": f"{t.get('id','Table')} · {t.get('caption','')}".strip(" ·"),
                       "body": _wrap(t.get("html") or t.get("markdown") or "", 90),
                       "notes": _unit_notes(t.get("id"), t.get("page"), t.get("caption", ""))})
    for f in data.get("formulas", []):
        latex = f.get("latex") or f.get("original", "")
        models.append({"title": f.get("id", "Formula"), "body": _wrap(latex, 90),
                       "notes": _unit_notes(f.get("id"), f.get("page"), latex)})
    for fig in data.get("figures", []):
        models.append({"title": f"{fig.get('id','Fig.')} · {fig.get('caption','')}".strip(" ·"),
                       "body": [], "notes": _unit_notes(fig.get("id"), fig.get("page"), fig.get("caption", ""))})

    refs = doc.get("references", [])
    if refs:
        models.append({"title": "References",
                       "body": _wrap("\n".join(r.get("id","")+" "+r.get("text","") for r in refs), 100),
                       "notes": _unit_notes("references", refs[0].get("page") if refs else None, "")})
    return models


def _wrap(text, width):
    if not text:
        return []
    out = []
    for raw in text.split("\n"):
        while len(raw) > width:
            out.append(raw[:width])
            raw = raw[width:]
        if raw:
            out.append(raw)
    return out[:60]  # 每页正文行数上限，避免溢出


def render_pdf(pptx_path, pdf_path):
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        print("[render] 未找到 soffice/libreoffice，跳过 PDF 渲染（保留 PPTX）")
        return False
    pdf_path = os.path.abspath(pdf_path)
    out_dir = os.path.dirname(pdf_path)
    converted = os.path.join(
        out_dir, os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf")
    cmd = [office, "--headless", "--convert-to", "pdf", "--outdir",
           out_dir, pptx_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print(f"[render] 渲染失败: {r.stderr[:400]}")
            return False
        if not os.path.isfile(converted):
            print(f"[render] 渲染失败：Office 未生成预期文件 {converted}")
            return False
        # LibreOffice 按 PPTX 文件名命名；显式 --render-pdf 路径必须最终生效。
        if os.path.abspath(converted) != pdf_path:
            shutil.move(converted, pdf_path)
    except OSError as exc:
        print(f"[render] Office/文件调用失败，跳过 PDF 渲染（保留 PPTX）: {exc}")
        return False
    print(f"[render] 已生成 PDF: {pdf_path}")
    return True


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = sys.argv[1]
    out = sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    try:
        import pptx  # noqa: F401
        build_with_pptx(data, out)
        print(f"[build_slides] 使用 python-pptx 生成: {out}")
    except ImportError:
        build_minimal_pptx(data, out)
        print(f"[build_slides] 使用最小 OOXML 生成: {out}")
    if "--render" in sys.argv or "--render-pdf" in sys.argv:
        pdf = os.path.splitext(out)[0] + ".pdf"
        if "--render-pdf" in sys.argv:
            index = sys.argv.index("--render-pdf")
            if index + 1 >= len(sys.argv):
                print("build_slides: --render-pdf 需要输出 PDF 路径", file=sys.stderr)
                return 2
            pdf = sys.argv[index + 1]
        render_pdf(out, pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
