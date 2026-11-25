"""Monta a versão do painel para a página do claude.ai (artifact/index.html):
o mesmo corpo do index.html, sem o esqueleto <html>/<head>/<body>, que a
plataforma acrescenta ao publicar."""
from pathlib import Path
import re, shutil
R = Path(__file__).resolve().parent.parent
src = (R / "index.html").read_text()
corpo = src.split("<!--CONTEUDO-->")[1].split("<!--/CONTEUDO-->")[0]
cab = """<title>Painel Merc</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap">
<link rel="stylesheet" href="style.css">
"""
out = R / "artifact"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(cab + corpo)
for f in ["style.css", "charts.js", "projections.json", "METODOLOGIA.md"]:
    shutil.copy(R / f, out / f)
print("ok", out)
