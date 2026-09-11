@echo off
cd /d "%~dp0"
echo Starting JARVIS Discord ticket bot...
echo Put your bot token and IDs in config\settings.json first:
echo   discord.enabled = true
echo   discord.bot_token
echo   discord.server_id
echo   discord.ticket_category_id
echo   discord.vault_role_id
echo.
python -m pip install discord.py requests psutil >nul 2>&1
python -c "from jarvis.config import load; from jarvis.discord.bot import TicketBot; from jarvis.vault import VaultLibrary; from jarvis.paths import BASE; s=load(); s['discord']['enabled']=True; b=TicketBot(s, vault=VaultLibrary(BASE/'vault'/'scripts')); print(b.start_background()); import time; 
while True: time.sleep(5)"
pause
