from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.current = None
        self.external = False
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.external = any(k.lower() == "src" for k, _ in attrs)
            self.current = [] if not self.external else None
    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "script":
            if self.current is not None:
                text = "".join(self.current).strip()
                if text:
                    self.parts.append(text)
            self.current = None
            self.external = False

def test_inline_javascript_syntax():
    for relative in ("docs/karta.html", "docs/utforda.html", "docs/index.html", "docs/historik.html"):
        parser = InlineScripts()
        parser.feed((ROOT / relative).read_text(encoding="utf-8"))
        for i, source in enumerate(parser.parts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as f:
                f.write(source)
                f.flush()
                subprocess.run(["node", "--check", f.name], check=True, capture_output=True, text=True)

if __name__ == "__main__":
    test_inline_javascript_syntax()
    print("Inline JavaScript syntax checks passed.")
