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

def test_map_layer_selection_and_legend_colors():
    html = (ROOT / "docs/karta.html").read_text(encoding="utf-8")
    # The common consultation action must use the same purple in map and legend.
    assert '.samrad{border-color:#a21caf}' in html
    assert 'if(value==="Annan skogsbruksåtgärd")return "#a21caf";' in html
    assert 'wantPlanned:document.getElementById("showPlanned").checked' in html
    assert 'wantPerformed:document.getElementById("showPerformed").checked' in html
    assert 'const plannedPromise=wantPlanned' in html
    assert 'const performedPromise=wantPerformed' in html
    assert 'getLayerForView(PLANNED,' in html
    assert 'getLayerForView(PERFORMED,' in html
    # A Samråd-only selection must still enter the separate optional layer path.
    assert 'const samradPromise=wantSamrad?Promise.all([' in html
    assert 'document.getElementById("showSamrad").addEventListener("change",()=>{applyVisibility();load()})' in html


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
    test_map_layer_selection_and_legend_colors()
    test_inline_javascript_syntax()
    print("Inline JavaScript syntax checks passed.")
