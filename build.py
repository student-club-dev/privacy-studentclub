#!/usr/bin/env python3
"""Builds the Student Club legal site from content/<lang>/<doc>.md.

    python3 build.py                 # writes <lang>/*.html, index.html and the legacy pages
    python3 build.py --sync-app DIR  # also copies terms/privacy markdown into the app's
                                     # composeResources/files/legal (DIR), so the app and the
                                     # site always show the same text

No third-party packages: the markdown subset (headings, paragraphs, lists, tables, bold,
blockquotes) is the same one the app's LegalSheet understands.
"""
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
LANGS = ["uz", "ru", "en"]
DOCS = ["privacy"]
APP_DOCS = ["privacy"]
EMAIL_ADDR = "quvonchbekgafurov07@gmail.com"

UI = {
    "uz": {
        "html_lang": "uz",
        "brand": "Student Club",
        "tagline": "Huquqiy hujjatlar",
        "home_title": "Student Club - hujjatlar",
        "home_lead": "Student Club - O'zbekiston universitetlari talabalarini bog'laydigan mobil ilova. Bu yerda ma'lumotlaringiz qanday yig'ilishi va himoyalanishi hamda bolalar xavfsizligi qoidalari bilan tanishishingiz mumkin.",
        "nav": {"privacy": "Maxfiylik siyosati", "child": "Bolalar xavfsizligi"},
        "desc": {
            "privacy": "Qanday ma'lumot yig'iladi, qanday himoyalanadi va huquqlaringiz.",
            "child": "Bolalarni himoya qilish standartlari va qanday xabar berish.",
        },
        "toc": "Mundarija",
        "print": "Chop etish / PDF",
        "open": "Ochish",
        "operator": "Operator: YaTT Qo'shshayev Qahhor G'afurovich",
    },
    "ru": {
        "html_lang": "ru",
        "brand": "Student Club",
        "tagline": "Правовые документы",
        "home_title": "Student Club - документы",
        "home_lead": "Student Club - мобильное приложение, объединяющее студентов вузов Узбекистана. Здесь собраны сведения о том, как собираются и защищаются ваши данные, и стандарты безопасности детей.",
        "nav": {"privacy": "Политика конфиденциальности", "child": "Безопасность детей"},
        "desc": {
            "privacy": "Какие данные собираются, как защищаются и ваши права.",
            "child": "Стандарты защиты детей и как сообщить о нарушении.",
        },
        "toc": "Содержание",
        "print": "Печать / PDF",
        "open": "Открыть",
        "operator": "Оператор: ИП Qo'shshayev Qahhor G'afurovich",
    },
    "en": {
        "html_lang": "en",
        "brand": "Student Club",
        "tagline": "Legal documents",
        "home_title": "Student Club - documents",
        "home_lead": "Student Club is a mobile app that connects university students in Uzbekistan. Here you can read how your data is collected and protected, and our child safety standards.",
        "nav": {"privacy": "Privacy Policy", "child": "Child Safety"},
        "desc": {
            "privacy": "What data we collect, how we protect it and your rights.",
            "child": "Child protection standards and how to report a concern.",
        },
        "toc": "Contents",
        "print": "Print / PDF",
        "open": "Open",
        "operator": "Operator: Sole proprietor Qo'shshayev Qahhor G'afurovich",
    },
}

LANG_LABEL = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}

# Old URLs already registered in App Store Connect and Play Console: keep them serving full pages.
LEGACY = {"privacy.html": ("en", "privacy")}


# ---------- markdown ----------

EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
BOLD = re.compile(r"\*\*(.+?)\*\*")
PLACEHOLDER = re.compile(r"\[([^\]]+)\](?!\()")


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = BOLD.sub(r"<strong>\1</strong>", out)
    out = PLACEHOLDER.sub(r'<mark class="todo">[\1]</mark>', out)
    out = EMAIL.sub(r'<a href="mailto:\1">\1</a>', out)
    return out


def slug(text: str, used: set) -> str:
    base = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-") or "s"
    s, n = base, 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def render(md: str):
    """Returns (title, body_html, toc[(id, text)])."""
    title, parts, toc, used = "", [], [], set()
    para, items, table = [], [], []

    def flush_para():
        if para:
            parts.append("<p>" + "<br>\n".join(inline(l) for l in para) + "</p>")
            para.clear()

    def flush_list():
        if items:
            parts.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    def flush_table():
        if table:
            rows = [r for r in table if not all(re.fullmatch(r":?-+:?", c) for c in r if c)]
            head, body = rows[0], rows[1:]
            h = "".join(f"<th>{inline(c)}</th>" for c in head)
            b = "".join("<tr>" + "".join(f'<td data-label="{html.escape(head[i] if i < len(head) else "")}">{inline(c)}</td>' for i, c in enumerate(r)) + "</tr>" for r in body)
            parts.append(f'<div class="table"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
            table.clear()

    def flush_all():
        flush_para(); flush_list(); flush_table()

    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            flush_all()
        elif line.startswith("# "):
            flush_all(); title = line[2:].strip()
        elif line.startswith("---"):
            flush_all()
        elif line.startswith("### "):
            flush_all()
            parts.append(f'<h3 id="{slug(line[4:], used)}">{inline(line[4:])}</h3>')
        elif line.startswith("## "):
            flush_all()
            hid = slug(line[3:], used)
            toc.append((hid, line[3:]))
            parts.append(f'<h2 id="{hid}">{inline(line[3:])}</h2>')
        elif line.startswith("> "):
            flush_all(); parts.append(f'<p class="note">{inline(line[2:])}</p>')
        elif line.startswith("- "):
            flush_para(); flush_table(); items.append(line[2:])
        elif line.startswith("|"):
            flush_para(); flush_list()
            table.append([c.strip() for c in line.strip("|").split("|")])
        else:
            flush_list(); flush_table(); para.append(line)
    flush_all()
    return title, "\n".join(parts), toc


# ---------- page shell ----------

def page(lang, current, title, body, prefix, alt_paths, description):
    ui = UI[lang]
    cur_page, cur_lang = ' aria-current="page"', ' aria-current="true"'
    nav = "".join(
        f'<a href="{prefix}{lang}/{d}.html"{cur_page if d == current else ""}>{ui["nav"][d]}</a>'
        for d in DOCS
    ) + f'<a href="{prefix}child-safety.html">{ui["nav"]["child"]}</a>'
    langs = "".join(
        f'<a href="{prefix}{alt_paths[l]}" lang="{l}"{cur_lang if l == lang else ""}>{l.upper()}</a>'
        for l in LANGS
    )
    hreflang = "".join(f'<link rel="alternate" hreflang="{l}" href="{prefix}{alt_paths[l]}">' for l in LANGS)
    footer_links = " · ".join([f'<a href="{prefix}{lang}/{d}.html">{ui["nav"][d]}</a>' for d in DOCS] + [f'<a href="{prefix}child-safety.html">{ui["nav"]["child"]}</a>'])
    return f"""<!doctype html>
<html lang="{ui['html_lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="theme-color" content="#14532d">
{hreflang}
<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap bar">
    <a class="brand" href="{prefix}{lang}/index.html"><span class="dot"></span>{ui['brand']}</a>
    <nav class="langs" aria-label="Language">{langs}</nav>
  </div>
  <div class="wrap"><nav class="tabs" aria-label="Documents">{nav}</nav></div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
  <p>{footer_links}</p>
  <p>{ui['operator']} · <a href="mailto:{EMAIL_ADDR}">{EMAIL_ADDR}</a></p>
  <p>© 2026 Student Club</p>
</footer>
</body>
</html>
"""


def doc_body(lang, title, body, toc):
    ui = UI[lang]
    toc_html = ""
    if len(toc) > 3:
        toc_html = (f'<details class="toc" open><summary>{ui["toc"]}</summary><ol>'
                    + "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in toc)
                    + "</ol></details>")
    return (f'<article class="doc"><div class="doc-head"><h1>{html.escape(title)}</h1>'
            f'<button class="print" type="button" onclick="window.print()">{ui["print"]}</button></div>'
            f"{toc_html}{body}</article>")


def home_body(lang):
    ui = UI[lang]
    cards = "".join(
        f'<a class="card" href="{d}.html"><strong>{ui["nav"][d]}</strong><span>{ui["desc"][d]}</span><em>{ui["open"]} →</em></a>'
        for d in DOCS
    ) + f'<a class="card" href="../child-safety.html"><strong>{ui["nav"]["child"]}</strong><span>{ui["desc"]["child"]}</span><em>{ui["open"]} →</em></a>'
    return (f'<section class="hero"><h1>{ui["home_title"]}</h1><p>{ui["home_lead"]}</p></section>'
            f'<section class="cards">{cards}</section>')


def build():
    written = []
    for lang in LANGS:
        out = ROOT / lang
        out.mkdir(exist_ok=True)
        for d in DOCS:
            title, body, toc = render((CONTENT / lang / f"{d}.md").read_text(encoding="utf-8"))
            alts = {l: f"{l}/{d}.html" for l in LANGS}
            (out / f"{d}.html").write_text(
                page(lang, d, f"{title} - Student Club", doc_body(lang, title, body, toc), "../", alts, UI[lang]["desc"][d]),
                encoding="utf-8")
            written.append(f"{lang}/{d}.html")
        alts = {l: f"{l}/index.html" for l in LANGS}
        (out / "index.html").write_text(
            page(lang, None, UI[lang]["home_title"], home_body(lang), "../", alts, UI[lang]["home_lead"]), encoding="utf-8")
        written.append(f"{lang}/index.html")

    for name, (lang, d) in LEGACY.items():
        title, body, toc = render((CONTENT / lang / f"{d}.md").read_text(encoding="utf-8"))
        alts = {l: f"{l}/{d}.html" for l in LANGS}
        (ROOT / name).write_text(
            page(lang, d, f"{title} - Student Club", doc_body(lang, title, body, toc), "", alts, UI[lang]["desc"][d]),
            encoding="utf-8")
        written.append(name)

    (ROOT / "index.html").write_text(ROOT_INDEX, encoding="utf-8")
    (ROOT / "404.html").write_text(ROOT_INDEX, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    written += ["index.html", "404.html"]
    return written


ROOT_INDEX = """<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student Club</title>
<script>
  (function () {
    var l = (navigator.language || "uz").slice(0, 2).toLowerCase();
    var lang = l === "ru" ? "ru" : l === "en" ? "en" : "uz";
    var base = /github\.io$/.test(location.hostname) ? "/" + location.pathname.split("/")[1] + "/" : "/";
    location.replace(base + lang + "/index.html");
  })();
</script>
</head>
<body>
<main class="wrap">
  <h1>Student Club</h1>
  <p><a href="uz/index.html">O'zbekcha</a> · <a href="ru/index.html">Русский</a> · <a href="en/index.html">English</a></p>
</main>
</body>
</html>
"""


def sync_app(target: Path):
    for lang in ["uz", "ru", "en"]:
        for d in APP_DOCS:
            shutil.copyfile(CONTENT / lang / f"{d}.md", target / f"{d}_{lang}.md")
            print("app:", target / f"{d}_{lang}.md")


if __name__ == "__main__":
    for f in build():
        print("site:", f)
    if "--sync-app" in sys.argv:
        sync_app(Path(sys.argv[sys.argv.index("--sync-app") + 1]).expanduser())
