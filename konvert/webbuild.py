"""Сборка интерфейса из web/ в одну HTML-страницу.

    python -m konvert.webbuild --out dist

dist/index.html — самодостаточная страница с данными внутри: открывается двойным
кликом и выкладывается на любой статический хостинг без сервера.
"""
from __future__ import annotations

import argparse
import json
import os

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
TITLE = "Антифрод Конверт"
FONTS = ("https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;500;600&family=Unbounded:wght@600&display=swap")


def _read(name: str) -> str:
    with open(os.path.join(WEB, name), encoding="utf-8") as fh:
        return fh.read()


def render(results: dict | None = None, data_url: str | None = None, fragment: bool = False) -> str:
    """results — встроить данные в страницу; data_url — загрузить их по адресу при открытии.
    fragment=True — без <html>/<head>/<body>, для площадок, которые оборачивают страницу сами."""
    head = (f"<title>{TITLE}</title>\n"
            f'<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="stylesheet" href="{FONTS}">\n'
            f"<style>\n{_read('styles.css')}\n</style>\n")
    data = ""
    if results is not None:
        payload = json.dumps(results, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
        data = f"<script>window.__KONVERT__ = {payload};</script>\n"
    elif data_url:
        data = f"<script>window.__KONVERT_URL__ = {json.dumps(data_url)};</script>\n"
    body = f"{_read('body.html')}\n{data}<script>\n{_read('app.js')}\n</script>\n"
    if fragment:
        return head + body
    return ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{head}</head>\n<body>\n{body}</body>\n</html>\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Сборка статической версии интерфейса")
    ap.add_argument("--results", default="outputs/results.json")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    with open(args.results, encoding="utf-8") as fh:
        results = json.load(fh)
    os.makedirs(args.out, exist_ok=True)
    for name, fragment in (("index.html", False), ("artifact.html", True)):
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(results=results, fragment=fragment))
        print(f"{path}: {os.path.getsize(path) / 1e6:.2f} МБ")


if __name__ == "__main__":
    main()
