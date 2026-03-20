import streamlit as st
from itertools import combinations

st.set_page_config(page_title="Euchre Tournament Scheduler", layout="wide")

# =========================================================
# Helpers: scheduling
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


def generate_partner_rounds(players: list[str]) -> list[list[tuple[str, str]]]:
    """
    Create rounds of partner pairs using the circle method.
    Each player partners every other player exactly once.
    
    If odd number of players, add a BYE ghost; whoever is paired with BYE sits out.
    """
    arr = players[:]
    ghost = None

    if len(arr) % 2 == 1:
        ghost = "__BYE__"
        arr.append(ghost)

    n = len(arr)
    rounds = []

    # Circle method
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a = arr[i]
            b = arr[n - 1 - i]
            if ghost not in (a, b):
                pairs.append((a, b))
        rounds.append(pairs)

        # rotate all but first
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    return rounds


def score_team_pair(team_a, team_b, opp_counts):
    """
    Lower score is better.
    team_a = (p1, p2), team_b = (p3, p4)
    Counts how many times these players have already opposed each other.
    """
    a1, a2 = team_a
    b1, b2 = team_b
    return (
        opp_counts[a1][b1]
        + opp_counts[a1][b2]
        + opp_counts[a2][b1]
        + opp_counts[a2][b2]
    )


def all_table_pairings(teams):
    """
    Generate all possible ways to pair teams into tables.
    Returns a list of pairing layouts, where each layout is:
      [ (team1, team2), (team3, team4), ... ]
    If odd number of teams, one team must sit out, and all possibilities are considered.
    """
    if not teams:
        return [([], [])]  # (tables, sitting_out_teams)

    results = []

    # odd number of teams -> try each possible sit-out team
    if len(teams) % 2 == 1:
        for i in range(len(teams)):
            sit_out = [teams[i]]
            remaining = teams[:i] + teams[i+1:]
            for tables, _ in all_table_pairings(remaining):
                results.append((tables, sit_out))
        return results

    # even number of teams
    first = teams[0]
    for i in range(1, len(teams)):
        second = teams[i]
        remaining = teams[1:i] + teams[i+1:]
        for rest_tables, rest_sit_out in all_table_pairings(remaining):
            results.append(([(first, second)] + rest_tables, rest_sit_out))

    return results

def evaluate_round_layout(players, tables, opp_counts):
    """
    Simulate applying this round's tables and return a fairness score.
    Lower is better.
    """
    # copy current counts
    simulated = {
        p: opp_counts[p].copy()
        for p in players
    }

    # add this round's opponent matchups
    for team1, team2 in tables:
        a, b = team1
        c, d = team2

        for x in (a, b):
            for y in (c, d):
                simulated[x][y] += 1
                simulated[y][x] += 1

    # collect unique pair counts
    pair_counts = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            p1 = players[i]
            p2 = players[j]
            pair_counts.append(simulated[p1][p2])

    if not pair_counts:
        return 0

    max_count = max(pair_counts)
    min_count = min(pair_counts)
    spread = max_count - min_count
    sum_squares = sum(x * x for x in pair_counts)

    # weighted objective
    return max_count * 1000 + spread * 100 + sum_squares

def pair_teams_into_tables(teams, players, opp_counts):
    """
    Try all valid table layouts for this round and choose the one
    that best balances opponent counts.
    """
    all_layouts = all_table_pairings(teams)

    best_tables = None
    best_sit_out = None
    best_score = None

    for tables, sit_out_teams in all_layouts:
        score = evaluate_round_layout(players, tables, opp_counts)

        if best_score is None or score < best_score:
            best_score = score
            best_tables = tables
            best_sit_out = sit_out_teams

    return best_tables, best_sit_out

def build_schedule(players: list[str]) -> list[dict]:
    partner_rounds = generate_partner_rounds(players)

    opp_counts = {
        p: {q: 0 for q in players if q != p}
        for p in players
    }

    schedule = []

    for round_index, partner_pairs in enumerate(partner_rounds, start=1):
        teams = [tuple(pair) for pair in partner_pairs]

        tables, sitting_out_teams = pair_teams_into_tables(teams, players, opp_counts)

        # update opponent counts
        for team1, team2 in tables:
            a, b = team1
            c, d = team2
            for x in (a, b):
                for y in (c, d):
                    opp_counts[x][y] += 1
                    opp_counts[y][x] += 1

        sit_out_players = []
        for team in sitting_out_teams:
            sit_out_players.extend(team)

        players_used = set()
        for a, b in partner_pairs:
            players_used.add(a)
            players_used.add(b)

        single_sit_out = [p for p in players if p not in players_used]
        sit_out_players.extend(single_sit_out)

        round_data = {
            "round_number": round_index,
            "tables": [],
            "sit_out": sit_out_players
        }

        for table_num, (team1, team2) in enumerate(tables, start=1):
            round_data["tables"].append({
                "table": table_num,
                "team1": list(team1),
                "team2": list(team2)
            })

        schedule.append(round_data)

    return schedule

def partner_summary(players, schedule):
    """Count how many times each pair partnered."""
    counts = {p: {q: 0 for q in players if q != p} for p in players}

    for rnd in schedule:
        for t in rnd["tables"]:
            a, b = t["team1"]
            c, d = t["team2"]
            counts[a][b] += 1
            counts[b][a] += 1
            counts[c][d] += 1
            counts[d][c] += 1

    # Also include any sitting-out teams if they were a partner team sitting out
    # Not needed here because those teams are still represented in partner rounds before table grouping.
    return counts


def opponent_summary(players, schedule):
    """Count how many times each pair opposed one another."""
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


def reset_tournament():
    st.session_state.players = []
    st.session_state.schedule = []
    st.session_state.current_round = 0
    st.session_state.generated = False


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
Upload or paste player names, generate the tournament once, and then use the round buttons
to move through the schedule.
"""
)

with st.expander("Enter player names", expanded=not st.session_state.generated):
    default_text = ""
    names_text = st.text_area(
        "One player per line",
        value=default_text,
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

    top1, top2, top3 = st.columns([1, 1, 1])
    with top1:
        st.metric("Players", len(st.session_state.players))
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
        partner_counts = partner_summary(st.session_state.players, schedule)
        opp_counts = opponent_summary(st.session_state.players, schedule)

        st.markdown("**Opponent counts by pair**")
        rows = opponent_balance_report(st.session_state.players, schedule)
        for a, b, c in rows:
            st.write(f"{a} vs {b}: {c}")
    
        st.markdown("**Partner counts**")
        partner_issues = []
        for a, b in combinations(st.session_state.players, 2):
            if partner_counts[a][b] != 1:
                partner_issues.append(f"{a} & {b}: {partner_counts[a][b]}")

        if partner_issues:
            st.error("Some partner counts are not exactly 1:")
            for issue in partner_issues:
                st.write(issue)
        else:
            st.success("Every player partners every other player exactly once in the generated rounds shown at tables.")

        st.markdown("**Opponent balance snapshot**")
        flat_opp = []
        for a, b in combinations(st.session_state.players, 2):
            flat_opp.append(opp_counts[a][b])

        if flat_opp:
            st.write(
                f"Minimum times as opponents: {min(flat_opp)} | "
                f"Maximum times as opponents: {max(flat_opp)}"
            )
