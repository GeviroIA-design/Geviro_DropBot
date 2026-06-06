// Optionnel : PM2 en COMPLÉMENT de systemd (pas le mode principal).
// Utilisation :
//   pm2 start deploy/optional-pm2-ecosystem.config.js
//   pm2 logs geviro-dropbot
//   pm2 save && pm2 startup
//
// Les secrets (TELEGRAM_BOT_TOKEN, etc.) doivent venir de l'environnement
// ou d'un .env chargé en amont — ne jamais les coder en dur ici.
module.exports = {
  apps: [
    {
      name: "geviro-dropbot",
      script: "-m app.run_service",
      interpreter: "./.venv/bin/python",
      cwd: "/opt/geviro-dropbot",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 50,
      kill_timeout: 20000,
      stop_signal: "SIGTERM",
      out_file: "logs/pm2-out.log",
      error_file: "logs/pm2-err.log",
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
