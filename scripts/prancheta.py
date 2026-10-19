#!/usr/bin/env python3
"""
Reels "Prancheta do lance": recria um lance famoso em animação 2D estilo prancheta tática
(1080x1920, 30 fps). Conteúdo 100% próprio: sem imagem, vídeo, escudo ou logo de ninguém.

Uso:
    python scripts/prancheta.py assets/lances/maradona-1986.json saida/reels.mp4

Formato do lance (JSON) — coordenadas em metros do campo: x = 0..68 (largura), y = 0..105
(comprimento), com o gol ATACADO no topo (y = 0). Só o trecho y_min..y_max aparece na tela.
{
  "titulo": "O GOL DO SÉCULO",            "selo": "LANCE HISTÓRICO",
  "y_max": 75,                            "duracao": 16,
  "jogadores": [
     {"id": "heroi", "nome": "Maradona", "time": "a", "heroi": true,
      "pontos": [[0, 34, 62], [3, 40, 50], ...]},            # [tempo_s, x, y]
     {"id": "d1", "time": "b", "pontos": [[0, 33, 58], [2, 34, 57]]}
  ],
  "bola": [[0, 34, 61], ...],             # [tempo_s, x, y]
  "textos": [[0, 2.5, "Copa de 1986"], ...],   # [início, fim, texto] (legenda de baixo)
  "final": "Qual lance a gente desenha na próxima? Comenta!"   # tela final
}
ffmpeg: variável FFMPEG, senão imageio_ffmpeg, senão o "ffmpeg" do PATH.
"""
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carrossel as c

W, H, FPS = 1080, 1920, 30
CAMPO_X0, CAMPO_X1 = 70, 1010          # área do campo na tela
CAMPO_Y0, CAMPO_Y1 = 330, 1560
GRAMA_1, GRAMA_2 = (22, 101, 52), (20, 92, 48)
LINHA = (235, 245, 238)
COR_A, COR_B = c.VERDE, c.BRANCO       # time do herói / adversário
FINAL_S = 3.0                          # tela final


def ffmpeg_exe() -> str:
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


class Tela:
    def __init__(self, y_max):
        self.y_max = y_max
        self.esc = min((CAMPO_X1 - CAMPO_X0) / 68, (CAMPO_Y1 - CAMPO_Y0) / (y_max + 4))
        self.ox = (W - 68 * self.esc) / 2
        self.oy = CAMPO_Y0 + 4 * self.esc   # 4 m de folga atrás do gol

    def p(self, x, y):
        return self.ox + x * self.esc, self.oy + y * self.esc


def interp(pontos, t):
    if t <= pontos[0][0]:
        return pontos[0][1], pontos[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(pontos, pontos[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1
            k = k * k * (3 - 2 * k)  # suaviza (ease in/out)
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    return pontos[-1][1], pontos[-1][2]


def fundo(lance, tela):
    img = Image.new("RGB", (W, H), c.NOITE)
    d = ImageDraw.Draw(img)
    # faixas de grama
    x0, y_top = tela.p(-2, -4)
    x1, y_bot = tela.p(70, lance["y_max"])
    faixa = 10 * tela.esc
    y = y_top
    i = 0
    while y < y_bot:
        d.rectangle((x0, y, x1, min(y + faixa, y_bot)), fill=GRAMA_1 if i % 2 == 0 else GRAMA_2)
        y += faixa
        i += 1
    lw = max(3, int(tela.esc * 0.18))

    def ln(a, b):
        d.line([tela.p(*a), tela.p(*b)], fill=LINHA, width=lw)

    def ret(xa, ya, xb, yb):
        d.rectangle((*tela.p(xa, ya), *tela.p(xb, yb)), outline=LINHA, width=lw)

    ln((0, 0), (68, 0))
    ln((0, 0), (0, lance["y_max"]))
    ln((68, 0), (68, lance["y_max"]))
    ret(13.84, 0, 54.16, 16.5)                # grande área
    ret(24.84, 0, 43.16, 5.5)                 # pequena área
    gx0, gy0 = tela.p(30.34, -2.2)
    gx1, gy1 = tela.p(37.66, 0)
    d.rectangle((gx0, gy0, gx1, gy1), outline=LINHA, width=lw)  # gol
    px, py = tela.p(34, 11)
    d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=LINHA)      # marca do pênalti
    ax0, ay0 = tela.p(34 - 9.15, 11 - 9.15)
    ax1, ay1 = tela.p(34 + 9.15, 11 + 9.15)
    d.arc((ax0, ay0, ax1, ay1), 37, 143, fill=LINHA, width=lw)   # meia-lua
    if lance["y_max"] >= 52.5:
        ln((0, 52.5), (68, 52.5))
        cx0, cy0 = tela.p(34 - 9.15, 52.5 - 9.15)
        cx1, cy1 = tela.p(34 + 9.15, 52.5 + 9.15)
        d.ellipse((cx0, cy0, cx1, cy1), outline=LINHA, width=lw)
    # degradê no fim do campo visível (sugere que continua)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    for k in range(120):
        a = int(255 * (k / 120) ** 1.6)
        ds.line([(0, y_bot - 120 + k), (W, y_bot - 120 + k)], fill=c.NOITE + (a,))
    img.paste(sombra, (0, 0), sombra)
    d = ImageDraw.Draw(img)
    d.rectangle((0, y_bot, W, H), fill=c.NOITE)
    # cabeçalho
    fs = c.fonte("Inter-Black.otf", 32)
    selo = lance.get("selo", "LANCE HISTÓRICO")
    lw2 = d.textlength(selo, font=fs) + 50
    d.rounded_rectangle(((W - lw2) / 2, 70, (W + lw2) / 2, 128), radius=29, fill=c.VERDE)
    d.text(((W - d.textlength(selo, font=fs)) / 2, 80), selo, font=fs, fill=c.NOITE)
    f, linhas = c.ajusta(d, lance["titulo"].upper(), "Anton-Regular.ttf", 110, 70, W - 120, 2)
    yy = 150
    for t in linhas:
        d.text(((W - d.textlength(t, font=f)) / 2, yy), t, font=f, fill=c.BRANCO)
        yy += f.size * 1.02
    # rodapé
    logo = Image.open(c.LOGO).convert("RGBA").resize((64, 64), Image.LANCZOS)
    fa = c.fonte("Inter-Bold.otf", 32)
    tw = d.textlength(c.ARROBA, font=fa)
    lx = (W - (64 + 16 + tw)) / 2
    img.paste(logo, (int(lx), H - 140), logo)
    d.text((lx + 80, H - 128), c.ARROBA, font=fa, fill=c.BRANCO)
    return img


def legenda(d, texto):
    f, linhas = c.ajusta(d, texto, "Inter-Black.otf", 56, 40, W - 200, 2)
    alt = len(linhas) * f.size * 1.2
    larg = max(d.textlength(t, font=f) for t in linhas)
    y0 = 1640
    d.rounded_rectangle(((W - larg) / 2 - 34, y0 - 20, (W + larg) / 2 + 34, y0 + alt + 12),
                        radius=26, fill=c.VERDE)
    y = y0
    for t in linhas:
        d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=c.NOITE)
        y += f.size * 1.2


def quadro(base, lance, tela, t, trilha):
    img = base.copy()
    d = ImageDraw.Draw(img, "RGBA")
    r = max(20, int(tela.esc * 1.75))
    # trilha do herói (tracejada)
    for i in range(1, len(trilha), 2):
        d.line([trilha[i - 1], trilha[i]], fill=(250, 214, 60, 235), width=9)
    for j in lance["jogadores"]:
        x, y = tela.p(*interp(j["pontos"], t))
        heroi = j.get("heroi")
        cor = COR_A if j["time"] == "a" else COR_B
        rr = int(r * 1.15) if heroi else r
        d.ellipse((x - rr + 4, y - rr + 6, x + rr + 4, y + rr + 6), fill=(0, 0, 0, 90))
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=cor,
                  outline=(250, 214, 60) if heroi else c.NOITE, width=6 if heroi else 4)
        if j.get("nome"):
            fn = c.fonte("Inter-Black.otf", 30)
            tw = d.textlength(j["nome"], font=fn)
            d.rounded_rectangle((x - tw / 2 - 14, y - rr - 56, x + tw / 2 + 14, y - rr - 12),
                                radius=12, fill=c.NOITE + (235,))
            d.text((x - tw / 2, y - rr - 52), j["nome"], font=fn, fill=c.BRANCO)
    bx, by = tela.p(*interp(lance["bola"], t))
    rb = max(11, int(r * 0.5))
    d.ellipse((bx - rb + 3, by - rb + 4, bx + rb + 3, by + rb + 4), fill=(0, 0, 0, 110))
    d.ellipse((bx - rb, by - rb, bx + rb, by + rb), fill=c.BRANCO, outline=c.NOITE, width=3)
    for ini, fim, texto in lance["textos"]:
        if ini <= t < fim:
            legenda(d, texto)
            break
    return img


def tela_final(lance):
    img = Image.new("RGB", (W, H), c.VERDE)
    d = ImageDraw.Draw(img)
    logo = Image.open(c.LOGO).convert("RGBA").resize((240, 240), Image.LANCZOS)
    borda = Image.new("RGBA", (264, 264), (0, 0, 0, 0))
    ImageDraw.Draw(borda).rounded_rectangle((0, 0, 263, 263), radius=64, fill=c.BRANCO)
    img.paste(borda, ((W - 264) // 2, 520), borda)
    img.paste(logo, ((W - 240) // 2, 532), logo)
    f, linhas = c.ajusta(d, lance.get("final", "Qual lance a gente desenha na próxima?").upper(),
                         "Anton-Regular.ttf", 100, 66, W - 160, 4)
    y = 860
    for t in linhas:
        d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=c.NOITE)
        y += f.size * 1.05
    fb = c.fonte("Inter-Black.otf", 42)
    txt = "COMENTA AÍ"
    bw = d.textlength(txt, font=fb) + 110
    d.rounded_rectangle(((W - bw) / 2, y + 50, (W + bw) / 2, y + 156), radius=53, fill=c.NOITE)
    d.text(((W - d.textlength(txt, font=fb)) / 2, y + 77), txt, font=fb, fill=c.BRANCO)
    fa = c.fonte("Inter-Bold.otf", 34)
    d.text(((W - d.textlength(c.ARROBA, font=fa)) / 2, H - 190), c.ARROBA, font=fa, fill=c.NOITE)
    return img


def gera(caminho_lance, saida):
    lance = json.loads(Path(caminho_lance).read_text(encoding="utf-8"))
    tela = Tela(lance["y_max"])
    base = fundo(lance, tela)
    heroi = next(j for j in lance["jogadores"] if j.get("heroi"))
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    dur = float(lance["duracao"])
    n = int(dur * FPS)
    cmd = [ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(saida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    trilha = []
    capa = None
    for i in range(n):
        t = i / FPS
        if i % 3 == 0:
            trilha.append(tela.p(*interp(heroi["pontos"], t)))
        img = quadro(base, lance, tela, t, trilha)
        if capa is None and t >= 1.0:
            capa = img
        proc.stdin.write(img.tobytes())
    fim = tela_final(lance).tobytes()
    for _ in range(int(FINAL_S * FPS)):
        proc.stdin.write(fim)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg falhou")
    (capa or base).save(saida.parent / "capa.jpg", quality=90)
    print(saida)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    gera(sys.argv[1], sys.argv[2])
