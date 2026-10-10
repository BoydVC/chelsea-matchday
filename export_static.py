#!/usr/bin/env python3
"""Write dist/chelsea-matchday-snapshot.html: one offline file (CSS, JS, fonts, match + research inlined)."""
import base64, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "web")


def main():
    rd = lambda n: open(os.path.join(W, n), encoding="utf-8").read()
    html, css, js = rd("index.html"), rd("style.css"), rd("app.js")
    css = re.sub(
        r'url\("(fonts/[^"]+)"\)',
        lambda m: 'url("data:font/ttf;base64,' + base64.b64encode(open(os.path.join(W, m.group(1)), "rb").read()).decode() + '")',
        css,
    )
    data = json.load(open(os.path.join(HERE, "data", "match.json"), encoding="utf-8"))
    research = {}
    rp = os.path.join(HERE, "data", "research_notes.json")
    if os.path.exists(rp):
        research = json.load(open(rp, encoding="utf-8"))
    html = html.replace('<link rel="stylesheet" href="style.css">', "<style>\n" + css + "\n</style>")
    html = html.replace("<!--MATCHDATA-->", "<script>window.__MATCH__=" + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";</script>")
    html = html.replace("<!--RESEARCH-->", "<script>window.__RESEARCH__=" + json.dumps(research, ensure_ascii=False).replace("</", "<\\/") + ";</script>")
    html = html.replace('<script src="app.js"></script>', "<script>\n" + js.replace("</script", "<\\/script") + "\n</script>")
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    out = os.path.join(HERE, "dist", "chelsea-matchday-snapshot.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out} ({os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
