# main.py
import schedule, time
from autoscale_manager import spawn_vms, delete_vms, sync_vms
from config import SPAWN_TIME, DELETE_TIME
from logger import log

if __name__ == "__main__":
    log(f"🚀 Auto-Spawner active — spawn at {SPAWN_TIME}, delete at {DELETE_TIME}")

    try:
        schedule.every().day.at(SPAWN_TIME).do(spawn_vms)
        schedule.every().day.at(DELETE_TIME).do(delete_vms)
        schedule.every(1).minutes.do(sync_vms)

        while True:
            try:
                schedule.run_pending()
            except Exception as e:
                log(f"[!] Scheduler runtime error: {e}")
            time.sleep(10)

    except KeyboardInterrupt:
        log("[🛑] Script manually stopped.")
