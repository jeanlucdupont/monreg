import win32api
import win32con
import threading
import time

REG_NOTIFY_CHANGE_NAME          = 0x00000001
REG_NOTIFY_CHANGE_ATTRIBUTES    = 0x00000002
REG_NOTIFY_CHANGE_LAST_SET      = 0x00000004
REG_NOTIFY_CHANGE_SECURITY      = 0x00000008
REG_NOTIFY_FILTER               = ( REG_NOTIFY_CHANGE_NAME | REG_NOTIFY_CHANGE_ATTRIBUTES | REG_NOTIFY_CHANGE_LAST_SET | REG_NOTIFY_CHANGE_SECURITY)

def f_snapshot(hive, subkey=""):
    snapshot = {"values": {}, "subkeys": {}}
    try:
        key_handle = win32api.RegOpenKeyEx(hive, subkey, 0, win32con.KEY_READ)
    except Exception:
       return snapshot
    i = 0
    while 42:
        try:
            value_name, value_data, _value_type = win32api.RegEnumValue(key_handle, i)
            snapshot["values"][value_name] = value_data
            i += 1
        except win32api.error:
            break
    i = 0
    while 42:
        try:
            subkey_name = win32api.RegEnumKey(key_handle, i)
            i += 1
            sub_snapshot = f_snapshot(hive, f"{subkey}\\{subkey_name}" if subkey else subkey_name)
            snapshot["subkeys"][subkey_name] = sub_snapshot
        except win32api.error:
            break
    return snapshot

def f_comparesnapshot(oldsnap, newsnap, path=""):
    changes     = []
    oldval      = oldsnap["values"]
    newval      = newsnap["values"]
    for val_name in oldval:
        if val_name not in newval:
            changes.append(f"[Removed value] {path}: {val_name} = {oldval[val_name]}")
        else:
            if oldval[val_name] != newval[val_name]:
                changes.append(f"[Modified value] {path}: {val_name} from {oldval[val_name]} to {newval[val_name]}")
    for val_name in newval:
        if val_name not in oldval:
            changes.append(f"[Add value] {path}: {val_name} = {newval[val_name]}")
    oldsubkeys  = oldsnap["subkeys"]
    newsubkeys  = newsnap["subkeys"]
    for oldsubkey in oldsubkeys:
        if oldsubkey not in newsubkeys:
            changes.append(f"[Removed subkey] {path}\\{oldsubkey}")
        else:
            sub_path        = f"{path}\\{oldsubkey}" if path else oldsubkey
            deeper_changes  = f_comparesnapshot(oldsubkeys[oldsubkey], newsubkeys[oldsubkey], sub_path)
            changes.extend(deeper_changes)
    for newsubkey in newsubkeys:
        if newsubkey not in oldsubkeys:
            changes.append(f"[Added subkey] {path}\\{newsubkey}")
    return changes

def f_monreg(hive, subkey=""):
    try:
        regkey = win32api.RegOpenKeyEx(hive, subkey, 0, win32con.KEY_READ)
    except Exception as e:
        print(f"Failure: {e}")
        return
    oldsnapshot = f_snapshot(hive, subkey)
    while 42:
        try:
            win32api.RegNotifyChangeKeyValue(regkey, True, REG_NOTIFY_FILTER, None, False)
            newsnapshot = f_snapshot(hive, subkey)
            changes     = f_comparesnapshot(oldsnapshot, newsnapshot, subkey)
            if changes:
                for change in changes:
                    print(change)
            oldsnapshot = newsnapshot
        except Exception as e:
            print(f"Failure '{subkey}': {e}")
            break

# ----------------
# Main
# ----------------
watcher_thread  = threading.Thread(target=f_monreg, args=(win32con.HKEY_LOCAL_MACHINE, "Software"), daemon=True)
watcher_thread.start()
try:
    while 42:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
