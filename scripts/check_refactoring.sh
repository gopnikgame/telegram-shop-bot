#!/bin/bash
# ������ ��� �������� ���������� ������������

echo "?? �������� ��������� bot/handlers/..."
echo ""

# ��������� ������� ���� �������
modules=("__init__.py" "start.py" "menu.py" "items.py" "cart.py" "delivery.py" "donate.py" "admin.py")

all_present=true
for module in "${modules[@]}"; do
    if [ -f "bot/handlers/$module" ]; then
        echo "? bot/handlers/$module"
    else
        echo "? bot/handlers/$module - �� ������!"
        all_present=false
    fi
done

echo ""

# ��������� ��������� Python
echo "?? �������� ���������� Python..."
if python -m py_compile bot/handlers/*.py 2>/dev/null; then
    echo "? ��� ������ ��� �������������� ������"
else
    echo "? ���������� �������������� ������!"
    all_present=false
fi

echo ""

# ��������� ������ � webhook_app.py
echo "?? �������� bot/webhook_app.py..."
if grep -q "from .handlers import main_router" bot/webhook_app.py; then
    echo "? ������ main_router ���������"
else
    echo "? ������������ ������ � bot/webhook_app.py!"
    all_present=false
fi

echo ""

if [ "$all_present" = true ]; then
    echo "? ��� �������� ��������!"
    echo ""
    echo "��������� ����:"
    echo "1. docker compose restart"
    echo "2. docker compose logs api -f"
    echo "3. ������������� ����"
    echo "4. ���� �� ��������: rm bot/handlers.py"
    echo ""
    echo "?? ��������� ������������: docs/REFACTORING_COMPLETE.md"
else
    echo "? ���� �������� - ��. ����"
    exit 1
fi
