# ??? ������� ���������� Telegram Shop Bot

����������� ������� ��� �������������, ��������� � ���������� telegram-shop-bot.

## ?? ����������

- [������� �����](#�������-�����)
- [���������](#���������)
- [������� ����������](#�������-����������)
- [������������](#������������)
- [���� ������](#����-������)
- [������������](#������������)

---

## ?? ������� �����

### �������������� ���������

```bash
# ��������� � ��������� ����������
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh
chmod +x launcher.sh
sudo ./launcher.sh
```

������ �������������:
- ��������� ����������� (git, docker, nano)
- ��������� ����������� � `/opt/telegram-shop-bot`
- �������� ������������� ���� ����������

### ������ ���������

```bash
# ������������ �����������
git clone https://github.com/gopnikgame/telegram-shop-bot.git
cd telegram-shop-bot

# ��������� ������������
cp .env.example .env
nano .env  # ��������� ������������ ���������

# ������ �����������
docker-compose up -d

# ���������� ��������
docker exec shopbot-api alembic upgrade head
```

---

## ?? ���������

### ����������

- **��:** Linux (Ubuntu 20.04+, Debian 10+, CentOS 7+)
- **Docker:** 20.10+
- **Docker Compose:** 2.0+ ��� docker-compose 1.29+
- **Git:** 2.0+
- **RAM:** ������� 1GB
- **Disk:** ������� 5GB ���������� �����

### �����������

������������� ��������������� �������� `launcher.sh`:
- git
- docker / docker.io
- docker-compose-plugin / docker-compose
- nano (��� vim)

---

## ?? ������� ����������

### �������� ��������

```bash
# ������ �������������� ����
./scripts/manage_bot.sh
```

**�����������:**
1. ? ���������� ������������� (.env, texts.yml)
2. ? ���������� ������������ (������, ���������, ����������, ����������)
3. ? ���������� �� (��������, ������, ��������������)
4. ? �������� ����� (���, API, PostgreSQL, ������)
5. ? ���������� �� �����������
6. ? ������� (����, ������, Docker)
7. ? ���������� ������� �������

### ������� �������

```bash
# ������� ������
./scripts/quick_start.sh

# ������� ���������
./scripts/quick_stop.sh

# �������� �����
./scripts/logs.sh              # ��� ����
./scripts/logs.sh api          # ������ API
./scripts/logs.sh db           # ������ PostgreSQL
./scripts/logs.sh errors       # ������ ������
./scripts/logs.sh follow       # ������������ � �������� �������

# ����� ���� ������
./scripts/backup_db.sh

# ���������� �� �����������
./scripts/update.sh
```

### ���������� ���� �� ����������

```bash
chmod +x scripts/*.sh
chmod +x launcher.sh
```

---

## ?? ������������

### ���� .env

**������������ ���������:**

```ini
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# YooKassa (��� ������ ��������)
YK_SHOP_ID=your_shop_id
YK_SECRET_KEY=your_secret_key
YK_RETURN_URL=http://localhost:8000/thanks
```

**������������ ���������:**

```ini
# ���� ������ (��� Docker ������������ �������� �� ���������)
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot@localhost:5432/shopbot

# ������
SERVER_IP=127.0.0.1
BASE_URL=http://localhost:8000
PORT=8000

# �������������
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
ADMIN_CHAT_ID=123456789
ADMIN_TG_USERNAME=@your_username

# Webhook (��� ����������)
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_webhook_secret

# ������
DONATE_AMOUNTS=100,200,500,1000
```

### �������������� ������������

```bash
# ����� �������� (�������������)
./scripts/manage_bot.sh
# �������� ����� 1: "�������/������������� .env"

# ��������
nano .env
```

### ���� texts.yml

�������� ��� ������ ���� (������, ����, �����������).

**��������������:**

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 2: "������������� texts.yml"

# ��������
nano app/texts.yml
```

**�������� ������:**
- `buttons` - ������ ������
- `main_menu` - ������� ���� � ������
- `payment` - ��������� ������
- `notifications` - ����������� ��������������
- `delivery` - ��������� � ��������
- `offline_delivery` - ������� ��� ������� �������

---

## ??? ���� ������

### �������������

��� ������ ������� �������� ����������� ������������� � `docker-entrypoint.sh`.

**������ ����������:**

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 7: "�������������/�������� ��"

# ��������
docker exec shopbot-api alembic upgrade head
```

### ��������

**������� ������:**

```bash
docker exec shopbot-api alembic current
```

**������� ��������:**

```bash
docker exec shopbot-api alembic history
```

**����� �� ���������� ������:**

```bash
docker exec shopbot-api alembic downgrade -1
```

### ������

**�������� ������:**

```bash
# ����� ������ (�������������)
./scripts/backup_db.sh

# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 8: "������� ����� ��"

# ��������
docker exec shopbot-postgres pg_dump -U shopbot shopbot > backup.sql
```

**�������������� �� ������:**

```bash
# ����� �������� (�������������)
./scripts/manage_bot.sh
# �������� ����� 9: "������������ �� �� ������"

# ��������
docker exec -i shopbot-postgres psql -U shopbot shopbot < backup.sql
```

**�������������� ������:**

������ ����������� � `/opt/telegram-shop-bot/backups/` ���:
- ���������� �� �����������
- ������ �������� ����� ��������

---

## ?? ������������

### ���������� �� �����������

```bash
# ����� ������ (�������������)
./scripts/update.sh

# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 16: "�������� �� �����������"
```

**��� ���������� ��� ����������:**
1. ? ��������� ����� ������������ (.env, texts.yml)
2. ? ����������� ��������� ��������� (git stash)
3. ? ������������ ����� ���������
4. ? ����������� ����������
5. ? ����������������� ��������� ���������
6. ? ������������ ���������� �����������

### �������� �����

```bash
# ��� ����
docker-compose logs --tail=100

# ������ API
docker-compose logs api --tail=100

# ������ PostgreSQL
docker-compose logs db --tail=100

# ������������ � �������� �������
docker-compose logs -f

# ����� ������
./scripts/logs.sh [all|api|db|errors|follow]
```

### �������

```bash
# ����� �������� (�������������)
./scripts/manage_bot.sh
# �������� ����� 17: "�������"
```

**����� �������:**
1. ������ ���� (>30 ����)
2. ������ ������ (>30 ����)
3. Docker volumes (?? ������ ��!)
4. Docker images � build cache
5. �� ����������������� (����� volumes)

### �������� �������

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 15: "��������� ������ �������"

# ��������
docker-compose ps
curl http://localhost:8000/health/
```

### ���������� ��������

```bash
# ��� ����������
docker-compose restart

# ������ API
docker-compose restart api

# ������ PostgreSQL
docker-compose restart db
```

### ���������� �����������

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 6: "����������� ����������"

# ��������
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## ?? ����������

### Endpoints ��� ��������

- **Health Check:** http://localhost:8000/health/
- **API Docs:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:8000/admin/

### ���� �����������

���� ����������� � `/opt/telegram-shop-bot/logs/`:
- `bot.log` - ����� ���� ����
- `error.log` - ������ ������
- `docker.log` - ���� Docker

### ������� �����������

```bash
# ������������� ��������
docker stats shopbot-api shopbot-postgres

# ������ �����������
docker ps -s
```

---

## ?? ������������

### ������������

1. **����������� ������� ������** ���:
   - `ADMIN_PASSWORD`
   - `YK_SECRET_KEY`
   - `WEBHOOK_SECRET`

2. **���������� ������ � ������:**
   ```bash
   chmod 600 .env
   ```

3. **����������� HTTPS** � ����������:
   - ��������� reverse proxy (nginx/traefik)
   - �������� SSL ���������� (Let's Encrypt)

4. **���������� ������:**
   ```bash
   # ��������� cron ��� �������������� �������
   0 2 * * * /opt/telegram-shop-bot/scripts/backup_db.sh
   ```

5. **����������:**
   - ��������� ���������� �� �����������
   - ������� �� ������������ ������������ Docker

---

## ?? Troubleshooting

### �������� � ��������

**������: "Cannot connect to Docker daemon"**
```bash
# ��������� ������ Docker
sudo systemctl status docker

# ��������� Docker
sudo systemctl start docker

# �������� ������������ � ������ docker
sudo usermod -aG docker $USER
newgrp docker
```

**������: "Port 8000 already in use"**
```bash
# ������� �������, ������������ ����
sudo lsof -i :8000

# �������� ���� � .env
PORT=8001
```

### �������� � ��

**������: "Database connection failed"**
```bash
# ��������� ������ PostgreSQL
docker-compose logs db

# ��������� �����������
docker exec shopbot-postgres pg_isready -U shopbot

# ������������ ��������� ��
docker-compose down
docker volume rm telegram-shop-bot_db_data
docker-compose up -d
```

**������ ��������:**
```bash
# �������� �������� � ��������� ������
docker exec shopbot-api alembic downgrade base
docker exec shopbot-api alembic upgrade head
```

### �������� � �����

**��� �� ��������:**
```bash
# ��������� �����
grep BOT_TOKEN .env

# ��������� ����
./scripts/logs.sh api

# ������������� ���������
docker-compose restart api
```

**������ ��������:**
```bash
# ��������� ��������� YooKassa
grep YK_ .env

# ��������� webhook
curl -X POST http://localhost:8000/payments/yookassa/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}'
```

---

## ?? ���������

- **GitHub Issues:** https://github.com/gopnikgame/telegram-shop-bot/issues
- **������������:** https://github.com/gopnikgame/telegram-shop-bot
- **Upstream:** https://github.com/TrackLine/telegram-shop-bot

---

## ?? Changelog

### v1.0.0 (2025-01-13)
- ? ������ ������� ����������
- ? ������������� ��������
- ? ������� �������
- ? �������������� ������
- ? ��������� ������� �������
- ? ������� �������

---

**Made with ?? for Telegram Shop Bot**
