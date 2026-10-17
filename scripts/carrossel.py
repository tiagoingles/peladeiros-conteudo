#!/usr/bin/env python3
"""
Gera os slides de um carrossel do Instagram (1080x1350) a partir de um post.json.

Uso:
    python3 scripts/carrossel.py posts/2026-10-20-cobranca/post.json

Formato do post.json (campo "slides"):
    [
      {"tipo": "capa",  "titulo": "O PIX DA PELADA", "subtitulo": "Todo mês a mesma novela"},
      {"tipo": "texto", "numero": "1", "titulo": "O 'te pago sexta'", "texto": "Sexta passou..."},
      {"tipo": "cta",   "titulo": "Chega de planilha", "texto": "Organiza tua pelada no app"}
    ]
Saída: slide-01.png, slide-02.png ... na mesma pasta do post.json.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "assets" / "fonts"
LOGO = RAIZ / "assets" / "brand" / "logo-bola.png"

W, H = 1080, 1350
MARGEM = 90

VERDE = (34, 197, 94)        # #22C55E
VERDE_ESC = (21, 128, 61)    # #15803D
NOITE = (15, 23, 42)         # #0F172A
NOITE_2 = (30, 41, 59)       # #1E293B
BRANCO = (255, 255, 255)
CINZA = (148, 163, 184)      # #94A3B8

ARROBA = "@peladeiros_de_respeito"
LINK = "pelada-pro-seven.vercel.app"


def fonte(nome, tam):
    return ImageFont.truetype(str(FONTES / nome), tam)


EMOJI = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200D]")


def quebra(draw, texto, f, largura):
    """Quebra o texto em linhas que caibam na largura (emojis são removidos: a fonte não tem)."""
    texto = EMOJI.sub("", texto).strip()
    linhas = []
    for paragrafo in texto.split("\n"):
        atual = ""
        for palavra in paragrafo.split():
            teste = f"{atual} {palavra}".strip()
            if draw.textlength(teste, font=f) <= largura:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def ajusta(draw, texto, nome_fonte, tam_max, tam_min, largura, max_linhas):
    """Diminui a fonte até o texto caber em max_linhas."""
    tam = tam_max
    while tam >= tam_min:
        f = fonte(nome_fonte, tam)
        linhas = quebra(draw, texto, f, largura)
        if len(linhas) <= max_linhas:
            return f, linhas
        tam -= 4
    f = fonte(nome_fonte, tam_min)
    return f, quebra(draw, texto, f, largura)


def escreve(draw, linhas, f, x, y, cor, entrelinha=1.12, centro=False):
    alt = f.size * entrelinha
    for linha in linhas:
        lx = x
        if centro:
            lx = (W - draw.textlength(linha, font=f)) / 2
        draw.text((lx, y), linha, font=f, fill=cor)
        y += alt
    return y


def fundo(cor_topo, cor_base):
    """Gradiente vertical + linhas de campo sutis."""
    img = Image.new("RGB", (W, H), cor_topo)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(cor_topo[i] + (cor_base[i] - cor_topo[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    # círculo central do campo, bem discreto
    sobre = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sobre)
    ds.ellipse((W - 420, H - 420, W + 260, H + 260), outline=(255, 255, 255, 18), width=6)
    ds.line([(0, H - 80), (W, H - 80)], fill=(255, 255, 255, 14), width=4)
    img.paste(sobre, (0, 0), sobre)
    return img


def rodape(img, d, total, idx, escuro=True):
    logo = Image.open(LOGO).convert("RGBA").resize((64, 64), Image.LANCZOS)
    img.paste(logo, (MARGEM, H - 120), logo)
    cor = BRANCO if escuro else NOITE
    d.text((MARGEM + 82, H - 108), ARROBA, font=fonte("Inter-Bold.otf", 30), fill=cor)
    if total > 1:
        txt = f"{idx}/{total}"
        f = fonte("Inter-Medium.otf", 28)
        d.text((W - MARGEM - d.textlength(txt, font=f), H - 106), txt, font=f, fill=CINZA if escuro else NOITE_2)


def slide_capa(s, idx, total):
    img = fundo(NOITE, NOITE_2)
    d = ImageDraw.Draw(img)
    largura = W - 2 * MARGEM
    # selo
    selo = s.get("selo", "PELADA")
    fs = fonte("Inter-Black.otf", 30)
    lw = d.textlength(selo.upper(), font=fs) + 48
    d.rounded_rectangle((MARGEM, 200, MARGEM + lw, 260), radius=30, fill=VERDE)
    d.text((MARGEM + 24, 212), selo.upper(), font=fs, fill=NOITE)
    # título
    f, linhas = ajusta(d, s["titulo"].upper(), "Anton-Regular.ttf", 150, 80, largura, 5)
    y = escreve(d, linhas, f, MARGEM, 320, BRANCO, 1.05)
    if s.get("subtitulo"):
        fsub, lsub = ajusta(d, s["subtitulo"], "Inter-Bold.otf", 48, 34, largura, 3)
        escreve(d, lsub, fsub, MARGEM, y + 40, VERDE, 1.25)
    if total > 1:
        d.text((MARGEM, H - 230), "ARRASTA PRO LADO  →", font=fonte("Inter-Black.otf", 30), fill=CINZA)
    rodape(img, d, total, idx)
    return img


def slide_texto(s, idx, total):
    img = fundo(NOITE, NOITE)
    d = ImageDraw.Draw(img)
    largura = W - 2 * MARGEM
    y = 190
    if s.get("numero"):
        fn = fonte("Anton-Regular.ttf", 200)
        d.text((MARGEM, y - 40), str(s["numero"]), font=fn, fill=VERDE)
        y += 230
    f, linhas = ajusta(d, s["titulo"], "Inter-Black.otf", 76, 50, largura, 4)
    y = escreve(d, linhas, f, MARGEM, y, BRANCO, 1.15)
    d.rectangle((MARGEM, y + 30, MARGEM + 120, y + 40), fill=VERDE)
    if s.get("texto"):
        ft, lt = ajusta(d, s["texto"], "Inter-Medium.otf", 46, 32, largura, 9)
        escreve(d, lt, ft, MARGEM, y + 80, (226, 232, 240), 1.4)
    rodape(img, d, total, idx)
    return img


def slide_cta(s, idx, total):
    img = fundo(VERDE, VERDE_ESC)
    d = ImageDraw.Draw(img)
    largura = W - 2 * MARGEM
    logo = Image.open(LOGO).convert("RGBA").resize((180, 180), Image.LANCZOS)
    # contorno branco para o logo destacar no verde
    borda = Image.new("RGBA", (196, 196), (0, 0, 0, 0))
    ImageDraw.Draw(borda).rounded_rectangle((0, 0, 195, 195), radius=48, fill=BRANCO)
    img.paste(borda, ((W - 196) // 2, 222), borda)
    img.paste(logo, ((W - 180) // 2, 230), logo)
    f, linhas = ajusta(d, s["titulo"].upper(), "Anton-Regular.ttf", 120, 70, largura, 4)
    y = escreve(d, linhas, f, 0, 480, NOITE, 1.05, centro=True)
    if s.get("texto"):
        ft, lt = ajusta(d, s["texto"], "Inter-Bold.otf", 46, 34, largura, 4)
        y = escreve(d, lt, ft, 0, y + 40, NOITE, 1.3, centro=True)
    # botão do link
    fl = fonte("Inter-Black.otf", 34)
    txt = s.get("botao", "LINK NA BIO")
    bw = d.textlength(txt, font=fl) + 100
    bx = (W - bw) / 2
    d.rounded_rectangle((bx, y + 60, bx + bw, y + 150), radius=45, fill=NOITE)
    d.text((bx + 50, y + 84), txt, font=fl, fill=BRANCO)
    rodape(img, d, total, idx, escuro=False)
    return img


TIPOS = {"capa": slide_capa, "texto": slide_texto, "cta": slide_cta}


def gera(caminho_json):
    caminho = Path(caminho_json)
    post = json.loads(caminho.read_text(encoding="utf-8"))
    slides = post["slides"]
    saidas = []
    for i, s in enumerate(slides, 1):
        img = TIPOS[s.get("tipo", "texto")](s, i, len(slides))
        out = caminho.parent / f"slide-{i:02d}.png"
        img.save(out, "PNG", optimize=True)
        saidas.append(out)
        print(out)
    return saidas


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    gera(sys.argv[1])
