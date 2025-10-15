# proxmox_utils.py
import time
from proxmoxer import ProxmoxAPI
from config import *
from logger import log

def connect_proxmox(retries=3, delay=5):
    """Connect to Proxmox API using token."""
    for attempt in range(1, retries + 1):
        try:
            proxmox = ProxmoxAPI(
                PROXMOX_HOST,
                user=PROXMOX_USER,
                token_name=PROXMOX_TOKEN_NAME,
                token_value=PROXMOX_TOKEN_VALUE,
                verify_ssl=False
            )
            return proxmox
        except Exception as e:
            log(f"[!] Failed to connect to Proxmox (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                log("[✗] Giving up after repeated Proxmox connection failures.")
                return None

def vm_exists(proxmox, name=None, ip=None):
    """Check if a VM with the same name or IP already exists."""
    try:
        vms = proxmox.nodes(PROXMOX_NODE).qemu.get()
        for vm in vms:
            if name and vm.get("name") == name:
                return True
            if ip and "ip" in vm and vm["ip"] == ip:  # Only works if guest agent reports IP
                return True
        return False
    except Exception as e:
        log(f"[!] Failed to check existing VMs: {e}")
        return False
    
def next_available_vmid(proxmox):
    """Return the next unused VMID based on current Proxmox state."""
    try:
        used_ids = {int(vm["vmid"]) for vm in proxmox.cluster.resources.get(type="vm")}
        vmid = VM_ID_START
        while vmid in used_ids:
            vmid += 1
        return vmid
    except Exception as e:
        log(f"[!] Could not determine next VMID: {e}")
        return VM_ID_START

def create_vm(vmid, username, ip):
    proxmox = connect_proxmox()
    if not proxmox:
        log(f"[!] Skipping VM creation for {username} ({ip}) — Proxmox unreachable.")
        return None

    vm_name = f"{VM_NAME_PREFIX}-{username.lower()}"

    if vm_exists(proxmox, name=vm_name):
        log(f"[⚠️] VM '{vm_name}' already exists, skipping creation.")
        return None
    
    try:
        log(f"[+] Creating VM {vm_name} ({ip}) → ID {vmid}")

        proxmox.nodes(PROXMOX_NODE).qemu(TEMPLATE_ID).clone.post(
            newid=vmid,
            name=vm_name,
            target=PROXMOX_NODE,
            full=0,  # use full clone; set to 0 for linked clone
        )

        proxmox.nodes(PROXMOX_NODE).qemu(vmid).config.post(
            ciuser=Ci_USER,
            cipassword=Ci_PASSWORD,
            ipconfig0=f"ip={ip}/24,gw={GATEWAY}",
            nameserver=DNS
        )

        proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post()
        log(f"[✓] VM {vm_name} started successfully")
        return {"vmid": vmid, "name": vm_name, "ip": ip, "user": username}
    
    except Exception as e:
        log(f"[!] Error creating VM {vm_name}: {e}")
        return None
    
def delete_vm(vmid, name):
    proxmox = connect_proxmox()
    log(f"[-] Deleting VM {name} ({vmid})")
    try:
        proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.stop.post()
        time.sleep(3)
        proxmox.nodes(PROXMOX_NODE).qemu(vmid).delete()
        log(f"[✓] Deleted VM {name}")
    except Exception as e:
        log(f"[!] Error deleting VM {name}: {e}")
