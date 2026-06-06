# Déploiement VPS (Ubuntu/Debian) — pas à pas

Cible : faire tourner le bot **24/7** sur ton VPS, géré par **systemd** (redémarrage
auto), code livré par **Git privé**. Le token reste **uniquement** dans le `.env`
du VPS — jamais dans Git.

Remplace partout :
- `TONUSER` → ton compte GitHub
- `user@VPS_IP` → ton accès SSH (ex: `root@51.158.x.x`)

---

## Phase A — Sur ton PC Windows (pousser le code)

> Le `.env` (avec ton token) est protégé par `.gitignore` : il ne partira PAS sur Git.

1. Crée un dépôt **PRIVÉ** sur https://github.com/new
   (nom: `geviro-dropbot`, **Private**, sans README/licence).

2. Dans PowerShell :
```powershell
cd C:\Users\vince\geviro-dropbot
git add .
git commit -m "Service 24/7 + console Telegram + deploiement VPS"
git branch -M main
git remote add origin git@github.com:TONUSER/geviro-dropbot.git
git push -u origin main
```
(En HTTPS, remplace l'URL par `https://github.com/TONUSER/geviro-dropbot.git` ;
GitHub demandera un Personal Access Token comme mot de passe.)

---

## Phase B — Sur le VPS (installer)

3. Connexion + paquets de base :
```bash
ssh user@VPS_IP
sudo apt-get update && sudo apt-get install -y git python3 python3-venv
```

4. Crée l'utilisateur de service et une **clé de déploiement lecture seule** :
```bash
sudo useradd --system --create-home --shell /bin/bash dropbot
sudo -u dropbot ssh-keygen -t ed25519 -N "" -f /home/dropbot/.ssh/id_ed25519
sudo -u dropbot bash -c 'ssh-keyscan github.com >> ~/.ssh/known_hosts'
sudo cat /home/dropbot/.ssh/id_ed25519.pub
```
Copie la ligne affichée (`ssh-ed25519 ...`) dans GitHub :
**ton repo → Settings → Deploy keys → Add deploy key** (titre libre, **lecture seule**, coller la clé).

5. Clone le repo puis lance l'installation :
```bash
sudo -u dropbot git clone git@github.com:TONUSER/geviro-dropbot.git /opt/geviro-dropbot
sudo bash /opt/geviro-dropbot/deploy/install.sh
```
Le script installe tout (venv, dépendances, service systemd) et crée un `.env`.

---

## Phase C — Configurer le token et démarrer

6. Renseigne le `.env` (token + ton ID admin) :
```bash
sudo -u dropbot nano /opt/geviro-dropbot/.env
```
Mets au minimum :
```
TELEGRAM_BOT_TOKEN=le_token_de_BotFather
TELEGRAM_ADMIN_IDS=1473089737
```
`Ctrl+O`, `Entrée`, `Ctrl+X` pour sauver.

7. Démarre et vérifie :
```bash
sudo systemctl start geviro-dropbot
sudo systemctl status geviro-dropbot
journalctl -u geviro-dropbot -f
```
Tu dois voir `service up ... telegram=on` puis `telegram admin: polling demarre`.
Envoie `/ping` puis `/status` au bot dans Telegram.

---

## Phase D — Exploitation au quotidien

```bash
# état / logs
sudo systemctl status geviro-dropbot
journalctl -u geviro-dropbot -f               # logs en direct
journalctl -u geviro-dropbot --since "1 hour ago"

# contrôle
sudo systemctl restart geviro-dropbot
sudo systemctl stop geviro-dropbot
sudo systemctl start geviro-dropbot

# mise à jour (après un nouveau push depuis Windows)
sudo bash /opt/geviro-dropbot/deploy/update.sh
```

Le service redémarre automatiquement après un crash (`Restart=always`) et au
reboot du VPS (`systemctl enable`, fait par le script).

---

## Sécurité — rappel
- Le `.env` du VPS est en `chmod 600` (lecture par le seul utilisateur `dropbot`).
- Le token n'est **jamais** dans Git (clé de déploiement = lecture seule).
- Seuls les `TELEGRAM_ADMIN_IDS` peuvent piloter le bot ; tout le reste est refusé et audité.
- Pour révoquer l'accès du VPS au code : supprime la deploy key dans GitHub.
