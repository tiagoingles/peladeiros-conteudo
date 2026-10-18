#!/usr/bin/env python3
"""
Gera um Reels "Quem é o craque?" (1080x1920, ~22s) só com texto e arte da marca:
nenhuma foto, vídeo, escudo ou logo de clube/patrocinador.

Uso:
    python scripts/quem_e_o_craque.py posts/2026-10-20-1700-quem-e-o-craque/post.json

Campos do post.json:
    "craque":  "Ronaldinho Gaúcho"                      (resposta, revelada no fim)
    "era":     "lenda" | "atual"                         (só muda o selo da capa)
    "dicas":   ["Dica 1 (mais difícil)", "Dica 2", "Dica 3 (mais fácil)"]   (3 dicas, fatos verificados)
    "revelacao": "Frase curta depois do nome (opcional)"
Saída: reels.mp4 e capa.jpg na pasta do post.json.

ffmpeg: usa a variável FFMPEG, senão o imageio_ffmpeg instalado, senão o "ffmpeg" do PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carrossel as c  # cores, fontes, logo e quebra de linha da marca

W, H = 1080, 1920
FPS = 30


def ffmpeg_exe() -> str:
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def base(cor_topo=c.NOITE, cor_base=c.NOITE_2):
    img = Image.new("RGB", (W, H), cor_topo)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(cor_topo[i] + (cor_base[i] - cor_topo[i]) * t) for i in range(3)))
    sobre = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sobre)
    ds.ellipse((W // 2 - 330, H // 2 - 330, W // 2 + 330, H // 2 + 330), outline=(255, 255, 255, 16), width=6)
    ds.line([(0, H // 2), (W, H // 2)], fill=(255, 255, 255, 12), width=5)
    img.paste(sobre, (0, 0), sobre)
    return img, ImageDraw.Draw(img)


def rodape(img, d, escuro=True):
    logo = Image.open(c.LOGO).convert("RGBA").resize((70, 70), Image.LANCZOS)
    fa = c.fonte("Inter-Bold.otf", 34)
    tw = d.textlength(c.ARROBA, font=fa)
    x0 = (W - (70 + 18 + tw)) / 2
    img.paste(logo, (int(x0), H - 170), logo)
    d.text((x0 + 88, H - 158), c.ARROBA, font=fa, fill=c.BRANCO if escuro else c.NOITE)


def centro(d, linhas, f, y, cor, entre=1.1):
    for ln in linhas:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=cor)
        y += f.size * entre
    return y


def selo(d, texto, y, fundo=c.VERDE, cor=c.NOITE):
    fs = c.fonte("Inter-Black.otf", 36)
    lw = d.textlength(texto, font=fs) + 60
    d.rounded_rectangle(((W - lw) / 2, y, (W + lw) / 2, y + 72), radius=36, fill=fundo)
    d.text(((W - d.textlength(texto, font=fs)) / 2, y + 14), texto, font=fs, fill=cor)


def tela_capa(era):
    img, d = base()
    selo(d, "LENDA DO FUTEBOL" if era == "lenda" else "CRAQUE DA ATUALIDADE", 520)
    f, linhas = c.ajusta(d, "QUEM É O CRAQUE?", "Anton-Regular.ttf", 190, 120, W - 140, 2)
    y = centro(d, linhas, f, 660, c.BRANCO, 1.02)
    fs, ls = c.ajusta(d, "3 dicas. Acertou antes da resposta? Comenta!", "Inter-Bold.otf", 48, 36, W - 200, 2)
    centro(d, ls, fs, y + 90, c.VERDE, 1.3)
    rodape(img, d)
    return img


def tela_dica(n, texto, total=3):
    img, d = base()
    # pontinhos de progresso
    for i in range(total):
        x = W / 2 + (i - (total - 1) / 2) * 70
        cor = c.VERDE if i < n else (51, 65, 85)
        d.ellipse((x - 16, 300, x + 16, 332), fill=cor)
    fn = c.fonte("Anton-Regular.ttf", 120)
    centro(d, [f"DICA {n}"], fn, 420, c.VERDE)
    d.rounded_rectangle((90, 640, W - 90, 1340), radius=48, fill=(30, 41, 59))
    f, linhas = c.ajusta(d, texto, "Inter-Black.otf", 76, 48, W - 300, 7)
    alt = len(linhas) * f.size * 1.25
    centro(d, linhas, f, 990 - alt / 2, c.BRANCO, 1.25)
    rodape(img, d)
    return img


def tela_contagem(num):
    img, d = base()
    fs, ls = c.ajusta(d, "Comenta teu palpite antes da resposta!", "Inter-Black.otf", 64, 44, W - 180, 2)
    centro(d, ls, fs, 520, c.BRANCO, 1.25)
    d.ellipse((W / 2 - 230, 780, W / 2 + 230, 1240), fill=c.VERDE)
    fn = c.fonte("Anton-Regular.ttf", 340)
    tw = d.textlength(str(num), font=fn)
    d.text(((W - tw) / 2, 790), str(num), font=fn, fill=c.NOITE)
    rodape(img, d)
    return img


def tela_revelacao(nome, frase):
    img, d = base(c.VERDE, c.VERDE_ESC)
    selo(d, "É ELE!", 560, fundo=c.NOITE, cor=c.BRANCO)
    f, linhas = c.ajusta(d, nome.upper(), "Anton-Regular.ttf", 200, 100, W - 140, 3)
    y = centro(d, linhas, f, 700, c.NOITE, 1.02)
    if frase:
        fs, ls = c.ajusta(d, frase, "Inter-Bold.otf", 50, 36, W - 200, 3)
        y = centro(d, ls, fs, y + 40, c.NOITE, 1.3)
    fb = c.fonte("Inter-Black.otf", 44)
    txt = "ACERTOU? CONTA AÍ"
    bw = d.textlength(txt, font=fb) + 120
    d.rounded_rectangle(((W - bw) / 2, y + 70, (W + bw) / 2, y + 180), radius=55, fill=c.NOITE)
    d.text(((W - d.textlength(txt, font=fb)) / 2, y + 98), txt, font=fb, fill=c.BRANCO)
    rodape(img, d, escuro=False)
    return img


def tela_cta():
    img, d = base(c.VERDE, c.VERDE_ESC)
    logo = Image.open(c.LOGO).convert("RGBA").resize((260, 260), Image.LANCZOS)
    borda = Image.new("RGBA", (284, 284), (0, 0, 0, 0))
    ImageDraw.Draw(borda).rounded_rectangle((0, 0, 283, 283), radius=70, fill=c.BRANCO)
    img.paste(borda, ((W - 284) // 2, 520), borda)
    img.paste(logo, ((W - 260) // 2, 532), logo)
    f, linhas = c.ajusta(d, "SEGUE PRA MAIS RESENHA", "Anton-Regular.ttf", 120, 80, W - 160, 2)
    y = centro(d, linhas, f, 880, c.NOITE, 1.05)
    fs, ls = c.ajusta(d, "E organiza tua pelada no PeladaPro: link na bio", "Inter-Bold.otf", 46, 34, W - 200, 2)
    centro(d, ls, fs, y + 40, c.NOITE, 1.3)
    rodape(img, d, escuro=False)
    return img


def gera(caminho_json):
    caminho = Path(caminho_json)
    post = json.loads(caminho.read_text(encoding="utf-8"))
    dicas = post["dicas"]
    if len(dicas) != 3:
        raise SystemExit("São exatamente 3 dicas, da mais difícil para a mais fácil.")
    cenas = [(tela_capa(post.get("era", "lenda")), 2.5)]
    cenas += [(tela_dica(i + 1, t), 4.0) for i, t in enumerate(dicas)]
    cenas += [(tela_contagem(n), 1.0) for n in (3, 2, 1)]
    cenas += [(tela_revelacao(post["craque"], post.get("revelacao", "")), 3.5), (tela_cta(), 2.0)]

    ff = ffmpeg_exe()
    saida = caminho.parent / "reels.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        lista = []
        for i, (img, dur) in enumerate(cenas):
            p = Path(tmp) / f"c{i:02d}.png"
            img.save(p)
            lista.append(f"file '{p.as_posix()}'\nduration {dur}\n")
        lista.append(f"file '{(Path(tmp) / f'c{len(cenas) - 1:02d}.png').as_posix()}'\n")
        txt = Path(tmp) / "lista.txt"
        txt.write_text("".join(lista), encoding="utf-8")
        cmd = [ff, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(txt),
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
               "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(saida)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(r.stderr[-1500:])
        cenas[0][0].convert("RGB").save(caminho.parent / "capa.jpg", quality=90)
    print(saida)
    return saida


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    gera(sys.argv[1])
