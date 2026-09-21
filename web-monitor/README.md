# Web Monitor

Self-hosted website uptime monitoring platform. No database — all persistent data is stored as JSON and daily log files on the local filesystem.

## Features

- Projects and websites with per-site check intervals (10–120 seconds)
- Background monitoring engine (APScheduler + concurrent HTTPX checks)
- UP/DOWN state transitions with HTML email alerts (no spam on repeated downs)
- Dashboard, project details, website details with Recharts graphs
- Logs search with CSV/JSON export
- Automatic 31-day log retention cleanup
- SSRF protections for monitored URLs

## Requirements

- Python 3.11+ (3.10+ should work)
- Node.js 18+
- SMTP server (optional, for email alerts)

## Project layout

```
web-monitor/
├── backend/          # FastAPI + monitoring worker
├── frontend/         # React + Vite dashboard
├── data/             # JSON storage + daily logs (no database)
└── README.md
```

## Backend installation

```bash
cd backend
python -m venv venv
```

Linux / macOS:

```bash
source venv/bin/activate
```

Windows:

```bat
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy environment file:

```bash
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

### Start backend

From the `backend` directory:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health

The monitoring worker starts automatically with FastAPI and keeps running even if no browser is open.

## Frontend installation

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://127.0.0.1:5173

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

### Production frontend build

```bash
cd frontend
npm install
npm run build
```

Serve `frontend/dist` with Nginx (see below).

## SMTP configuration

1. Open **Email Alerts** in the dashboard.
2. Set SMTP host, port, username, password, from address, and recipients.
3. Click **Save Configuration**, then **Test Email**.

Passwords are stored in `data/settings.json` and are never returned by `GET /api/settings/email`.

## Data directory

All application state lives under `data/`:

```
data/
├── projects.json
├── websites.json
├── settings.json
├── state.json
├── logs/
│   ├── 2026-09-21.json
│   └── ...
└── backups/
```

- No PostgreSQL, MySQL, MongoDB, SQLite, Redis, Firebase, or cloud DB is used.
- JSON writes use atomic temp-file + replace.
- On first start (empty projects/websites), demo data is created once.

## Log retention

- Default retention: **31 days**
- Configured via `LOG_RETENTION_DAYS` in `.env`
- Cleanup runs at startup and daily via the scheduler
- Only files older than the retention window are deleted

## Monitoring configuration

Per website:

| Field | Notes |
|-------|--------|
| `check_interval` | 10–120 seconds (presets + custom) |
| `timeout` | Request timeout in seconds |
| `expected_status_code` | Default 200 |
| `alert_enabled` | DOWN/RECOVERY emails |

Environment variables (backend `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_HOST` | `0.0.0.0` | Bind host |
| `APP_PORT` | `8000` | Bind port |
| `MAX_CONCURRENT_CHECKS` | `20` | Concurrent HTTP checks |
| `LOG_RETENTION_DAYS` | `31` | Log retention |
| `DATA_DIR` | `../data` | Filesystem data path |
| `ALLOW_PRIVATE_URLS` | `false` | Allow private/localhost targets |
| `CORS_ORIGINS` | Vite origins | Frontend origins |

## Production deployment

Recommended topology:

```
Internet / LAN
     ↓
   Nginx
     ↓
 React static files  +  /api → FastAPI (uvicorn)
                              ↓
                     Monitoring worker
                              ↓
                     Local JSON storage
```

### 1. Backend systemd service

Create `/etc/systemd/system/web-monitor.service`:

```ini
[Unit]
Description=Web Monitor FastAPI
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/web-monitor/backend
Environment=PATH=/opt/web-monitor/backend/venv/bin
EnvironmentFile=/opt/web-monitor/backend/.env
ExecStart=/opt/web-monitor/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable web-monitor
sudo systemctl start web-monitor
sudo systemctl status web-monitor
```

### 2. Nginx configuration

```nginx
server {
    listen 80;
    server_name monitor.example.com;

    root /opt/web-monitor/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Reload Nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Permissions

Ensure the service user can read/write the data directory:

```bash
sudo chown -R www-data:www-data /opt/web-monitor/data
sudo chmod -R u+rwX /opt/web-monitor/data
```

## Backup and restore

### Backup

```bash
tar -czf web-monitor-backup-$(date +%F).tar.gz -C /opt/web-monitor data
```

Or copy:

```bash
cp -a /opt/web-monitor/data /backup/web-monitor-data-$(date +%F)
```

### Restore

1. Stop the service: `sudo systemctl stop web-monitor`
2. Replace the `data/` directory with the backup
3. Start: `sudo systemctl start web-monitor`

Automatic backups of settings/websites/projects are also written under `data/backups/` before major configuration deletes/updates.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/projects` | List / create projects |
| PUT/DELETE | `/api/projects/{id}` | Update / delete |
| GET/POST | `/api/websites` | List / create websites |
| PUT/DELETE | `/api/websites/{id}` | Update / delete |
| GET | `/api/websites/{id}/details` | Charts, incidents, uptime |
| GET | `/api/dashboard` | Summary dashboard |
| GET | `/api/logs` | Filtered logs |
| GET | `/api/logs/export` | CSV/JSON download |
| GET/PUT | `/api/settings/email` | SMTP config (no password on GET) |
| POST | `/api/settings/email/test` | Send test email |
| GET | `/api/health` | Health + engine status |

## Security notes

- URLs are validated; private/link-local/metadata addresses are blocked by default
- Set `ALLOW_PRIVATE_URLS=true` only if you intentionally monitor internal hosts
- SMTP password is never exposed via GET APIs
- Log export is limited to files under the application `data/logs` directory

## License

MIT — use freely for personal or internal monitoring.
