# Npuls-huisstijl

`design-tokens.json` is letterlijk overgenomen uit de skill
`vormgever-npuls-huisstijl` in
[cedanl/.github](https://github.com/cedanl/.github/tree/main/.claude/skills/vormgever-npuls-huisstijl)
(commit `e9db48e`). Pas het bestand hier niet met de hand aan: haal bij een
wijziging de nieuwe versie op uit `cedanl/.github`.

`app/_huisstijl.py` leest de tokens. `.streamlit/config.toml` bevat dezelfde
kleuren (Streamlit leest alleen TOML); `tests/test_huisstijl.py` controleert
dat die twee niet uit elkaar lopen.
