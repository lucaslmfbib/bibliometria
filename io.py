import unicodedata
from pathlib import Path
from typing import Optional, Union


def _normalize_header(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.strip().lower().replace("_", " ").split())


def _clean_bibtex_value(value: str) -> str:
    text = value.strip().strip(",").strip()
    if not text:
        return ""
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1].strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    text = text.replace("\n", " ").replace("\r", " ")
    return " ".join(text.split())


def _split_top_level(text: str, sep: str) -> list[str]:
    parts = []
    start = 0
    depth = 0
    in_quotes = False
    escaped = False

    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            continue
        if not in_quotes:
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(0, depth - 1)
            elif char == sep and depth == 0:
                parts.append(text[start:idx])
                start = idx + 1
    parts.append(text[start:])
    return parts


def _extract_bib_entries(raw_text: str):
    entries = []
    size = len(raw_text)
    idx = 0

    while idx < size:
        at_pos = raw_text.find("@", idx)
        if at_pos < 0:
            break

        open_pos = -1
        for pos in range(at_pos, size):
            if raw_text[pos] in "{(":
                open_pos = pos
                break
            if raw_text[pos] == "\n":
                break
        if open_pos < 0:
            idx = at_pos + 1
            continue

        entry_type = raw_text[at_pos + 1 : open_pos].strip().lower()
        opener = raw_text[open_pos]
        closer = "}" if opener == "{" else ")"

        depth = 1
        in_quotes = False
        escaped = False
        end_pos = open_pos + 1

        while end_pos < size and depth > 0:
            char = raw_text[end_pos]
            if escaped:
                escaped = False
                end_pos += 1
                continue
            if char == "\\":
                escaped = True
                end_pos += 1
                continue
            if char == '"':
                in_quotes = not in_quotes
                end_pos += 1
                continue
            if not in_quotes:
                if char == opener:
                    depth += 1
                elif char == closer:
                    depth -= 1
            end_pos += 1

        if depth != 0:
            break

        content = raw_text[open_pos + 1 : end_pos - 1].strip()
        entries.append((entry_type, content))
        idx = end_pos

    return entries


def _parse_bibtex_entry(entry_type: str, content: str):
    chunks = _split_top_level(content, ",")
    if not chunks:
        return {}

    entry_key = chunks[0].strip()
    row = {"entry_type": entry_type, "entry_key": entry_key}

    for chunk in chunks[1:]:
        if "=" not in chunk:
            continue
        field, value = chunk.split("=", 1)
        field_name = field.strip().lower()
        field_value = _clean_bibtex_value(value)
        if not field_name:
            continue
        row[field_name] = field_value

    author_raw = row.get("author")
    if author_raw:
        import re

        authors = [part.strip() for part in re.split(r"\s+and\s+", author_raw, flags=re.IGNORECASE) if part.strip()]
        row["author"] = "; ".join(authors)

    return row


def _load_bibtex(file_path: Path, encoding: Optional[str] = None):
    import pandas as pd

    read_encoding = encoding or "utf-8"
    raw_text = file_path.read_text(encoding=read_encoding, errors="ignore")

    entries = _extract_bib_entries(raw_text)
    rows = []
    for entry_type, content in entries:
        row = _parse_bibtex_entry(entry_type, content)
        if row:
            rows.append(row)

    if not rows:
        raise ValueError(f"Nenhuma entrada BibTeX válida encontrada em: {file_path}")

    return pd.DataFrame(rows)


def load_bibliography(
    path: Union[str, Path],
    encoding: Optional[str] = None,
    sheet_name: Union[str, int] = 0,
):
    """Carrega um arquivo CSV/Excel/BibTeX contendo registros bibliográficos.

    Colunas conhecidas são normalizadas para:
    - Authors
    - Title
    - Year
    - Journal
    - Keywords
    - Cited by
    - Abstract
    - DOI

    Demais colunas do arquivo original são preservadas.
    """
    import pandas as pd

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    ext = file_path.suffix.lower()
    if ext == ".csv":
        # sep=None habilita autodetecção de delimitador (vírgula, ponto e vírgula etc.)
        df = pd.read_csv(file_path, encoding=encoding, sep=None, engine="python")
    elif ext in (".xls", ".xlsx"):
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    elif ext == ".bib":
        df = _load_bibtex(file_path, encoding=encoding)
    else:
        # fallback por autodetecção
        try:
            df = pd.read_csv(file_path, encoding=encoding, sep=None, engine="python")
        except Exception:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            except Exception:
                df = _load_bibtex(file_path, encoding=encoding)

    df = df.rename(columns={c: str(c).strip() for c in df.columns})
    normalized_columns = {_normalize_header(c): c for c in df.columns}

    def try_get(names):
        for name in names:
            original = normalized_columns.get(_normalize_header(name))
            if original is not None:
                return df[original]
        return None

    mapped = {
        "Authors": try_get(
            [
                "authors",
                "author",
                "author(s)",
                "au",
                "autores",
            ]
        ),
        "Title": try_get(
            [
                "title",
                "document title",
                "article title",
                "titulo",
            ]
        ),
        "Year": try_get(
            [
                "year",
                "py",
                "publication year",
                "ano",
            ]
        ),
        "Journal": try_get(
            [
                "source title",
                "journal",
                "journal title",
                "booktitle",
                "book title",
                "publisher",
                "source",
                "periodico",
                "revista",
            ]
        ),
        "Keywords": try_get(
            [
                "author keywords",
                "keywords",
                "index keywords",
                "palavras-chave",
                "palavras chave",
            ]
        ),
        "Cited by": try_get(
            [
                "cited by",
                "times cited",
                "cited_by",
                "citedby",
                "citation count",
                "citations",
                "citado por",
            ]
        ),
        "Abstract": try_get(
            [
                "abstract",
                "summary",
                "resumo",
                "description",
                "ab",
            ]
        ),
        "DOI": try_get(
            [
                "doi",
                "document object identifier",
                "article doi",
                "id doi",
            ]
        ),
        "Entry Type": try_get(
            [
                "entry type",
                "entry_type",
            ]
        ),
        "Entry Key": try_get(
            [
                "entry key",
                "entry_key",
                "id",
            ]
        ),
    }

    out = pd.DataFrame()
    for canonical, series in mapped.items():
        if series is not None:
            out[canonical] = series

    canonical_set = set(out.columns)
    for col in df.columns:
        if col not in canonical_set:
            out[col] = df[col]

    if "Year" in out.columns:
        out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype("Int64")

    return out
