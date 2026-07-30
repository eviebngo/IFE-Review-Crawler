"""One-off: clear IFE system tags that were only inferred from the airline
lookup (not actually named in the title/transcript). The guess is preserved
in ife_system_guess; manually-set tags (ife_system_manual) are untouched.

Run:  python clear_inferred_systems.py
"""
from ife_data_manager import IFEDataManager

dm = IFEDataManager()
dm.reload_from_disk()
cleared = 0
for r in dm.data.get("reviews", []):
    if r.get("ife_system_inferred") and not r.get("ife_system_manual"):
        r["ife_system_guess"] = r.get("ife_system")
        r["ife_system"] = None
        r["ife_system_inferred"] = False
        cleared += 1
if cleared:
    dm.save_cache()
kept = sum(1 for r in dm.data.get("reviews", []) if r.get("ife_system"))
print(f"cleared {cleared} inferred tags; {kept} reviews keep an explicitly-detected system")
