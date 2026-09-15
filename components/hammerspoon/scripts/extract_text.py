#!/usr/bin/env python3
"""选中文件 → 可读文本（供 Hammerspoon「复制文件名+内容」⌘⌃⇧C 调用）。

纯文本直接读；docx/doc/pdf/xlsx/pptx 等二进制按格式抽全文，不再吐乱码字节。
契约：参数 = 一个或多个文件绝对路径；stdout = 按「文件名：X\\n\\n<正文>\\n\\n----」拼接的整块文本；
绝不 raise，单个文件失败只在它那段标 [抽取失败: 原因]，不影响其它文件。

抽取链（沿用 downloads_triage/content.py 验证过的回退顺序，但全文不截断）：
  .pdf            → pdftotext 全页；无文本层(扫描件) → macOS Vision OCR 兜底
  .doc/.docx      → textutil；空/乱码 → pandoc 回退
  .xlsx/.xls      → pandas 全 sheet（每 sheet 上限 20000 行，超出标注）
  .pptx           → python-pptx 全 slide（文本框 + 表格）
  其它            → 试 utf-8/gb18030 解码；含 NUL 字节判二进制 → [二进制，跳过]
"""
import subprocess
import os
import json
import sys
from pathlib import Path

SEP = "\n-----------------------------------\n"
XLSX_ROW_CAP = 20000   # 每 sheet 行上限，覆盖几千行台账；仅防病态超大表撑爆剪贴板
OCR_DIR = os.environ.get("MACKIT_OCR_DIR", "")
if not OCR_DIR:
    try:
        local_paths = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "mackit/paths.json"
        OCR_DIR = json.loads(local_paths.read_text()).get("ocr_dir", "")
    except (OSError, ValueError):
        pass
OCR_MAX_PAGES = 20     # 扫描件 OCR 页上限（~1-2s/页），防百页扫描件跑几分钟

# 直接当纯文本读的扩展名（代码/配置/标记/数据）
TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".htm", ".css",
    ".js", ".jsx", ".ts", ".tsx", ".py", ".lua", ".sh", ".bash", ".zsh", ".rb",
    ".go", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc", ".java", ".kt", ".swift",
    ".php", ".pl", ".sql", ".r", ".m", ".vim", ".env", ".gitignore", ".plist",
    ".srt", ".vtt", ".tex", ".bib", ".gradle", ".properties", ".dockerfile",
}


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          errors="replace")


def _looks_like_mojibake(text):
    """textutil 把旧版二进制 .doc(OLE/CDF) 当 plain text 误读出的乱码启发式。"""
    if not text:
        return False
    sample = text[:2000]
    bad = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\n\r\t")
    return bad > len(sample) * 0.05


def _read_plain(path):
    """试 utf-8 → gb18030 解码；NUL 字节 = 二进制。"""
    raw = Path(path).read_bytes()
    if b"\x00" in raw[:8192]:
        return None, "二进制，跳过"
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc), "ok"
        except UnicodeDecodeError:
            continue
    return None, "无法解码"


def _ocr_pdf(path):
    if not OCR_DIR:
        return ""
    """扫描件无文本层 → macOS Vision OCR 兜底。失败返回 ''，绝不 raise。"""
    try:
        if OCR_DIR not in sys.path:
            sys.path.insert(0, OCR_DIR)
        import vision_ocr
        res = vision_ocr.ocr_file(path, max_pages=OCR_MAX_PAGES)
        return (res.get("text") or "").strip() if res.get("ok") else ""
    except Exception:
        return ""


def _extract_pdf(path):
    r = _run(["pdftotext", "-layout", path, "-"])
    text = (r.stdout or "").strip()
    if text:
        return text, "ok"
    # 无文本层(扫描件) → Vision OCR 兜底
    ocr = _ocr_pdf(path)
    if ocr:
        return ocr, "ocr"
    return "", "无文本层且 OCR 未识别"


def _extract_doc(path):
    try:
        r = _run(["textutil", "-convert", "txt", "-stdout", path])
        text = (r.stdout or "").strip()
        if text and not _looks_like_mojibake(text):
            return text, "ok"
    except Exception:
        pass
    try:
        r = _run(["pandoc", "-t", "plain", path])
        text = (r.stdout or "").strip()
        if text and not _looks_like_mojibake(text):
            return text, "ok"
    except Exception as e:
        return "", str(e)
    return "", "旧版二进制 .doc 无可读文本"


def _extract_xlsx(path):
    try:
        import pandas as pd
    except Exception as e:
        return "", f"pandas 不可用: {e}"
    try:
        xl = pd.ExcelFile(path)
    except Exception as e:
        return "", str(e)
    parts = []
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=0, dtype=str)
        except Exception:
            continue
        n = len(df)
        capped = n > XLSX_ROW_CAP
        if capped:
            df = df.head(XLSX_ROW_CAP)
        head = f"# [{sheet}]" + (f"  (共 {n} 行，截前 {XLSX_ROW_CAP})" if capped else f"  ({n} 行)")
        parts.append(head)
        parts.append(df.to_csv(index=False).rstrip())
    text = "\n\n".join(parts).strip()
    return (text, "ok") if text else ("", "空表")


def _extract_pptx(path):
    try:
        from pptx import Presentation
    except Exception as e:
        return "", f"python-pptx 不可用: {e}"
    try:
        prs = Presentation(path)
    except Exception as e:
        return "", str(e)
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        lines = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    s = "".join(run.text for run in para.runs).rstrip()
                    if s.strip():
                        lines.append(s)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        lines.append(" | ".join(cells))
        if lines:
            parts.append(f"# Slide {i}\n" + "\n".join(lines))
    text = "\n\n".join(parts).strip()
    return (text, "ok") if text else ("", "无文本")


def extract(path):
    """返回 (text, reason)。reason=='ok' 表示成功。绝不 raise。"""
    try:
        p = Path(path)
        if not p.exists():
            return "", "文件不存在"
        if p.is_dir():
            return "", "是目录"
        ext = p.suffix.lower()
        if ext == ".pdf":
            return _extract_pdf(str(p))
        if ext in (".doc", ".docx"):
            return _extract_doc(str(p))
        if ext in (".xlsx", ".xls", ".xlsm"):
            return _extract_xlsx(str(p))
        if ext == ".pptx":
            return _extract_pptx(str(p))
        if ext in TEXT_EXTS:
            text, reason = _read_plain(str(p))
            return (text or "", reason)
        # 未知扩展名：试当文本读（含 NUL 即二进制跳过）
        text, reason = _read_plain(str(p))
        return (text or "", reason)
    except Exception as e:  # 契约：绝不 raise
        return "", str(e)


def main(argv):
    paths = argv[1:]
    if not paths:
        print("用法: extract_text.py <file> [file ...]", file=sys.stderr)
        return 2
    blocks, ok = [], 0
    for path in paths:
        name = Path(path).name
        text, reason = extract(path)
        if reason in ("ok", "ocr") and text.strip():
            tag = "（OCR 识别，可能有误差）" if reason == "ocr" else ""
            blocks.append(f"文件名：{name}{tag}\n\n{text.rstrip()}")
            ok += 1
        else:
            blocks.append(f"文件名：{name}\n\n[抽取失败: {reason}]")
    sys.stdout.write(SEP.join(blocks) + SEP)
    # 退出码 = 成功数（0 表示全失败，供 Lua 判断）
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
