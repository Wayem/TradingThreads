#!/bin/sh

# Wait for network interface to be ready
while ! ping -c 1 -W 1 google.fr; do
    echo "network interface might be down..."
    sleep 3
done

cd /home/rasputin/TradingThreads
/home/rasputin/TradingThreads/.venv/bin/python main.py