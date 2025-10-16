# ?? �������� � ����������

## �������� �� ������ ������

### �� telegram-publisher-bot

���� �� ������������ telegram-publisher-bot � ������ �����������:

#### 1. ��������� ������

```bash
# �������� ����� ������ �� (���� ����)
docker exec old-container pg_dump -U user dbname > old_backup.sql

# ��������� ������������
cp old-project/.env ~/backup_env
```

#### 2. ���������� telegram-shop-bot

```bash
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh
chmod +x launcher.sh
sudo ./launcher.sh
```

#### 3. ��������� ������������

```bash
cd /opt/telegram-shop-bot
./scripts/manage_bot.sh
# �������� ����� 1: �������/������������� .env
```

**������ ��������� � .env:**

```ini
# ������ ���������� (telegram-publisher-bot)
BOT_TOKEN=...
ADMIN_IDS=...
CHANNEL_ID=...

# ����� ���������� (telegram-shop-bot)
BOT_TOKEN=...              # ��� �� �����
ADMIN_CHAT_ID=...          # ������ ADMIN_IDS (���� ID)
YK_SHOP_ID=...             # �����: YooKassa
YK_SECRET_KEY=...          # �����: YooKassa
DATABASE_URL=...           # �����: PostgreSQL ������ SQLite
```

#### 4. �������� ������ (�����������)

���� � ��� ���� �� � ������ �������, ����� ��������� �������������:

```python
# migration_script.py
import sqlite3
import psycopg2

# ����������� � ������ ��
old_db = sqlite3.connect('old_bot.db')
old_cursor = old_db.cursor()

# ����������� � ����� ��
new_db = psycopg2.connect(
    host='localhost',
    port=5432,
    user='shopbot',
    password='shopbot',
    database='shopbot'
)
new_cursor = new_db.cursor()

# ������� �������������
old_cursor.execute("SELECT tg_id, username, first_name FROM users")
users = old_cursor.fetchall()

for user in users:
    new_cursor.execute(
        "INSERT INTO users (tg_id, username, first_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        user
    )

new_db.commit()
print(f"Migrated {len(users)} users")
```

### ���������� � ���������� ������ telegram-shop-bot

#### ����� 1: ����� ������ ���������� (�������������)

```bash
cd /opt/telegram-shop-bot
./scripts/update.sh
```

������ �������������:
- ? ������� ����� ������������
- ? �������� ��������� ���������
- ? ������� ����� ���������
- ? �������� ����������
- ? ����������� ������������
- ? ��������� ����������

#### ����� 2: ������ ����������

```bash
cd /opt/telegram-shop-bot

# 1. �����
./scripts/backup_db.sh
cp .env .env.backup
cp app/texts.yml app/texts.yml.backup

# 2. ��������� ����������
git fetch origin
git log HEAD..origin/main --oneline  # ���������� ���������

# 3. ���������� ����������
git pull origin main

# 4. �������������� ������������ (���� ���������)
cp .env.backup .env
cp app/texts.yml.backup app/texts.yml

# 5. ���������� � ����������
docker compose down
docker compose build
docker compose up -d

# 6. ���������� ��������
docker exec shopbot-api alembic upgrade head
```

## ����� �� ���������� ������

### ����� ����

```bash
cd /opt/telegram-shop-bot

# ���������� ������� ��������
git log --oneline

# ���������� �� ���������� ������
git reset --hard <commit-hash>

# ����������
docker compose down
docker compose build
docker compose up -d
```

### ����� ��

```bash
# 1. ���������� ����������
./scripts/quick_stop.sh

# 2. ������������ �� �� ������
docker compose up -d db
sleep 5

# 3. �������� �������� �� ������ ������
docker exec shopbot-api alembic downgrade <revision>

# 4. ��� ������������ �� SQL ������
./scripts/manage_bot.sh
# �������� ����� 9: ������������ �� �� ������

# 5. ��������� ����������
./scripts/quick_start.sh
```

## �������� ���� ������

### ���������� ����� ��������

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 7: �������������/�������� ��

# ��������
docker exec shopbot-api alembic upgrade head
```

### �������� ������� ������

```bash
docker exec shopbot-api alembic current
```

### ������� ��������

```bash
docker exec shopbot-api alembic history
```

### ����� ��������

```bash
# ����� �� ���� ������ �����
docker exec shopbot-api alembic downgrade -1

# ����� �� ���������� ������
docker exec shopbot-api alembic downgrade <revision>

# ����� ���� ��������
docker exec shopbot-api alembic downgrade base
```

## ��������� � ������������

### ����� ��������� � ������ 1.0.0

�������� � `.env` ���� �� ���:

```ini
# ������� ������ (�����)
# (������������� ��������������)

# ������� (�����)
# (������������� ��������������)

# ������ - ����� ������
DONATE_AMOUNTS=100,200,500,1000

# Webhook ��� ���������� (�����������)
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_secret_here
```

### ��������� � texts.yml

����� ������:

```yaml
# ������� ��������
offline_delivery:
  prompts:
    fullname: "?? ������� ���� ��� ��� ��������:"
    phone: "?? ������� ����� �������� ��� �����:"
    address: "?? ������� ����� ��������:"
    comment: "?? �������� ����������� � ������ (��� ����������):"

# �������
buttons:
  add_to_cart: "? � �������"
  remove_from_cart: "? ������ �� �������"
  cart: "?? �������"
  checkout: "?? �������� ({total} ?)"
  clear_cart: "?? �������� �������"
```

���������� �� �� `app/texts.yml.example` ��� ������������ �����������.

## �������� ����� ��������

### 1. ��������� ������ �������

```bash
./scripts/check_requirements.sh
```

### 2. ��������� ����������

```bash
docker compose ps
```

������ ���� ��������:
- `shopbot-api`
- `shopbot-postgres`

### 3. ��������� API

```bash
curl http://localhost:8000/health/
```

�����: `{"status": "ok", "database": "connected"}`

### 4. ��������� ��

```bash
docker exec shopbot-api alembic current
```

������ ���� ������: `20250903_000001`

### 5. ��������� ����

```bash
./scripts/logs.sh errors
```

�� ������ ���� ����������� ������.

## ������ �������� ��� ��������

### ��������� ������������

**��������:** Git �� ����� ��������� ���������� ��-�� ��������� � `.env`

**�������:**
```bash
# ��������� ���������
git stash

# ����������
git pull origin main

# ������������ ���������
git stash pop

# ��������� ��������� �������
nano .env
```

### ������ �������� ��

**��������:** �������� �� �����������

**�������:**
```bash
# 1. ��������� ������� ������
docker exec shopbot-api alembic current

# 2. ���������� �� base
docker exec shopbot-api alembic downgrade base

# 3. ��������� ������
docker exec shopbot-api alembic upgrade head

# 4. ���� �� ������� - ������������ �� (?? ������ ������!)
docker compose down -v
docker compose up -d
```

### ��������������� ������

**��������:** ������ ������ Docker/Docker Compose

**�������:**
```bash
# �������� Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# ���������� Docker Compose plugin
sudo apt-get install docker-compose-plugin
```

## ����� � ���������� ���������� ������

���� ���������� ������� ��������:

```bash
cd /opt/telegram-shop-bot

# 1. ���������� ����������
./scripts/quick_stop.sh

# 2. ���������� � ���������� �������� �������
git log --oneline
git reset --hard <working-commit-hash>

# 3. ������������ �� �� ������
./scripts/manage_bot.sh
# ����� 9: ������������ ��

# 4. ������������ � ���������
docker compose build
./scripts/quick_start.sh
```

## ���������

���� �������� �������� � ���������:

1. ��������� [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#-troubleshooting)
2. �������� Issue: https://github.com/gopnikgame/telegram-shop-bot/issues
3. ���������:
   - ������ ������� (`cat VERSION.md`)
   - ���� (`./scripts/logs.sh errors`)
   - ������ Docker (`docker --version`)

---

**�������� ��������! ??**
