import json, os, time
from guac_db import get_connections_in_range
from proxmox_utils import create_vm, delete_vm, next_available_vmid, connect_proxmox                     
from config import *
from logger import log
from datetime import datetime

_last_heartbeat = None  # global tracker to limit heartbeat logs
# -----------------------
# Spawn / Delete Functions
# -----------------------

def spawn_vms():
    """Spawn VMs based on Guacamole connection list."""
    log("[⏰] Scheduled spawn triggered.")
    conns = get_connections_in_range()
    if not conns:
        log("[Info] No valid Guacamole connections found.")
        return

    state = {}
    vmid = VM_ID_START

    for username, ip in conns:
        vm_info = create_vm(vmid, username, ip)
        if vm_info:
            state[ip] = vm_info
            vmid += 1
        else:
            log(f"[!] Skipped {username} ({ip}) due to previous errors.")

    
    log(f"[✓] Spawn complete: {len(state)} VMs created.")

def delete_vms():
    log("[⏰] Scheduled delete triggered.")

    proxmox = connect_proxmox()
    if not proxmox:
        log("[!] Cannot connect to Proxmox, skipping delete.")
        return

    try:
        existing_vms = proxmox.nodes(PROXMOX_NODE).qemu.get()
    except Exception as e:
        log(f"[!] Failed to fetch VM list from Proxmox: {e}")
        return

    # Filter only our auto-spawned VMs
    auto_vms = [vm for vm in existing_vms if vm["name"].startswith(VM_NAME_PREFIX)]

    if not auto_vms:
        log("[Info] No active auto-spawned VMs to delete.")
        return

    for vm in auto_vms:
        vmid = vm["vmid"]
        name = vm["name"]
        try:
            log(f"[-] Deleting VM {name} ({vmid})")
            proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.stop.post()
            time.sleep(2)
            proxmox.nodes(PROXMOX_NODE).qemu(vmid).delete()
            log(f"[✓] Deleted VM {name}")
        except Exception as e:
            log(f"[!] Failed to delete VM {name}: {e}")

    log(f"[✓] All {len(auto_vms)} auto-spawned VMs deleted successfully.")

# -----------------------
# Continuous Sync (every 1 minute)
# -----------------------

def sync_vms():

    global _last_heartbeat

    now = datetime.now()
    current_time = now.time()
    start = datetime.strptime(SPAWN_TIME, "%H:%M").time()
    end = datetime.strptime(DELETE_TIME, "%H:%M").time()

    
    within_schedule = (
            start <= current_time <= end if start < end else (current_time >= start or current_time <= end)
    )

    # --- Heartbeat (once per hour) ---
    if _last_heartbeat is None or (now - _last_heartbeat).seconds >= 3600:
        log(f"[Info] Scheduler active — monitoring Guacamole & Proxmox.")
        _last_heartbeat = now

    # Skip silently if outside window
    if not within_schedule:
        return

    # --- Get Guacamole connections ---
    conns = get_connections_in_range()
    if not conns:
        
        return

    # --- Connect to Proxmox ---
    proxmox = connect_proxmox()
    if not proxmox:
        log("[!] Cannot connect to Proxmox.")
        return

    # --- Fetch all existing VMs in Proxmox ---
    try:
        existing_vms = proxmox.nodes(PROXMOX_NODE).qemu.get()
        existing_names = {vm["name"] for vm in existing_vms}
    except Exception as e:
        log(f"[!] Failed to fetch VM list from Proxmox: {e}")
        return

    # --- Determine which VMs need to be created ---
    new_conns = []
    for username, ip in conns:
        vm_name = f"{VM_NAME_PREFIX}-{username.lower()}"
        if vm_name not in existing_names:
            new_conns.append((username, ip))

    if not new_conns:
        return  # Silent if no new connections

    # --- Log and create new VMs ---
    log(f"[+] Found {len(new_conns)} new Guacamole connections: {[ip for _, ip in new_conns]}")
    vmid = next_available_vmid(proxmox)
    for username, ip in new_conns:
        vm_info = create_vm(vmid, username, ip)
        if vm_info:
            log(f"[✓] Created {vm_info['name']} ({ip})")
        else:
            log(f"[!] Failed to create VM for {username} ({ip})")
        vmid += 1
    log(f"[✓] Sync complete: {len(new_conns)} new VMs created.")
