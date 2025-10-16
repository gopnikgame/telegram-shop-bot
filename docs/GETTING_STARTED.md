# ?? ������ ��������� Telegram Shop Bot

��������� ����������� ��� ����� �������������.

## ��� 1: ����������

### 1.1 �������� Telegram ����

1. ������� [@BotFather](https://t.me/BotFather) � Telegram
2. ��������� `/newbot`
3. �������� ����������� (��� � username ����)
4. **��������� �����** - �� ����������� ��� `.env`
5. ��������� ����:
   ```
   /setdescription - �������� ����
   /setabouttext - ����� "� ����"
   /setuserpic - ��������� ������
   ```

### 1.2 ����������������� � YooKassa

1. ��������� �� [yookassa.ru](https://yookassa.ru)
2. ����������������� � �������� �������
3. � ������� "����������" ��������:
   - **shopId** (ID ��������)
   - **��������� ����**
4. ��������� ������� ������ (�����, ���)

### 1.3 ������� ���� Telegram ID

1. ������� [@userinfobot](https://t.me/userinfobot)
2. ��������� `/start`
3. **��������� ��� ID** - �� ����������� ��� `ADMIN_CHAT_ID`

## ��� 2: ���������

### 2.1 �������������� ��������� (�������������)

```bash
# ��������� ����������
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh

# �������� ��� �����������
chmod +x launcher.sh

# ��������� (����� ����� sudo ��� ��������� Docker)
sudo ./launcher.sh
```

���������� �������������:
- ? ��������� ����������� (git, docker, nano)
- ? ��������� ����������� � `/opt/telegram-shop-bot`
- ? �������� ������������� ����

### 2.2 ������ ���������

```bash
# ���������� �����������
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin nano

# ���������� �����������
git clone https://github.com/gopnikgame/telegram-shop-bot.git
cd telegram-shop-bot

# �������� ������� ������������
chmod +x scripts/*.sh
chmod +x launcher.sh

# ��������� ��������
./scripts/manage_bot.sh
```

## ��� 3: ��������� ������������

### 3.1 ��������� .env

� ������������� ����:
- �������� **����� 1: �������/������������� .env**

��� �������:
```bash
cp .env.example .env
nano .env
```

**����������� ���������:**

```ini
# 1. TELEGRAM BOT (�� ���� 1.1)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 2. YOOKASSA (�� ���� 1.2)
YK_SHOP_ID=123456
YK_SECRET_KEY=live_abc123xyz456
YK_RETURN_URL=http://localhost:8000/thanks

# 3. DATABASE (��� Docker �������� ��� ����)
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot@db:5432/shopbot

# 4. ADMIN (�� ���� 1.3)
ADMIN_CHAT_ID=123456789
ADMIN_TG_USERNAME=@your_username
ADMIN_USERNAME=admin
ADMIN_PASSWORD=����������������123!

# 5. SERVER (��� ���������� ������������ �������� ��� ����)
SERVER_IP=127.0.0.1
BASE_URL=http://localhost:8000
PORT=8000
```

**����������� (����� ��������� �����):**

```ini
# Webhook ��� ����������
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_webhook_secret

# ������
DONATE_AMOUNTS=100,200,500,1000

# ������ � ����
SHOW_CONTACT_BUTTON=true
CONTACT_ADMIN=@your_username
SHOW_DONATE_BUTTON=true
```

### 3.2 ��������� texts.yml (�����������)

� ������������� ����:
- �������� **����� 2: ������������� texts.yml**

��� �������:
```bash
nano app/texts.yml
```

�������� ������ ��� ��� ������:

```yaml
main_menu:
  title: "?? ������ ������� ����_��������"
  buttons:
    projects: "?? ���� �������"
    services: "????? ���� ������"
    # ...
```

## ��� 4: ������

### 4.1 ��������� ����������

� ������������� ����:
- �������� **����� 3: ��������� ����������**

��� �������:
```bash
./scripts/quick_start.sh
```

��������� 10-15 ������, ���� ���������� �������.

### 4.2 ��������� �������� ��

� ������������� ����:
- �������� **����� 7: �������������/�������� ��**

��� �������:
```bash
docker exec shopbot-api alembic upgrade head
```

### 4.3 ��������� ������

```bash
# ����� ��������
./scripts/manage_bot.sh
# �������� ����� 15: ��������� ������ �������

# ��� �������
curl http://localhost:8000/health/
```

**��������� �����:**
```json
{"status": "ok", "database": "connected"}
```

## ��� 5: ������ �������������

### 5.1 �������� �������

1. �������� � ��������: http://localhost:8000/admin/
2. ������� � �������� ������� �� `.env`:
   - �����: `ADMIN_USERNAME`
   - ������: `ADMIN_PASSWORD`

### 5.2 �������� ������ �����

1. � ������� ��������� � "Items" ? "Create New Item"
2. ��������� �����:
   - **Title:** �������� ������
   - **Description:** ��������
   - **Price:** ���� � ������
   - **Type:** �������� ���:
     - `service` - ������ (�������� ����� ���������)
     - `digital` - �������� ����� (����/GitHub/����)
     - `offline` - ���������� ����� (� ���������)
   - **Is Active:** ? (����� ����� ��� �����)

3. ��� **digital �������** �������� ������ ��������:
   - **file** - ��������� ����
   - **github** - ������� URL ����������� � ����� �������
   - **codes** - ��������� TXT ���� � ������ (�� ������ �� ������)

4. ������� **Create**

### 5.3 ������������� ����

1. ������� ������ ���� � Telegram (username �� ���� 1.1)
2. ��������� `/start`
3. ������ ��������� ������� ����
4. ��������� � ������ � ��������
5. ���������� �������� ����� � �������
6. �������� �������� �����

## ��� 6: ��������� ����������� (�����������)

### 6.1 Systemd service

��� ����������� ��� ������������ �������:

```bash
sudo ./scripts/install_service.sh
```

������ ��� ����� ������������� ����������� ��� ������ �������.

**���������� ��������:**
```bash
sudo systemctl start telegram-shop-bot     # ���������
sudo systemctl stop telegram-shop-bot      # ����������
sudo systemctl restart telegram-shop-bot   # �������������
sudo systemctl status telegram-shop-bot    # ������
```

### 6.2 �������������� ������

��������� ���������� ������ ��:

```bash
sudo ./scripts/setup_cron.sh
```

�������� ������� (�������������: ��������� � 02:00).

## ��� 7: ��������� ��� ���������� (�����������)

### 7.1 ��������� �����

1. ������ �����
2. ��������� A-������ �� IP ������ �������
3. ���������� nginx:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```

4. �������� ������ nginx:
   ```nginx
   # /etc/nginx/sites-available/shopbot
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

5. �������� ������:
   ```bash
   sudo ln -s /etc/nginx/sites-available/shopbot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

6. �������� SSL ����������:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

### 7.2 ��������� webhook

� `.env` ��������:
```ini
BASE_URL=https://your-domain.com
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=������������_���������_������
```

�������������:
```bash
./scripts/manage_bot.sh
# �������� ����� 5: ������������� ����������
```

### 7.3 ��������� YooKassa webhook

1. ������� � ������ YooKassa
2. ��������� � "����������" ? "HTTP-�����������"
3. �������� URL: `https://your-domain.com/payments/yookassa/webhook`
4. �������� ����������� ��� ������� `payment.succeeded`

## ��� 8: ����������

### 8.1 �������� �����

```bash
# � �������� �������
./scripts/logs.sh follow

# ������ ������
./scripts/logs.sh errors

# ��� ���� API
./scripts/logs.sh api
```

### 8.2 �������� �������

```bash
./scripts/check_requirements.sh
```

### 8.3 ������ ��������

```bash
curl http://localhost:8000/health/
docker compose ps
```

## ������ �������

### ��� �� ��������

1. ��������� �����:
   ```bash
   grep BOT_TOKEN .env
   ```

2. ��������� ����:
   ```bash
   ./scripts/logs.sh api
   ```

3. �������������:
   ```bash
   ./scripts/manage_bot.sh
   # ����� 5: ������������� ����������
   ```

### ������� �� ��������

1. ��������� ��������� YooKassa:
   ```bash
   grep YK_ .env
   ```

2. ���������, ��� ������� ����������� � YooKassa
3. ��������� ������� ������ (������ ���� ��������)
4. ��� ���������� ��������� webhook (��. ��� 7.3)

### ������� �� �����������

1. ���������, ��� ���������� ��������:
   ```bash
   docker compose ps
   ```

2. ��������� ������� ������ � `.env`:
   ```bash
   grep ADMIN_USERNAME .env
   grep ADMIN_PASSWORD .env
   ```

3. ���������� ������ ���� � `.env`:
   ```ini
   PORT=8001
   ```

### �������� �� �����������

1. ��������� ��:
   ```bash
   docker compose logs db
   ```

2. ��������� �������� ������:
   ```bash
   docker exec shopbot-api alembic upgrade head
   ```

3. ���� �� �������, ������������ �� (?? ������ ������):
   ```bash
   docker compose down -v
   docker compose up -d
   docker exec shopbot-api alembic upgrade head
   ```

## ��������� ����

1. ?? ������� [������ ������������](docs/DEPLOYMENT.md)
2. ?? ��������� ������ � ����������� � `texts.yml`
3. ??? �������� ������ ������� ����� �������
4. ?? ��������� SSL � webhook ��� ����������
5. ?? ��������� ���������� � ����������
6. ?? ��������� ������� ����!

## ���������

����� ������?

- ?? [������������](docs/DEPLOYMENT.md)
- ?? [GitHub Issues](https://github.com/gopnikgame/telegram-shop-bot/issues)
- ?? [���������](CHEATSHEET.md)

---

**�������� �������! ??**
