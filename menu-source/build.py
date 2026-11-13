#!/usr/bin/env python3
"""Build a translated menu PDF: python3 menu-source/build.py ru  ->  assets/menu-ru.pdf

menu.json holds the dishes, numbers, prices and allergens (English).
lang/<code>.json holds one translation. Dish names stay in English on
every edition (staff take orders by number + English name); the
translation is printed underneath each dish, like the Greek on the
original menu. Needs Google Chrome (headless) and Pillow.
"""
import html, json, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent
BUILD = ROOT / "_build"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

e = html.escape


def load(lang):
    menu = json.loads((ROOT / "menu.json").read_text())
    tr = json.loads((ROOT / "lang" / f"{lang}.json").read_text())
    return menu, tr


def marks(it):
    m = [x for x, on in (("H", it.get("h")), ("N", it.get("nuts"))) if on]
    return f' <span class="mk">({",".join(m)})</span>' if m else ""


def al(it):
    return f' <span class="al">({it["al"]})</span>' if it.get("al") else ""


def new(it, ui):
    return f' <span class="new">{e(ui["new"])}</span>' if it.get("new") else ""


def item_html(it, tr):
    ui = tr["ui"]
    if "sub" in it:
        return (f'<div class="sub"><b>{e(it["name"])}</b>{marks(it)}'
                f'<div class="tr">{e(tr["subs"][it["sub"]])}</div></div>')
    num = it.get("num", it["n"])
    price = f'<span class="p">{it["price"]}</span>' if it.get("price") else ""
    extra = f' <span class="ex">{e(it["extra"])}</span>' if it.get("extra") else ""
    out = [f'<div class="it"><span class="n">{e(num) + "." if num else ""}</span><div class="b">'
           f'<div class="l1"><span class="nm">{e(it["name"])}</span>{marks(it)}{extra}{al(it)}{new(it, ui)}</div>'
           f'<div class="tr">{e(tr["items"][it["n"]])}</div>']
    for o in it.get("opts", []):
        label = tr["opts"][it["n"] + o["id"]]
        out.append(f'<div class="opt"><span><span class="ol">{e(o["label"])}</span> · <i>{e(label)}</i></span><span class="p">{o["price"]}</span></div>')
    out.append(f'</div>{price}</div>')
    return "".join(out)


def head(sid, sec, tr, euro=True):
    sub = tr.get("subtitles", {}).get(sid)
    subtitle = f'<div class="h-sub">{e(sec["subtitle"])} {e(sub)}</div>' if sub else ""
    return (f'<div class="h"><div class="h-en">{e(sec["title"])}</div>'
            f'<div class="h-tr">{e(tr["sections"][sid])}</div>{subtitle}</div>')


def section_html(sid, menu, tr):
    ui = tr["ui"]
    if sid == "info":
        return info_html(menu, tr)
    if sid == "legend":
        return (f'<div class="legend"><b>(H)</b> = {e(ui["hot"])} &nbsp;&nbsp; <b>(N)</b> = {e(ui["nuts"])}'
                f' &nbsp;&nbsp; <b>(1–14)</b> = {e(ui["allergens"].lower())}</div>')
    if sid == "pricesNote":
        return f'<div class="note">{e(ui["pricesNote"])}</div>'
    if sid == "allergens":
        lis = "".join(f"<li><b>{i}.</b> {e(a)}</li>" for i, a in enumerate(ui["allergenList"], 1))
        return (f'<div class="allergens"><div class="a-h">{e(ui["allergens"])} / Allergens</div>'
                f'<ol>{lis}</ol><div class="a-note">{e(ui["allergenNote"])}</div></div>')

    sec = menu["sections"][sid]
    kind = sec.get("type")
    body = []
    if kind == "sets":
        for s in sec["items"]:
            t = tr["sets"][s["n"]]
            lis = "".join(f"<li>{e(x)}</li>" for x in t["list"])
            body.append(f'<div class="set"><div class="set-h"><span><span class="set-en">{e(s["name"])}</span>'
                        f' · {e(t["t"])}</span><span class="p">€{s["price"]}</span></div><ul>{lis}</ul></div>')
        body = [f'<div class="sets">{"".join(body)}</div>']
    elif kind == "bowls":
        for b in sec["items"]:
            body.append(f'<div class="bowl"><div class="bowl-h"><span class="nm">{e(b["name"])}</span>{new(b, ui)}'
                        f'<span class="p">{b["price"]}</span></div>'
                        f'<div class="tr">{e(tr["items"][b["n"]])}</div><div class="al-line">{al(b)}</div></div>')
        body = [f'<div class="bowls">{"".join(body)}</div>']
    elif kind == "sushi":
        c, ts = sec["combo"], tr["sushi"]
        opts = "".join(f'<div class="opt"><span>{e(ts["comboOpt"].format(each=o["id"], pieces=o["pieces"]))}</span>'
                       f'<span class="p">€{o["price"]}</span></div>' for o in c["opts"])
        body.append(f'<div class="sub"><b>{e(c["name"])}</b> · {e(ts["combo"])}{al(c)}'
                    f'<div class="combo-rolls">{e(" · ".join(c["rolls"]))}</div>'
                    f'<div class="tr">{e(ts["comboIntro"])}</div>{opts}</div>')
        body.append(f'<div class="sub"><b>{e(ts["rolls"])}</b> <span class="ex">{e(ts["rollsSub"])}</span></div>')
        for r in sec["items"]:
            body.append(f'<div class="it roll"><div class="b"><div class="l1"><span class="nm">{e(r["name"])}</span></div>'
                        f'<div class="tr">{e(tr["items"][r["n"]])}</div></div><span class="p">{r["price"]}</span></div>')
    else:
        body = [item_html(it, tr) for it in sec["items"]]
    return f'<section class="s-{sid}">{head(sid, sec, tr)}{"".join(body)}</section>'


def info_html(menu, tr):
    """Header band at the top of page 1: logo, name, hours and contact details."""
    ui, inf = tr["ui"], menu["info"]
    rows = "".join(
        f'<tr><td>{e(ui[k])}</td><td>{e(v) if v else e(ui["closed"])}</td></tr>' for k, v in inf["hours"])
    return f'''<header class="info">
  <img class="logo" src="logo.png" alt="">
  <div class="i-brand">
    <div class="brand">The Flying Dragon</div>
    <div class="tagline">{e(ui["tagline"])}</div>
    <div class="edition">{e(ui["edition"])}</div>
  </div>
  <div class="hours"><div class="i-h">{e(ui["hoursTitle"])}</div><table>{rows}</table></div>
  <div class="contact">
    <div class="phone">☎ {e(inf["phone"])}</div>
    <div class="c-b">{e(ui["takeaway"])}</div>
    <div>{e(ui["freeDelivery"])}</div>
    <div>{e(ui["minOrder"].format(amount=inf["minOrder"]))}</div>
    <div class="c-b addr">{e(inf["address"])}</div>
    <div>({e(ui["addressNote"])})</div>
  </div>
  <img class="qr" src="qr-code.png" alt="">
</header>'''


def page_html(menu, tr):
    flow = "".join(section_html(s, menu, tr) for s in menu["order"])
    foot = section_html("legend", menu, tr) + section_html("pricesNote", menu, tr)
    font = tr.get("font", '"Helvetica Neue", Helvetica, Arial, sans-serif')
    css = (ROOT / "menu.css").read_text().replace("/*FONT*/", font)
    return (f'<!doctype html><html lang="{tr["lang"]}" dir="{tr.get("dir", "ltr")}"><head><meta charset="utf-8">'
            f'<style>{css}</style></head><body>{info_html(menu, tr)}{section_html("legend", menu, tr)}'
            f'<main class="flow">{flow}</main><footer>{foot}</footer></body></html>')


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "ru"
    menu, tr = load(lang)
    BUILD.mkdir(exist_ok=True)
    # Small copies of the images so the PDF stays light enough for phones.
    logo = Image.open(SITE / "assets" / "logo.png"); logo.thumbnail((700, 700)); logo.save(BUILD / "logo.png")
    Image.open(SITE / "assets" / "qr-code.png").save(BUILD / "qr-code.png")
    src = BUILD / f"menu-{lang}.html"
    src.write_text(page_html(menu, tr))
    out = SITE / "assets" / f"menu-{lang}.pdf"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True)
    print(f"wrote {out.relative_to(SITE)}")


if __name__ == "__main__":
    main()
