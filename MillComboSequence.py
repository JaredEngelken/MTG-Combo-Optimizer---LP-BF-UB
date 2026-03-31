#######################
# Mill Combo Sequence #
# v1.03               #
# Jared Engelken      #
# Python 3.13.5       #
# 31.03.2026          #
#######################

from functools import lru_cache
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass(frozen=True)
class State:
    storm: int
    mana: int
    graveyard: int
    library: int
    starting_library: int
    opponents: Tuple[int, ...]  # cards remaining in each opponent's library
    lp_in_hand: bool
    bf_in_hand: bool
    jhoira: bool


def legal_actions(state: State):
    actions = []

    if state.lp_in_hand and (not state.jhoira or state.library >1):
        actions.append(("LP_HAND", None))

    # Escape Lotus Petal
    if state.graveyard >= 3 and (not state.jhoira or state.library >1):
        actions.append(("LP_ESCAPE", None))

    if state.bf_in_hand and state.mana >= 2 and state.library > 0:
        actions.append(("BF_SELF_HAND", None))

    # Escape Brain Freeze targeting self
    if state.mana >= 2 and state.graveyard >= 3 and state.library > 1:
        actions.append(("BF_SELF_ESCAPE", None))

    if state.bf_in_hand and state.mana >= 2 and state.library > 1:
        actions.append(("BF_OPP_HAND", None))

    # Escape Brain Freeze targeting each living opponent
    if state.mana >= 2 and state.graveyard >= 3:
        for i, cards in enumerate(state.opponents):
            if cards > 0:
                actions.append(("BF_OPP_ESCAPE", i))

    return actions


def apply_action(state: State, action):
    kind, target = action
    s = state.storm

    if kind == "LP_HAND":
        return State(
            storm = s + 1,
            mana = state.mana + 1,
            graveyard = state.graveyard,
            library = state.library - (1 if state.jhoira else 0),
            opponents = state.opponents,
            lp_in_hand = False,
            bf_in_hand = state.bf_in_hand,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )
    
    if kind == "LP_ESCAPE":
        return State(
            storm = s + 1,
            mana = state.mana + 1,
            graveyard = state.graveyard - 3,
            library = state.library - (1 if state.jhoira else 0),
            opponents = state.opponents,
            lp_in_hand = False,
            bf_in_hand = state.bf_in_hand,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )

    bf_mill = 3 * (s + 1)

    if kind == "BF_SELF_HAND":
        safe_self_mill = min(bf_mill, max(0, state.library - 1))
        spillover = bf_mill - safe_self_mill

        opps = list(state.opponents)

        for i in range(len(opps)):
            if spillover <= 0:
                break
            if opps[i] > 0:
                mill_amount = min(opps[i], spillover)
                opps[i] -= mill_amount
                spillover -= mill_amount

        return State(
            storm = s + 1,
            mana = state.mana - 2,
            graveyard = state.graveyard + safe_self_mill,
            library = state.library - safe_self_mill,
            opponents = tuple(opps),
            lp_in_hand = state.lp_in_hand,
            bf_in_hand = False,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )
    
    if kind == "BF_SELF_ESCAPE":
        safe_self_mill = min(bf_mill, max(0, state.library - 1))
        spillover = bf_mill - safe_self_mill

        opps = list(state.opponents)

        for i in range(len(opps)):
            if spillover <= 0:
                break
            if opps[i] > 0:
                mill_amount = min(opps[i], spillover)
                opps[i] -= mill_amount
                spillover -= mill_amount

        return State(
            storm = s + 1,
            mana = state.mana - 2,
            graveyard = state.graveyard - 3 + safe_self_mill,
            library = state.library - safe_self_mill,
            opponents = tuple(opps),
            lp_in_hand = state.lp_in_hand,
            bf_in_hand = False,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )

    elif kind == "BF_OPP_HAND":
        total_mill = 3 * (s + 1)
        opps = list(state.opponents)

        for i in range(len(opps)):
            if total_mill <= 0:
                break

            if opps[i] > 0:
                mill_amount = min(opps[i], total_mill)
                opps[i] -= mill_amount
                total_mill -= mill_amount

        return State(
            storm=s + 1,
            mana=state.mana - 2,
            graveyard=state.graveyard,
            library=state.library,
            opponents=tuple(opps),
            lp_in_hand = state.lp_in_hand,
            bf_in_hand = False,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )
    
    elif kind == "BF_OPP_ESCAPE":
        total_mill = 3 * (s + 1)
        opps = list(state.opponents)

        for i in range(len(opps)):
            if total_mill <= 0:
                break

            if opps[i] > 0:
                mill_amount = min(opps[i], total_mill)
                opps[i] -= mill_amount
                total_mill -= mill_amount

        return State(
            storm=s + 1,
            mana=state.mana - 2,
            graveyard=state.graveyard - 3,
            library=state.library,
            opponents=tuple(opps),
            lp_in_hand = state.lp_in_hand,
            bf_in_hand = False,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )
        

    raise ValueError("Unknown action")


def score(state: State):
    kills = sum(1 for x in state.opponents if x == 0)
    total_mill = sum(99 - x for x in state.opponents)
    library_used = state.starting_library - state.library
    return kills, total_mill, -library_used


@lru_cache(maxsize=None) # Store game states to prevent recalculation of same results
def search(state: State, depth_limit: int = 30):
    if depth_limit == 0:
        return score(state), []

    actions = legal_actions(state)
    if not actions:
        return score(state), []

    best_score = score(state)
    best_path: List[Tuple[str, Optional[int]]] = []

    for action in actions:
        next_state = apply_action(state, action)
        child_score, child_path = search(next_state, depth_limit - 1)

        if child_score > best_score:
            best_score = child_score
            best_path = [action] + child_path

    return best_score, best_path

def get_int(prompt, default):
    return int(input(prompt) or default)

def describe_action(kind, state):
    if kind in ("BF_SELF_HAND", "BF_SELF_ESCAPE"):
        bf_mill = 3 * (state.storm + 1)
        safe_self_mill = max(0, state.library - 1)

        if bf_mill > safe_self_mill:
            prefix = "Cast" if kind == "BF_SELF_HAND" else "Escape"
            return f"{prefix} Brain Freeze on yourself with extra copies against opponent(s)."

        return "Cast Brain Freeze on yourself." if kind == "BF_SELF_HAND" else "Escape Brain Freeze on yourself."

    elif kind == "BF_OPP_HAND":
        return "Cast Brain Freeze against opponent(s)."

    elif kind == "BF_OPP_ESCAPE":
        return "Escape Brain Freeze against opponent(s)."

    elif kind == "LP_HAND":
        return "Cast and crack Lotus Petal."

    else:
        return "Escape and crack Lotus Petal."
    
def print_compressed_sequence(initial_state, result_path):
    compressed = []
    current_state = initial_state

    for action in result_path:
        kind, _ = action
        label = describe_action(kind, current_state)

        if compressed and compressed[-1][0] == label:
            compressed[-1][1] += 1
        else:
            compressed.append([label, 1])

        current_state = apply_action(current_state, action)

    # Print nicely
    step = 1
    for label, count in compressed:
        if count == 1:
            print(f"{step}: {label}")
        else:
            print(f"{step}: {label} ×{count}")
        step += count

if __name__ == "__main__":
    
    opponents_number = get_int("How many opponents? ", 1)
    starting_library = get_int("Library size? ", 91)
    # Adjust these values
    initial_state = State(
        storm = get_int("What is the current storm count? ", 0),
        mana = get_int("How much mana do you have available? ", 0),
        graveyard = get_int("How many cards are in your graveyard? ", 0),   # enough fuel to start one escape
        starting_library = starting_library,
        library = starting_library,
        opponents = (99,)*opponents_number,
        lp_in_hand = True if input("Is Lotus Petal in your hand? ").lower() == "yes" else False,
        bf_in_hand = True if input("Is Brain Freeze in your hand? ").lower() == "yes" else False,
        jhoira = True if input("Is Jhoira in play? ").lower() == "yes" else False
    )

    result_score, result_path = search(initial_state, depth_limit=24)
    kills = result_score[0]
    total_opponents = len(initial_state.opponents)

    if kills == total_opponents:
        print("\nWinning line found.")
    else:
        print("\nNo full-table winning line found.")

    final_state = initial_state
    for action in result_path:
        final_state = apply_action(final_state, action)

    print("\nBest score (kills, total mill, efficiency):", result_score)
    print("Cards remaining in library:", final_state.library)
    print("Best sequence:")
    print_compressed_sequence(initial_state, result_path)
