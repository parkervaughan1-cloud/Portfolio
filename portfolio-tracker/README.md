# Parker Vaughan Portfolio Tracker

A self-hosted project portfolio designed for a Raspberry Pi, Docker, and Cloudflare Tunnel.

## Features

- Public portfolio homepage
- Individual project case-study pages
- Private admin login
- Add, edit, and delete projects
- Upload project screenshots
- Upload PDFs and other project documentation
- Add GitHub and live-demo links
- Mark projects as featured
- Edit homepage hero and About content from the admin panel
- SQLite database
- Docker + Gunicorn deployment

## 1. Run locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="change-me"
export ADMIN_PASSWORD="choose-a-strong-password"

python app.py
```

Open:

- Portfolio: http://localhost:5000
- Admin: http://localhost:5000/admin/login

## 2. Run with Docker

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set strong values.

Then:

```bash
docker compose up -d --build
```

The application will be reachable on the Raspberry Pi itself at:

```text
http://127.0.0.1:5000
```

Because the Docker port is bound to `127.0.0.1`, it is not directly exposed to the rest of your LAN. Cloudflare Tunnel can connect to this local service.

## 3. Cloudflare Tunnel

After the site works on the Pi, create a Cloudflare Tunnel and configure a public hostname:

```text
Hostname: parkervaughan-portfolio.com
Service type: HTTP
URL: http://localhost:5000
```

You can also add:

```text
www.parkervaughan-portfolio.com
```

and either point it to the same tunnel or redirect `www` to the root domain.

Do not create a public A record pointing to your home IP if you are publishing through Cloudflare Tunnel.

## Important before production

- Replace `SECRET_KEY`.
- Use a strong admin password.
- Keep the Pi and Docker updated.
- Back up `portfolio.db` and `static/uploads`.
- Consider putting the admin route behind Cloudflare Access for additional protection.
- Do not upload confidential documents or secrets.
- Consider adding CSRF protection before exposing admin forms publicly.

## Suggested Cloudflare Access rule

A strong next step is to protect:

```text
parkervaughan-portfolio.com/admin/*
```

with Cloudflare Access so only your authorized email can even reach the admin login page.
