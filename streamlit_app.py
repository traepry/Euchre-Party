import math
import random
from itertools import combinations

import streamlit as st

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

        # rotate all but first
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    return rounds


# =========================================================
# Helpers: opponent counts
# =========================================================

def make_empty_opp_counts(players):
    return {p: {q: 0 for q in players if q != p} for p in players}


def apply_tables_to_opp_counts(opp_counts, tables):
    for team1, team2 in tables:
        a, b = team1
        c, d = team2
        for x in (a, b):
            for y in (c, d):
                opp_counts[x][y] += 1
                opp_counts[y][x] += 1


def opponent_target(players, partner_rounds):
    """
    Average ideal opponent count per player pair.
    """
    total_pairs = math.comb(len(players), 2)
    total_opponent_pair_events = 0

    for rnd in partner_rounds:
        table_count = len(rnd["pairs"]) // 2
        total_opponent_pair_events += table_count * 4

    return total_opponent_pair_events / total_pairs


def opponent_low_high(players, partner_rounds):
    target = opponent_target(players, partner_rounds)
    return math.floor(target), math.ceil(target), target


def edge_penalty(c, low, high):
    """
    Penalty for final opponent count c.
    We want counts to fall in [low, high] whenever possible.
    """
    if c < low:
        return 1000 * (low - c) ** 2
    if c > high:
        return 3000 * (c - high) ** 2
    mid = (low + high) / 2.0
    return (c - mid) ** 2


def incremental_match_cost(team_a, team_b, opp_counts, low, high):
    """
    Cost of making team_a play against team_b right now.
    Lower is better.
    """
    a1, a2 = team_a
    b1, b2 = team_b

    cost = 0
    for x in (a1, a2):
        for y in (b1, b2):
            before = opp_counts[x][y]
            after = before + 1
            cost += edge_penalty(after, low, high) - edge_penalty(before, low, high)

    return cost


# =========================================================
# Helpers: sit-out balancing
# =========================================================

def compute_sitout_targets(players, partner_rounds, rng):
    """
    Compute the mathematically best possible sit-out totals per player.

    Final sit-out counts must differ by at most 1.
    Example for 30 players:
      total sit-outs = 58
      low = 1, high = 2
      exactly 28 players get 2
      exactly 2 players get 1

    Also respects mandatory BYEs from odd-player schedules.
    """
    n = len(players)
    mandatory = {p: 0 for p in players}
    total_slots = 0

    for rnd in partner_rounds:
        round_slots = 0

        if rnd["bye"] is not None:
            mandatory[rnd["bye"]] += 1
            round_slots += 1

        if len(rnd["pairs"]) % 2 == 1:
            round_slots += 2  # one partner-team sits out

        total_slots += round_slots

    low = total_slots // n
    high = low + (1 if total_slots % n else 0)
    num_high = total_slots - low * n

    # Everyone starts at the lower target
    targets = {p: low for p in players}

    # Anyone whose mandatory count exceeds low must be in the high bucket
    required_high = [p for p in players if mandatory[p] > low]
    required_high = list(dict.fromkeys(required_high))

    if len(required_high) > num_high:
        # Fallback: force minimum feasible target profile
        for p in players:
            targets[p] = max(low, mandatory[p])
        return targets, low, high, total_slots

    chosen_high = set(required_high)
    remaining = [p for p in players if p not in chosen_high]
    rng.shuffle(remaining)

    for p in remaining[:max(0, num_high - len(chosen_high))]:
        chosen_high.add(p)

    for p in chosen_high:
        targets[p] = high

    # Ensure mandatory constraints are satisfied
    for p in players:
        if targets[p] < mandatory[p]:
            targets[p] = mandatory[p]

    return targets, low, high, total_slots


def choose_sitout_team(teams, sit_counts, sit_targets, rng):
    """
    Choose one partner-team to sit out this round.

    Priority:
    1) Do not exceed final sit-out targets if possible
    2) Give sit-outs to players furthest below target
    3) Keep total sit-outs balanced
    """
    scored = []

    for team in teams:
        a, b = team
        after_a = sit_counts[a] + 1
        after_b = sit_counts[b] + 1

        over_target = max(0, after_a - sit_targets[a]) + max(0, after_b - sit_targets[b])
        remaining_deficit = max(0, sit_targets[a] - after_a) + max(0, sit_targets[b] - after_b)
        current_total = sit_counts[a] + sit_counts[b]

        scored.append((over_target, remaining_deficit, current_total, rng.random(), team))

    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    shortlist = scored[:min(4, len(scored))]
    return rng.choice(shortlist)[4]


def count_sitouts(schedule):
    sit = {}
    for rnd in schedule:
        for p in rnd["sit_out"]:
            sit[p] = sit.get(p, 0) + 1
    return sit


# =========================================================
# Helpers: round construction
# =========================================================

def greedy_pair_tables(teams, opp_counts, low, high, rng):
    """
    Randomized greedy pairing of partner-teams into tables.
    """
    remaining = teams[:]
    tables = []

    while remaining:
        # choose the most constrained team first
        team_scores = []
        for i, team_a in enumerate(remaining):
            candidate_costs = []
            for j, team_b in enumerate(remaining):
                if i == j:
                    continue
                candidate_costs.append(
                    incremental_match_cost(team_a, team_b, opp_counts, low, high)
                )

            if candidate_costs:
                team_scores.append((min(candidate_costs), rng.random(), i))

        team_scores.sort(reverse=True)
        _, _, idx_a = team_scores[0]
        team_a = remaining.pop(idx_a)

        match_options = []
        for j, team_b in enumerate(remaining):
            cost = incremental_match_cost(team_a, team_b, opp_counts, low, high)
            match_options.append((cost, rng.random(), j, team_b))

        match_options.sort(key=lambda x: (x[0], x[1]))
        shortlist = match_options[:min(3, len(match_options))]
        _, _, idx_b, team_b = rng.choice(shortlist)

        remaining.pop(idx_b)
        tables.append((team_a, team_b))

    return tables


def round_cost(tables, opp_counts, low, high):
    cost = 0
    for team1, team2 in tables:
        cost += incremental_match_cost(team1, team2, opp_counts, low, high)
    return cost


def improve_round_layout(tables, opp_counts_before_round, low, high):
    """
    Local search:
    For any two tables (A vs B) and (C vs D),
    try the two alternate pairings and keep improvements.
    """
    tables = tables[:]
    improved = True

    while improved:
        improved = False

        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                t1a, t1b = tables[i]
                t2a, t2b = tables[j]

                original = [tables[i], tables[j]]
                original_cost = round_cost(original, opp_counts_before_round, low, high)

                candidates = [
                    [(t1a, t2a), (t1b, t2b)],
                    [(t1a, t2b), (t1b, t2a)],
                ]

                best_local = original
                best_local_cost = original_cost

                for cand in candidates:
                    cand_cost = round_cost(cand, opp_counts_before_round, low, high)
                    if cand_cost < best_local_cost:
                        best_local = cand
                        best_local_cost = cand_cost

                if best_local_cost < original_cost:
                    tables[i], tables[j] = best_local[0], best_local[1]
                    improved = True

    return tables


# =========================================================
# Helpers: scoring / summaries
# =========================================================

def final_opponent_score(players, opp_counts, low, high, target):
    vals = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            vals.append(opp_counts[a][b])

    min_count = min(vals)
    max_count = max(vals)
    spread = max_count - min_count
    outside_band = sum(1 for v in vals if v < low or v > high)
    band_penalty = sum(edge_penalty(v, low, high) for v in vals)
    sse = sum((v - target) ** 2 for v in vals)

    return (outside_band, band_penalty, sse, spread, max_count, min_count)


def opponent_summary(players, schedule):
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


def opponent_balance_report(players, schedule):
    counts = opponent_summary(players, schedule)
    rows = []

    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            rows.append((a, b, counts[a][b]))

    return rows


def partner_summary(players, schedule):
    """
    Count partnerships using the partner pair list,
    including sit-out teams and not just played tables.
    """
    counts = {p: {q: 0 for q in players if q != p} for p in players}

    for rnd in schedule:
        for a, b in rnd["partner_pairs"]:
            counts[a][b] += 1
            counts[b][a] += 1

    return counts


# =========================================================
# Main schedule builder
# =========================================================

def build_schedule(players: list[str], attempts: int = 80, seed: int = 42) -> list[dict]:
    """
    Scalable schedule builder for larger tournaments.

    Hard rule:
      - each player partners every other player exactly once

    Soft rules:
      - opponent counts as even as possible
      - sit-outs as even as mathematically possible
    """
    partner_rounds = generate_partner_rounds(players)
    opp_low, opp_high, opp_target = opponent_low_high(players, partner_rounds)

    best_schedule = None
    best_score = None

    for attempt in range(attempts):
        rng = random.Random(seed + attempt)

        sit_targets, sit_low, sit_high, total_sit_slots = compute_sitout_targets(players, partner_rounds, rng)
        opp_counts = make_empty_opp_counts(players)
        sit_counts = {p: 0 for p in players}
        schedule = []

        for round_index, rnd in enumerate(partner_rounds, start=1):
            teams = [tuple(pair) for pair in rnd["pairs"]]
            bye = rnd["bye"]

            sit_out_players = []
            sit_out_team = None

            # mandatory single-player bye (only when odd number of players)
            if bye is not None:
                sit_out_players.append(bye)
                sit_counts[bye] += 1

            # if odd number of partner-teams, one full team must sit
            active_teams = teams[:]
            if len(active_teams) % 2 == 1:
                sit_out_team = choose_sitout_team(active_teams, sit_counts, sit_targets, rng)
                active_teams.remove(sit_out_team)

                for p in sit_out_team:
                    sit_out_players.append(p)
                    sit_counts[p] += 1

            # build tables
            tables = greedy_pair_tables(active_teams, opp_counts, opp_low, opp_high, rng)
            tables = improve_round_layout(tables, opp_counts, opp_low, opp_high)

            apply_tables_to_opp_counts(opp_counts, tables)

            round_data = {
                "round_number": round_index,
                "partner_pairs": [list(pair) for pair in teams],
                "bye": bye,
                "sit_out_team": list(sit_out_team) if sit_out_team is not None else [],
                "sit_out": sit_out_players,
                "tables": []
            }

            for table_num, (team1, team2) in enumerate(tables, start=1):
                round_data["tables"].append({
                    "table": table_num,
                    "team1": list(team1),
                    "team2": list(team2)
                })

            schedule.append(round_data)

        # final scoring
        opp_score = final_opponent_score(players, opp_counts, opp_low, opp_high, opp_target)
        sit_target_miss = sum(abs(sit_counts[p] - sit_targets[p]) for p in players)
        sit_vals = [sit_counts[p] for p in players]
        sit_spread = max(sit_vals) - min(sit_vals)

        # prioritize exact best-possible sit-out balance first
        score = (
            sit_target_miss,
            sit_spread,
            *opp_score
        )

        if best_score is None or score < best_score:
            best_score = score
            best_schedule = schedule

    return best_schedule


# =========================================================
# Session helpers
# =========================================================

def reset_tournament():
    st.session_state.players = []
    st.session_state.schedule = []
    st.session_state.current_round = 0
    st.session_state.generated = False
    st.session_state.error = ""


def generate_tournament(names_text):
    players = normalize_names(names_text)

    if len(players) < 4:
        st.session_state.error = "You need at least 4 players."
        return

    st.session_state.players = players
    st.session_state.schedule = build_schedule(players)
    st.session_state.current_round = 0
    st.session_state.generated = True
    st.session_state.error = ""


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
        opp_score = final_opponent_score(players, opp_counts, opp_low, opp_high, opp_target)

        sits = count_sitouts(schedule)
        sit_vals = [sits.get(p, 0) for p in players]
        total_sit_slots = sum(sit_vals)
        sit_low = total_sit_slots // len(players)
        sit_high = math.ceil(total_sit_slots / len(players))

        st.write(f"Ideal average opponent count per pair: {opp_target:.4f}")
        st.write(f"Desired opponent band: {opp_low} to {opp_high}")
        st.write(
            f"Pairs outside desired band: {opp_score[0]} | "
            f"Band penalty: {opp_score[1]:.2f} | "
            f"SSE from target: {opp_score[2]:.2f} | "
            f"Spread: {opp_score[3]} | "
            f"Max: {opp_score[4]} | Min: {opp_score[5]}"
        )

        st.markdown("**Sit-out balance**")
        st.write(
            f"Total sit-out slots: {total_sit_slots} | "
            f"Best possible sit-out range: {sit_low} to {sit_high}"
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
