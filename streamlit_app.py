import math
from itertools import combinations

import streamlit as st

st.set_page_config(page_title="Euchre Tournament Scheduler", layout="wide")

# =========================================================
# PRECOMPUTED TEMPLATE FORMAT
# =========================================================
# Each template is a list of rounds.
# Each round is a list of partner-pairs, in table order:
# [
#   [[a,b], [c,d], [e,f], [g,h], ...],
#   ...
# ]
#
# Every 2 partner-pairs make one table:
#   pair 1 vs pair 2
#   pair 3 vs pair 4
#   ...
#
# For odd player counts like 17 or 21, include a "BYE" placeholder in the
# templates if your external schedule source uses one, or store rounds in the
# alternate dict format shown below in the placeholder notes.


# =========================================================
# VERIFIED TEMPLATE: 16 PLAYERS
# Source-derived exact whist schedule
# =========================================================

TEMPLATE_16 = [
    [[16, 1], [9, 14], [2, 4], [5, 8], [3, 10], [12, 13], [6, 15], [7, 11]],
    [[16, 2], [10, 15], [3, 5], [6, 9], [4, 11], [13, 14], [7, 1], [8, 12]],
    [[16, 3], [11, 1], [4, 6], [7, 10], [5, 12], [14, 15], [8, 2], [9, 13]],
    [[16, 4], [12, 2], [5, 7], [8, 11], [6, 13], [15, 1], [9, 3], [10, 14]],
    [[16, 5], [13, 3], [6, 8], [9, 12], [7, 14], [1, 2], [10, 4], [11, 15]],
    [[16, 6], [14, 4], [7, 9], [10, 13], [8, 15], [2, 3], [11, 5], [12, 1]],
    [[16, 7], [15, 5], [8, 10], [11, 14], [9, 1], [3, 4], [12, 6], [13, 2]],
    [[16, 8], [1, 6], [9, 11], [12, 15], [10, 2], [4, 5], [13, 7], [14, 3]],
    [[16, 9], [2, 7], [10, 12], [13, 1], [11, 3], [5, 6], [14, 8], [15, 4]],
    [[16, 10], [3, 8], [11, 13], [14, 2], [12, 4], [6, 7], [15, 9], [1, 5]],
    [[16, 11], [4, 9], [12, 14], [15, 3], [13, 5], [7, 8], [1, 10], [2, 6]],
    [[16, 12], [5, 10], [13, 15], [1, 4], [14, 6], [8, 9], [2, 11], [3, 7]],
    [[16, 13], [6, 11], [14, 1], [2, 5], [15, 7], [9, 10], [3, 12], [4, 8]],
    [[16, 14], [7, 12], [15, 2], [3, 6], [1, 8], [10, 11], [4, 13], [5, 9]],
    [[16, 15], [8, 13], [1, 3], [4, 7], [2, 9], [11, 12], [5, 14], [6, 10]],
]

# =========================================================
# PLACEHOLDERS YOU CAN REPLACE LATER
# =========================================================
# Replace None with your verified templates when ready.
#
# For 17 and 21 players, you can use one of two formats:
#
# FORMAT A (simple list format, if your source already omits the bye pair):
# TEMPLATE_17 = [
#   [[17,1], [2,3], [4,5], ...],   # even number of real partner pairs
#   ...
# ]
#
# FORMAT B (dict format if you want to explicitly store a bye):
# TEMPLATE_17 = [
#   {
#     "pairs": [[a,b], [c,d], ...],
#     "bye": 17
#   },
#   ...
# ]
#
# The code below supports both formats.

TEMPLATE_17 = None
TEMPLATE_20 = None
TEMPLATE_21 = None

PRECOMPUTED_TEMPLATES = {
    16: TEMPLATE_16,
    17: TEMPLATE_17,
    20: TEMPLATE_20,
    21: TEMPLATE_21,
}


# =========================================================
# Template conversion / mapping
# =========================================================

def normalize_names(raw_text: str) -> list[str]:
    seen = set()
    names = []
    for line in raw_text.splitlines():
        name = line.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def map_num_to_name(x, players: list[str]) -> str:
    """
    Maps 1-based template numbers to player names.
    """
    if isinstance(x, str):
        return x
    return players[x - 1]


def convert_round_from_template(round_template, players: list[str], round_number: int) -> dict:
    """
    Supports two round formats:
    1) list of pairs:
       [[1,2], [3,4], [5,6], [7,8]]
    2) dict:
       {"pairs": [[1,2], [3,4], ...], "bye": 17}
    """
    if isinstance(round_template, dict):
        raw_pairs = round_template.get("pairs", [])
        bye = round_template.get("bye")
    else:
        raw_pairs = round_template
        bye = None

    partner_pairs = [[map_num_to_name(a, players), map_num_to_name(b, players)] for a, b in raw_pairs]

    tables = []
    for i in range(0, len(partner_pairs), 2):
        if i + 1 >= len(partner_pairs):
            break
        tables.append({
            "table": len(tables) + 1,
            "team1": partner_pairs[i],
            "team2": partner_pairs[i + 1],
        })

    sit_out = []
    if bye is not None:
        sit_out.append(map_num_to_name(bye, players))

    return {
        "round_number": round_number,
        "partner_pairs": partner_pairs,
        "bye": map_num_to_name(bye, players) if bye is not None else None,
        "sit_out_team": [],
        "sit_out": sit_out,
        "tables": tables,
    }


def build_schedule_from_template(players: list[str]) -> list[dict]:
    n = len(players)

    if n in (18, 19):
        raise ValueError(
            f"A perfect schedule is not possible for {n} players under your rules. "
            f"Supported perfect sizes here are 16, 17, 20, and 21."
        )

    if n not in PRECOMPUTED_TEMPLATES:
        raise ValueError(
            "This version is configured for 16, 17, 20, and 21 players only."
        )

    template = PRECOMPUTED_TEMPLATES[n]
    if template is None:
        raise ValueError(
            f"The precomputed template for {n} players is still a placeholder. "
            f"Replace TEMPLATE_{n} in the file with your verified round list."
        )

    return [
        convert_round_from_template(round_template, players, i + 1)
        for i, round_template in enumerate(template)
    ]


# =========================================================
# Validation helpers
# =========================================================

def partner_summary(players: list[str], schedule: list[dict]) -> dict:
    counts = {p: {q: 0 for q in players if q != p} for p in players}
    for rnd in schedule:
        for a, b in rnd["partner_pairs"]:
            counts[a][b] += 1
            counts[b][a] += 1
    return counts


def opponent_summary(players: list[str], schedule: list[dict]) -> dict:
    counts = {p: {q: 0 for q in players if q != p} for p in players}
    for rnd in schedule:
        for t in rnd["tables"]:
            a, b = t["team1"]
            c, d = t["team2"]
            for x in (a, b):
                for y in (c, d):
                    counts[x][y] += 1
                    counts[y][x] += 1
    return counts


def opponent_balance_report(players: list[str], schedule: list[dict]) -> list[tuple[str, str, int]]:
    counts = opponent_summary(players, schedule)
    rows = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            rows.append((a, b, counts[a][b]))
    return rows


def count_sitouts(schedule: list[dict]) -> dict:
    sit = {}
    for rnd in schedule:
        for p in rnd["sit_out"]:
            sit[p] = sit.get(p, 0) + 1
    return sit


def opponent_target_from_schedule(players: list[str], schedule: list[dict]) -> float:
    total_pairs = math.comb(len(players), 2)
    total_opponent_pair_events = 0
    for rnd in schedule:
        total_opponent_pair_events += len(rnd["tables"]) * 4
    return total_opponent_pair_events / total_pairs


# =========================================================
# Session helpers
# =========================================================

def reset_tournament():
    st.session_state.players = []
    st.session_state.schedule = []
    st.session_state.current_round = 0
    st.session_state.generated = False
    st.session_state.error = ""


def generate_tournament(names_text: str):
    players = normalize_names(names_text)

    if len(players) < 4:
        st.session_state.error = "You need at least 4 players."
        st.session_state.generated = False
        st.session_state.schedule = []
        st.session_state.current_round = 0
        return

    try:
        st.session_state.players = players
        st.session_state.schedule = build_schedule_from_template(players)
        st.session_state.current_round = 0
        st.session_state.generated = True
        st.session_state.error = ""
    except Exception as e:
        st.session_state.error = str(e)
        st.session_state.generated = False
        st.session_state.schedule = []
        st.session_state.current_round = 0


def next_round():
    if st.session_state.current_round < len(st.session_state.schedule) - 1:
        st.session_state.current_round += 1


def prev_round():
    if st.session_state.current_round > 0:
        st.session_state.current_round -= 1


# =========================================================
# Session state init
# =========================================================

if "players" not in st.session_state:
    st.session_state.players = []

if "schedule" not in st.session_state:
    st.session_state.schedule = []

if "current_round" not in st.session_state:
    st.session_state.current_round = 0

if "generated" not in st.session_state:
    st.session_state.generated = False

if "error" not in st.session_state:
    st.session_state.error = ""


# =========================================================
# UI
# =========================================================

st.title("Euchre Tournament Scheduler")

st.markdown(
    """
Paste one player name per line, generate the tournament once, and use the round buttons
to move through the schedule.

This version is template-backed for **perfect schedules** at:
**16, 17, 20, and 21 players**

Right now:
- **16 players** is loaded
- **17, 20, and 21** are placeholders you can replace later
- **18 and 19** are intentionally rejected
"""
)

with st.expander("Enter player names", expanded=not st.session_state.generated):
    names_text = st.text_area(
        "One player per line",
        value="",
        height=220,
        key="names_input"
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.button(
            "Generate Tournament",
            key="generate_btn",
            on_click=generate_tournament,
            args=(names_text,)
        )
    with c2:
        st.button(
            "Reset",
            key="reset_btn",
            on_click=reset_tournament
        )

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.generated and st.session_state.schedule:
    schedule = st.session_state.schedule
    idx = st.session_state.current_round
    round_data = schedule[idx]
    players = st.session_state.players

    top1, top2, top3 = st.columns([1, 1, 1])
    with top1:
        st.metric("Players", len(players))
    with top2:
        st.metric("Current Round", f"{idx + 1} / {len(schedule)}")
    with top3:
        st.metric("Tables This Round", len(round_data["tables"]))

    st.subheader(f"Round {round_data['round_number']}")

    tables = round_data["tables"]

    if tables:
        cols_per_row = 3
        for row_start in range(0, len(tables), cols_per_row):
            row_tables = tables[row_start:row_start + cols_per_row]
            cols = st.columns(len(row_tables))

            for col, table in zip(cols, row_tables):
                with col:
                    st.markdown(
                        f"""
<div style="border:1px solid #d9d9d9; border-radius:12px; padding:16px; margin-bottom:12px;">
    <h4 style="margin-top:0;">Table {table["table"]}</h4>
    <p style="margin-bottom:6px;"><strong>Team 1:</strong> {table["team1"][0]} + {table["team1"][1]}</p>
    <p style="margin-bottom:0;"><strong>Team 2:</strong> {table["team2"][0]} + {table["team2"][1]}</p>
</div>
""",
                        unsafe_allow_html=True
                    )
    else:
        st.info("No active tables in this round.")

    if round_data["sit_out"]:
        st.warning("Sitting out this round: " + ", ".join(round_data["sit_out"]))
    else:
        st.success("No sit-outs this round.")

    nav1, nav2, nav3 = st.columns([1, 1, 1])
    with nav1:
        st.button("Previous Round", key="prev_round_btn", on_click=prev_round)
    with nav2:
        st.button("Next Round", key="next_round_btn", on_click=next_round)
    with nav3:
        if idx == len(schedule) - 1:
            st.success("Final round reached.")
        else:
            st.write("")

    with st.expander("Validation / stats"):
        partner_counts = partner_summary(players, schedule)
        opp_counts = opponent_summary(players, schedule)
        opp_target = opponent_target_from_schedule(players, schedule)

        st.write(f"Ideal average opponent count per pair: {opp_target:.4f}")
        st.write(f"Desired opponent band: {math.floor(opp_target)} to {math.ceil(opp_target)}")

        outside = sum(
            1 for a, b in combinations(players, 2)
            if opp_counts[a][b] != opp_target
        )
        max_opp = max(opp_counts[a][b] for a, b in combinations(players, 2))
        min_opp = min(opp_counts[a][b] for a, b in combinations(players, 2))
        sse = sum(
            (opp_counts[a][b] - opp_target) ** 2
            for a, b in combinations(players, 2)
        )

        st.write(
            f"Pairs outside desired band: {outside} | "
            f"SSE from target: {sse:.2f} | "
            f"Spread: {max_opp - min_opp} | "
            f"Max: {max_opp} | "
            f"Min: {min_opp}"
        )

        sits = count_sitouts(schedule)
        sit_vals = [sits.get(p, 0) for p in players]

        st.markdown("**Sit-out balance**")
        st.write(
            f"Total sit-out slots: {sum(sit_vals)} | "
            f"Actual sit-out minimum: {min(sit_vals)} | "
            f"Actual sit-out maximum: {max(sit_vals)}"
        )

        st.markdown("**Partner counts**")
        partner_issues = []
        for a, b in combinations(players, 2):
            if partner_counts[a][b] != 1:
                partner_issues.append(f"{a} & {b}: {partner_counts[a][b]}")

        if partner_issues:
            st.error("Some partner counts are not exactly 1:")
            for issue in partner_issues:
                st.write(issue)
        else:
            st.success("Every player partners every other player exactly once.")

        st.markdown("**Opponent counts by pair**")
        rows = opponent_balance_report(players, schedule)
        for a, b, c in rows:
            st.write(f"{a} vs {b}: {c}")
