# Black Bloc

A Discord moderation and content bot. Python 3.12, `discord.py`, SQLite, with an
optional FastAPI companion server. Runs as one always-on process (locally in a
venv, or as a container on Fly.io).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env      # then fill in DISCORD_TOKEN and DEV_GUILD_ID
pytest
python -m black_bloc
```
