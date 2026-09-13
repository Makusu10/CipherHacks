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
