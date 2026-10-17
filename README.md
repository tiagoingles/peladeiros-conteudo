# peladeiros-conteudo

Agente de conteúdo do Instagram @peladeiros_de_respeito (app PeladaPro).
Regras e fluxo em `CLAUDE.md`. Roda como tarefa agendada do Claude (seg, qua, sex) e publica via Metricool.

- `scripts/carrossel.py` — gera carrossel 1080x1350 a partir de `post.json`
- `scripts/reels.py` — gera Reels 1080x1920 a partir de gravação de tela em `gravacoes/`
- `pautas/` — banco de ideias, radar semanal e histórico
- `posts/` — cada post publicado (json + mídias, servidas publicamente pelo GitHub)
