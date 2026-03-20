import math
from itertools import combinations

import streamlit as st
from ortools.sat.python import cp_model

st.set_page_config(page_title="Euchre Tournament Scheduler", layout="wide")

# =========================================================
# Helpers: input
# =========================================================

def normalize_names(raw_text: str) -> list[str]:
    """Parse one name per line, remove blanks, preserve order, remove duplicates."""
    seen = set()
    names = []
    for line in raw_text.splitlines():
        name = line.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


# =========================================================
# Helpers: partner schedule (hard constraint)
# =========================================================

def generate_partner_rounds(players: list[str]) -> list[dict]:
    """
    Create rounds of partner pairs using the circle method.
    Each player partners every other player exactly once.

    Returns a list of dicts:
      {
        "pairs": [(a,b), (c,d), ...],
        "bye": <player_or_none>
      }

    If odd number of players, one player gets a BYE each round.
    """
    arr = players[:]
    ghost = None

    if len(arr) % 2 == 1:
        ghost = "__BYE__"
        arr.append(ghost)

    n = len(arr)
    rounds = []

    for _ in range(n - 1):
        pairs = []
        bye = None

        for i in range(n // 2):
            a = arr[i]
            b = arr[n - 1 - i]

            if ghost in (a, b):
                bye = b if a == ghost else a
            else:
                pairs.append((a, b))

        rounds.append({
            "pairs": pairs,
            "bye": bye
        })

        # Rotate all but first
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    return rounds


# =========================================================
# Helpers: exact opponent solver
# =========================================================

def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def opponent_target(players: list[str], partner_rounds: list[dict]) -> float:
    """Average ideal opponent count per player pair."""
    total_pairs = math.comb(len(players), 2)
    total_opponent_pair_events = 0

    for rnd in partner_rounds:
        table_count = len(rnd["pairs"]) // 2
        total_opponent_pair_events += table_count * 4

    return total_opponent_pair_events / total_pairs


def opponent_low_high(players: list[str], partner_rounds: list[dict]) -> tuple[int, int, float]:
    target = opponent_target(players, partner_rounds)
    return math.floor(target), math.ceil(target), target


def all_table_pairings_even(teams: list[tuple[str, str]]) -> list[list[tuple[tuple[str, str], tuple[str, str]]]]:
    """
    Return all ways to pair an even number of teams into tables.
    Example:
      [T1,T2,T3,T4] ->
      [
        [(T1,T2),(T3,T4)],
        [(T1,T3),(T2,T4)],
        [(T1,T4),(T2,T3)]
      ]
    """
    if not teams:
        return [[]]

    first = teams[0]
    results = []

    for i in range(1, len(teams)):
        second = teams[i]
        remaining = teams[1:i] + teams[i + 1:]
        for rest in all_table_pairings_even(remaining):
            results.append([(first, second)] + rest)

    return results


def layout_opponent_pairs(
    tables: list[tuple[tuple[str, str], tuple[str, str]]]
) -> set[tuple[str, str]]:
    """Return the set of player-pairs who oppose each other in this layout."""
    opposed = set()

    for team1, team2 in tables:
        a, b = team1
        c, d = team2
        opposed.add(pair_key(a, c))
        opposed.add(pair_key(a, d))
        opposed.add(pair_key(b, c))
        opposed.add(pair_key(b, d))

    return opposed


def copy_opp_counts(opp_counts):
    return {p: opp_counts[p].copy() for p in opp_counts}


def exact_score_from_counts(players, opp_counts, target):
    vals = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            vals.append(opp_counts[a][b])

    max_dev = max(abs(v - target) for v in vals)
    sse = sum((v - target) ** 2 for v in vals)
    spread = max(vals) - min(vals)
    zeros = sum(1 for v in vals if v == 0)
    above = sum(1 for v in vals if v > target)

    return (max_dev, sse, spread, zeros, above)


def all_round_layouts_small(teams):
    """
    Exact layouts for one round.
    If odd number of teams, one team sits out.
    """
    layouts = []

    if len(teams) % 2 == 0:
        for tables in all_table_pairings_even(teams):
            layouts.append({
                "tables": tables,
                "sit_out_team": []
            })
    else:
        for i in range(len(teams)):
            sit_out_team = teams[i]
            remaining = teams[:i] + teams[i + 1:]
            for tables in all_table_pairings_even(remaining):
                layouts.append({
                    "tables": tables,
                    "sit_out_team": list(sit_out_team)
                })

    return layouts


def build_schedule_exact_small(players: list[str]) -> list[dict]:
    """
    Exact backtracking search for small cases like 8 and 9 players.
    Much faster on Streamlit Cloud than CP-SAT for these sizes.
    """
    partner_rounds = generate_partner_rounds(players)
    target = opponent_target(players, partner_rounds)

    if abs(target - round(target)) > 1e-9:
        raise ValueError(
            f"Exact equal opponent counts are impossible for {len(players)} players because "
            f"the ideal average opponent count is {target:.4f}, not an integer."
        )

    target = int(round(target))

    layouts_by_round = []
    for rnd in partner_rounds:
        teams = [tuple(pair) for pair in rnd["pairs"]]
        layouts = all_round_layouts_small(teams)
        layouts_by_round.append(layouts)

    empty_opp_counts = {p: {q: 0 for q in players if q != p} for p in players}

    best_score = None
    best_layouts = None

    def search(round_idx, opp_counts, chosen_layouts):
        nonlocal best_score, best_layouts

        if round_idx == len(layouts_by_round):
            score = exact_score_from_counts(players, opp_counts, target)
            if best_score is None or score < best_score:
                best_score = score
                best_layouts = chosen_layouts[:]
            return

        for layout in layouts_by_round[round_idx]:
            new_counts = copy_opp_counts(opp_counts)
            apply_tables_to_opp_counts(new_counts, layout["tables"])
            chosen_layouts.append(layout)
            search(round_idx + 1, new_counts, chosen_layouts)
            chosen_layouts.pop()

    search(0, empty_opp_counts, [])

    if best_layouts is None:
        raise ValueError("No exact layout was found.")

    schedule = []

    for round_index, (rnd, chosen) in enumerate(zip(partner_rounds, best_layouts), start=1):
        teams = [tuple(pair) for pair in rnd["pairs"]]
        bye = rnd["bye"]

        sit_out_players = []
        if bye is not None:
            sit_out_players.append(bye)
        sit_out_players.extend(chosen["sit_out_team"])

        round_data = {
            "round_number": round_index,
            "partner_pairs": [list(pair) for pair in teams],
            "bye": bye,
            "sit_out_team": chosen["sit_out_team"],
            "sit_out": sit_out_players,
            "tables": []
        }

        for table_num, (team1, team2) in enumerate(chosen["tables"], start=1):
            round_data["tables"].append({
                "table": table_num,
                "team1": list(team1),
                "team2": list(team2)
            })

        schedule.append(round_data)

    return schedule


def build_schedule(players: list[str], time_limit_seconds: int = 120) -> list[dict]:
    """
    Exact-only schedule builder.
    Uses specialized exact search for small sizes.
    Uses CP-SAT for larger exact-feasible sizes up to 20.
    """
    n = len(players)

    if n < 4:
        raise ValueError("You need at least 4 players.")

    if n > 20:
        raise ValueError("This version is configured only for exact schedules up to 20 players.")

    if n % 4 not in (0, 1):
        raise ValueError(
            f"Exact equal opponent counts are impossible for {n} players under your rules. "
            f"Use 4, 5, 8, 9, 12, 13, 16, 17, or 20 players for exact schedules."
        )

    # Fast exact search for small cases
    if n <= 9:
        return build_schedule_exact_small(players)

    # CP-SAT for larger exact-feasible cases
    return build_schedule_exact(players, time_limit_seconds=time_limit_seconds)


# =========================================================
# Helpers: stats / validation
# =========================================================

def partner_summary(players: list[str], schedule: list[dict]) -> dict:
    """
    Count partnerships using the partner pair list.
    """
    counts = {p: {q: 0 for q in players if q != p} for p in players}

    for rnd in schedule:
        for a, b in rnd["partner_pairs"]:
            counts[a][b] += 1
            counts[b][a] += 1

    return counts


def opponent_summary(players: list[str], schedule: list[dict]) -> dict:
    """
    Count how many times each player-pair opposed one another.
    """
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


def final_opponent_score_exact(
    players: list[str], opp_counts: dict, target: float
) -> tuple[float, float, int, int, int]:
    """
    Score summary for the exact case.
    Lower is better.
    """
    vals = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            vals.append(opp_counts[a][b])

    max_dev = max(abs(v - target) for v in vals)
    sse = sum((v - target) ** 2 for v in vals)
    spread = max(vals) - min(vals)
    zeros = sum(1 for v in vals if v == 0)
    above_target = sum(1 for v in vals if v > target)

    return max_dev, sse, spread, zeros, above_target


def count_sitouts(schedule: list[dict]) -> dict:
    sit = {}
    for rnd in schedule:
        for p in rnd["sit_out"]:
            sit[p] = sit.get(p, 0) + 1
    return sit


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
        st.session_state.schedule = build_schedule(players, time_limit_seconds=120)
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

This version uses an exact solver for **20 or fewer players** when exact equal opponent
counts are mathematically possible. Valid exact player counts are:

**4, 5, 8, 9, 12, 13, 16, 17, 20**
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
        opp_low, opp_high, opp_target = opponent_low_high(players, generate_partner_rounds(players))
        opp_score = final_opponent_score_exact(players, opp_counts, opp_target)

        sits = count_sitouts(schedule)
        sit_vals = [sits.get(p, 0) for p in players]

        st.write(f"Ideal average opponent count per pair: {opp_target:.4f}")
        st.write(f"Desired opponent band: {opp_low} to {opp_high}")
        st.write(
            f"Pairs outside desired band: "
            f"{sum(1 for a, b in combinations(players, 2) if opp_counts[a][b] != opp_target)} | "
            f"SSE from target: {opp_score[1]:.2f} | "
            f"Spread: {opp_score[2]} | "
            f"Max: {max(opp_counts[a][b] for a, b in combinations(players, 2))} | "
            f"Min: {min(opp_counts[a][b] for a, b in combinations(players, 2))}"
        )

        st.markdown("**Sit-out balance**")
        st.write(
            f"Total sit-out slots: {sum(sit_vals)} | "
            f"Best possible sit-out range: {min(sit_vals)} to {max(sit_vals)}"
        )
        st.write(
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
