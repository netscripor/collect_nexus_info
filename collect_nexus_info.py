#!/usr/bin/env python3

import argparse
import getpass
import re
from netmiko import ConnectHandler
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

# Регулярки
HOSTNAME_RE = re.compile(r'hostname (\S+)', re.IGNORECASE)
SERIAL_RE_PROC = re.compile(r'Processor board ID (\S+)', re.IGNORECASE)
SERIAL_RE_INV = re.compile(r'NAME: "Chassis".*?SN:\s*(\S+)', re.DOTALL)
SERIAL_RE_HARDWARE = re.compile(r'Serial number is (\S+)', re.IGNORECASE)
UPTIME_RE = re.compile(r'uptime is (.+)')
VERSION_RE = re.compile(r'NXOS:\s+version\s+(\S+)', re.IGNORECASE)

# Аргументы CLI
parser = argparse.ArgumentParser(description="Сбор hostname, serial и системной информации")
parser.add_argument('-f', '--file', default='nxnode.txt', help="Файл с IP-адресами устройств")
parser.add_argument('-d', '--device-type', default='cisco_nxos', help="Тип устройства для Netmiko")

args = parser.parse_args()

# Чтение IP-адресов
try:
    with open(args.file) as f:
        ip_list = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(Fore.RED + f"[!] Файл не найден: {args.file}")
    exit(1)

# Запрос логина и пароля
username = input('Username: ')
password = getpass.getpass('Password: ')

# Логи
log_file = open("log.txt", "a")
output_file = open("output.log", "a")

for ip in ip_list:
    print(Fore.CYAN + f"[+] Подключение к {ip}")
    device = {
        'device_type': args.device_type,
        'ip': ip,
        'username': username,
        'password': password
    }

    try:
        conn = ConnectHandler(**device)

        # Hostname
        run_cfg = conn.send_command('show running-config | include hostname')
        hostname_match = HOSTNAME_RE.search(run_cfg)
        hostname = hostname_match.group(1) if hostname_match else 'UNKNOWN'

        # Serial
        serial = 'UNKNOWN'
        version_out = conn.send_command('show version')
        if m := SERIAL_RE_PROC.search(version_out):
            serial = m.group(1)
        if serial == 'UNKNOWN':
            inv = conn.send_command('show inventory')
            if m := SERIAL_RE_INV.search(inv):
                serial = m.group(1)
        if serial == 'UNKNOWN':
            hw = conn.send_command('show hardware')
            if m := SERIAL_RE_HARDWARE.search(hw):
                serial = m.group(1)

        # Uptime
        uptime = 'UNKNOWN'
        if m := UPTIME_RE.search(version_out):
            uptime = m.group(1)

        # NX-OS Version
        nxos_version = 'UNKNOWN'
        if m := VERSION_RE.search(version_out):
            nxos_version = m.group(1)

        # Environment
        env_output = conn.send_command('show environment')

        # Вывод в терминал
        print(Fore.WHITE + f"Device: {hostname} ({ip})")
        print(Fore.WHITE + f"Serial: {serial}")
        print(Fore.WHITE + f"Uptime: {uptime}")
        print(Fore.WHITE + f"NX-OS Version: {nxos_version}")

        # Запись в единый лог-файл
        output_file.write(f"\n{'='*60}\n")
        output_file.write(f"[{datetime.now()}] Hostname: {hostname}\n")
        output_file.write(f"IP: {ip}\n")
        output_file.write(f"Serial: {serial}\n")
        output_file.write(f"Uptime: {uptime}\n")
        output_file.write(f"NX-OS Version: {nxos_version}\n")
        output_file.write(f"\n--- show environment ---\n{env_output}\n")

        conn.disconnect()

    except Exception as e:
        err_msg = f"[!] Ошибка подключения к {ip}: {e}"
        print(Fore.RED + err_msg)
        log_file.write(err_msg + '\n')

log_file.close()
output_file.close()
