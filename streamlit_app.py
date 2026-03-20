import streamlit as st

st.set_page_config(page_title="Euchre Tournament", layout="wide")

st.title("Euchre Tournament Scheduler")

# Initialize state
if "players" not in st.session_state:
    st.session_state.players = []

if "schedule" not in st.session_state:
    st.session_state.schedule = []

if "current_round" not in st.session_state:
    st.session_state.current_round = 0

# Input area
st.subheader("Enter players")
names_text = st.text_area(
    "Paste one player name per line",
    height=200,
    placeholder="Alice\nBob\nCharlie\nDana"
)

def generate_placeholder_schedule(players):
    # fake example schedule just to prove the UI works
    return [
        {
            "round_name": "Round 1",
            "tables": [
                {"table": 1, "team1": ["Alice", "Bob"], "team2": ["Charlie", "Dana"]},
                {"table": 2, "team1": ["Eli", "Fran"], "team2": ["Gabe", "Holly"]},
            ],
            "sit_out": []
        },
        {
            "round_name": "Round 2",
            "tables": [
                {"table": 1, "team1": ["Alice", "Charlie"], "team2": ["Bob", "Dana"]},
                {"table": 2, "team1": ["Eli", "Gabe"], "team2": ["Fran", "Holly"]},
            ],
            "sit_out": []
        }
    ]

if st.button("Generate Tournament"):
    players = [name.strip() for name in names_text.splitlines() if name.strip()]
    st.session_state.players = players
    st.session_state.schedule = generate_placeholder_schedule(players)
    st.session_state.current_round = 0

# Display current round
if st.session_state.schedule:
    round_data = st.session_state.schedule[st.session_state.current_round]

    st.subheader(round_data["round_name"])

    cols = st.columns(len(round_data["tables"]))
    for col, table in zip(cols, round_data["tables"]):
        with col:
            st.markdown(f"### Table {table['table']}")
            st.write(f"**Team 1:** {table['team1'][0]} + {table['team1'][1]}")
            st.write(f"**Team 2:** {table['team2'][0]} + {table['team2'][1]}")

    if round_data["sit_out"]:
        st.warning("Sit out: " + ", ".join(round_data["sit_out"]))
    else:
        st.success("No sit-outs this round")

    left, middle, right = st.columns([1, 1, 1])

    with left:
        if st.button("Previous Round") and st.session_state.current_round > 0:
            st.session_state.current_round -= 1

    with right:
        if st.button("Next Round") and st.session_state.current_round < len(st.session_state.schedule) - 1:
            st.session_state.current_round += 1
