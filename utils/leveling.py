BANDS = [
    ("recruit", 1, 10, "Recruit"),
    ("operator", 11, 25, "Operator"),
    ("analyst", 26, 45, "Analyst"),
    ("specialist", 46, 70, "Specialist"),
    ("redteam", 71, 90, "Red Team"),
    ("apex", 91, 100, "Apex"),
]

CHECKPOINT_FOR_BAND = {
    "recruit": "recruit-checkpoint",
    "operator": "operator-checkpoint",
    "analyst": "analyst-checkpoint",
    "specialist": "specialist-checkpoint",
    "redteam": "redteam-checkpoint",
    "apex": "apex-checkpoint",
}

def xp_needed_for_level(level: int) -> int:
    # cost to go from `level` to `level+1`
    return 80 + level * 20

def level_from_xp(xp: int) -> int:
    lvl = 1
    remaining = xp
    while lvl < 100:
        cost = xp_needed_for_level(lvl)
        if remaining < cost:
            break
        remaining -= cost
        lvl += 1
    return lvl

def band_for_level(level: int) -> str:
    for slug, lo, hi, _ in BANDS:
        if lo <= level <= hi:
            return slug
    return "apex"

def band_label(slug: str) -> str:
    for s, _lo, _hi, label in BANDS:
        if s == slug:
            return label
    return slug

def elo_expected(a: int, b: int) -> float:
    return 1.0 / (1.0 + 10 ** ((b - a) / 400.0))

def elo_delta(player: int, opponent: int, score: float, k: int = 32) -> int:
    return round(k * (score - elo_expected(player, opponent)))

# Narrative rank titles: level → character title. Bands stay the unlock truth;
# titles are the game skin on top.
RANK_TITLES = [
    (1, "Street Awake"), (4, "Password Rat"), (7, "Phish Spotter"),
    (11, "Cable Runner"), (16, "Port Knocker"), (21, "Shell Tender"),
    (26, "Paper Trail"), (32, "Scan Reader"), (39, "Bug Dio"),
    (46, "Hash Smuggler"), (53, "Escalationist"), (60, "Overflow Orphan"),
    (65, "Graph Walker"),
    (71, "Chain Binder"), (77, "Fetcher's Bane"), (83, "Sandbox Ghost"), (88, "Cloud Leech"),
    (91, "Incident Calm"), (96, "Bossbreaker"), (100, "Apex Myth"),
]

BAND_DOSSIER = {
    "recruit": ("Case 01 — The Leaky Block", "Neighbors click everything. Your job: lock the block down before the next barangay-wide phishing wave. No terminal. Paper, habits, eyes."),
    "operator": ("Case 02 — The Basement Switch", "A dead switch hums in a flooded basement. Learn its language — packets, ports, permissions — and it talks. Terminal goes live here."),
    "analyst": ("Case 03 — Alon Freight", "A fictional shipper leaks like a sieve. Footprint it, scan it, read its broken web app — then write the fix memo. Hints cost 1.5x now."),
    "specialist": ("Case 04 — The Locked Rooms", "Five sealed practice boxes: escalation, hashes, a caged overflow, a drawn AD graph, a hostile spectrum. Multi-step or nothing. Hints 2x."),
    "redteam": ("Case 05 — The Long Chain", "One fictional campaign, four hops: chain it like ATT&CK, fetch what you shouldn't, read fake clouds. Hints 2.5x, hand-holding gone."),
    "apex": ("Case 06 — Blackout Night", "City dark, logs screaming. Triage the bundle, chain every skill under a timer, then decide: prestige back to 1 with a badge, or hold the myth seat."),
}

def rank_title(level: int) -> str:
    title = RANK_TITLES[0][1]
    for lo, name in RANK_TITLES:
        if level >= lo:
            title = name
    return title

def xp_for_level(level: int) -> int:
    total, lvl = 0, 1
    while lvl < level:
        total += xp_needed_for_level(lvl)
        lvl += 1
    return total

def progress_to_next(xp: int) -> tuple:
    lvl = level_from_xp(xp)
    if lvl >= 100:
        return (100, 1, 1)
    base = xp_for_level(lvl)
    cost = xp_needed_for_level(lvl)
    return (lvl, max(0, xp - base), cost)
