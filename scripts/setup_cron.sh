#!/bin/bash

# ��������� cron ����� ��� �������������� �������
# �������������: sudo ./scripts/setup_cron.sh

set -euo pipefail

# �����
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$PROJECT_ROOT/scripts/backup_db.sh"

echo -e "${BLUE}? ��������� cron ��� �������������� �������...${NC}\n"

# �������� ������������� ������� ������
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}? ������ ������ �� ������: $BACKUP_SCRIPT${NC}"
    exit 1
fi

# ���� ������ �������
echo "�������� ������� �������������� �������:"
echo "1. ��������� � 02:00"
echo "2. ������ � ���� (02:00 � 14:00)"
echo "3. ����������� (����������� � 02:00)"
echo "4. ���������� (1-�� ����� � 02:00)"
echo "5. ���������������� ����������"
echo "0. ������"
echo ""

read -p "�������� ������� (0-5): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="��������� � 02:00"
        ;;
    2)
        CRON_SCHEDULE="0 2,14 * * *"
        DESCRIPTION="������ � ���� (02:00 � 14:00)"
        ;;
    3)
        CRON_SCHEDULE="0 2 * * 0"
        DESCRIPTION="����������� (����������� � 02:00)"
        ;;
    4)
        CRON_SCHEDULE="0 2 1 * *"
        DESCRIPTION="���������� (1-�� ����� � 02:00)"
        ;;
    5)
        echo ""
        echo "������� ���������� � ������� cron (��������: 0 2 * * *):"
        read -r CRON_SCHEDULE
        DESCRIPTION="���������������� ����������: $CRON_SCHEDULE"
        ;;
    0)
        echo -e "${YELLOW}?? ��������${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}? �������� �����${NC}"
        exit 1
        ;;
esac

# �������� cron ������
CRON_JOB="$CRON_SCHEDULE $BACKUP_SCRIPT >> $PROJECT_ROOT/logs/cron_backup.log 2>&1"

echo ""
echo -e "${BLUE}?? ����� ������� cron ������:${NC}"
echo "  ����������: $DESCRIPTION"
echo "  �������: $BACKUP_SCRIPT"
echo ""

read -p "����������? [Y/n] " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    # ������� ������ ������ ��� ����� �������
    (crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" || true) | crontab -
    
    # ��������� ����� ������
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    
    echo -e "${GREEN}? Cron ������ �����������${NC}\n"
    
    echo -e "${BLUE}?? ������� cron ������:${NC}"
    crontab -l
    
    echo ""
    echo -e "${YELLOW}?? ���� ������� ����� ����������� �:${NC}"
    echo "   $PROJECT_ROOT/logs/cron_backup.log"
else
    echo -e "${YELLOW}?? ��������${NC}"
fi
