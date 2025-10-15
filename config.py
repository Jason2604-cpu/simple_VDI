# config.py

# Proxmox
PROXMOX_HOST = ""
PROXMOX_USER = ""
PROXMOX_TOKEN_NAME = "autospawn"
PROXMOX_TOKEN_VALUE = ""
PROXMOX_NODE = ""
TEMPLATE_ID = 3000
STORAGE = "local-zfs"
VM_NAME_PREFIX = "auto"
VM_ID_START = 5000
GATEWAY = ""
DNS = "8.8.8.8"
Ci_USER = "user"
Ci_PASSWORD = ""


# Database
DB_HOST = ""
DB_USER = ""
DB_PASS = ""
DB_NAME = "guacamole_db"

# --- IP range to monitor ---
IP_PREFIX = "192.168.220."
IP_RANGE_START = 50
IP_RANGE_END = 70

# --- Schedule ---
SPAWN_TIME = "00:56"
DELETE_TIME = "10:00"

# --- State / Log paths ---
LOG_FILE = "proxmox_autospawn.log"
