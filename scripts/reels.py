#!/usr/bin/env python3
"""
Monta um Reels (1080x1920, até 30s) a partir de uma gravação de tela do app.

Uso:
    python3 scripts/reels.py posts/2026-10-22-sorteio/post.json

Campos do post.json usados:
    "video_base": "gravacoes/sorteio-times.mp4"   (caminho a partir da raiz do repo)
    "gancho":     "Sorteio de time sem briga?"   (texto do topo, aparece o vídeo todo)
    "legendas":   [ {"de": 0, "ate": 3, "texto": "Abre a pelada"}, ... ]  (textos do rodapé)
    "cta":        "Link na bio"                   (tela final de 2,5s)
    "inicio": 0, "duracao": 25                    (opcional: corte da gravação, em segundos)
Saída: reels.mp4 e capa.jpg na pasta do post.json.

Layout: fundo azul-noite, gravação centralizada (cantos arredondados), gancho grande
em cima, legenda verde embaixo, logo + @ no rodapé e tela final verde com o CTA.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carrossel as c  # reaproveita cores, fontes e quebra de linha

W, H = 1080, 1920
TELA_W = 640  # largura da gravação dentro do Reels


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise SystemExit(f"ffmpeg falhou: {' '.join(cmd[:6])}...")
    return r.stdout


def duracao_video(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


def moldura(gancho, tmp):
    """PNG transparente com fundo, gancho e rodapé; a gravação fica por baixo do 'buraco'."""
    img = Image.new("RGBA", (W, H), c.NOITE + (255,))
    d = ImageDraw.Draw(img)
    f, linhas = c.ajusta(d, gancho.upper(), "Anton-Regular.ttf", 110, 64, W - 160, 3)
    y = 150
    for ln in linhas:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=c.BRANCO)
        y += f.size * 1.05
    logo = Image.open(c.LOGO).convert("RGBA").resize((70, 70), Image.LANCZOS)
    fa = c.fonte("Inter-Bold.otf", 34)
    tw = d.textlength(c.ARROBA, font=fa)
    x0 = (W - (70 + 18 + tw)) / 2
    img.paste(logo, (int(x0), H - 150), logo)
    d.text((x0 + 88, H - 138), c.ARROBA, font=fa, fill=c.BRANCO)
    p = Path(tmp) / "moldura.png"
    img.save(p)
    return p


def legenda_png(texto, tmp, i):
    img = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f, linhas = c.ajusta(d, texto, "Inter-Black.otf", 58, 40, W - 200, 2)
    alt = len(linhas) * f.size * 1.2
    larg = max(d.textlength(ln, font=f) for ln in linhas)
    y0 = (260 - alt) / 2
    d.rounded_rectangle(((W - larg) / 2 - 36, y0 - 22, (W + larg) / 2 + 36, y0 + alt + 14),
                        radius=28, fill=c.VERDE + (255,))
    y = y0
    for ln in linhas:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=c.NOITE)
        y += f.size * 1.2
    p = Path(tmp) / f"leg{i}.png"
    img.save(p)
    return p


def tela_final(cta, tmp):
    img = Image.new("RGB", (W, H), c.VERDE)
    d = ImageDraw.Draw(img)
    logo = Image.open(c.LOGO).convert("RGBA").resize((260, 260), Image.LANCZOS)
    borda = Image.new("RGBA", (284, 284), (0, 0, 0, 0))
    ImageDraw.Draw(borda).rounded_rectangle((0, 0, 283, 283), radius=70, fill=c.BRANCO)
    img.paste(borda, ((W - 284) // 2, 488), borda)
    img.paste(logo, ((W - 260) // 2, 500), logo)
    f, linhas = c.ajusta(d, "ORGANIZA TUA PELADA", "Anton-Regular.ttf", 120, 80, W - 160, 2)
    y = 860
    for ln in linhas:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=c.NOITE)
        y += f.size * 1.05
    fb = c.fonte("Inter-Black.otf", 44)
    bw = d.textlength(cta.upper(), font=fb) + 120
    d.rounded_rectangle(((W - bw) / 2, y + 60, (W + bw) / 2, y + 170), radius=55, fill=c.NOITE)
    d.text(((W - d.textlength(cta.upper(), font=fb)) / 2, y + 88), cta.upper(), font=fb, fill=c.BRANCO)
    fa = c.fonte("Inter-Bold.otf", 36)
    d.text(((W - d.textlength(c.ARROBA, font=fa)) / 2, H - 200), c.ARROBA, font=fa, fill=c.NOITE)
    p = Path(tmp) / "final.png"
    img.save(p)
    return p


def mascara_cantos(w, h, tmp):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=40, fill=255)
    p = Path(tmp) / "mask.png"
    m.save(p)
    return p


def gera(caminho_json):
    caminho = Path(caminho_json)
    post = json.loads(caminho.read_text(encoding="utf-8"))
    base = c.RAIZ / post["video_base"]
    inicio = float(post.get("inicio", 0))
    dur = float(post.get("duracao", min(27, duracao_video(base) - inicio)))
    dur = min(dur, 27)  # + 2,5s da tela final = até ~30s
    legendas = post.get("legendas", [])
    saida = caminho.parent / "reels.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        mold = moldura(post["gancho"], tmp)
        final = tela_final(post.get("cta", "Link na bio"), tmp)
        legs = [legenda_png(lg["texto"], tmp, i) for i, lg in enumerate(legendas)]

        # altura da gravação mantendo proporção, limitada ao espaço útil
        probe = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                     "stream=width,height", "-of", "csv=p=0", str(base)]).strip().split(",")
        vw, vh = int(probe[0]), int(probe[1])
        tw = TELA_W
        th = int(tw * vh / vw) // 2 * 2
        if th > 1050:
            th = 1050
            tw = int(th * vw / vh) // 2 * 2
        mask = mascara_cantos(tw, th, tmp)
        tx, ty = (W - tw) // 2, 470

        inputs = ["-ss", str(inicio), "-t", str(dur), "-i", str(base), "-i", str(mold), "-i", str(mask)]
        for lp in legs:
            inputs += ["-i", str(lp)]
        fc = (f"[0:v]scale={tw}:{th},format=rgba[v];[2:v]format=gray,scale={tw}:{th}[m];"
              f"[v][m]alphamerge[vr];[1:v][vr]overlay={tx}:{ty}[b0]")
        ultimo = "b0"
        for i, lg in enumerate(legendas):
            fc += (f";[{ultimo}][{3 + i}:v]overlay=0:{ty + th - 40}:"
                   f"enable='between(t,{lg['de']},{lg['ate']})'[b{i + 1}]")
            ultimo = f"b{i + 1}"
        fc += f";[{ultimo}]fps=30,format=yuv420p[out]"
        parte1 = Path(tmp) / "p1.mp4"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(parte1)])

        parte2 = Path(tmp) / "p2.mp4"
        run(["ffmpeg", "-y", "-loop", "1", "-t", "2.5", "-i", str(final), "-vf", "fps=30,format=yuv420p",
             "-c:v", "libx264", "-crf", "20", str(parte2)])

        lista = Path(tmp) / "lista.txt"
        lista.write_text(f"file '{parte1}'\nfile '{parte2}'\n")
        # áudio silencioso: o Instagram aceita melhor vídeo com faixa de áudio
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
             "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", str(saida)])

        run(["ffmpeg", "-y", "-ss", "1", "-i", str(saida), "-frames:v", "1", "-q:v", "3",
             str(caminho.parent / "capa.jpg")])
    print(saida)
    return saida


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    gera(sys.argv[1])
