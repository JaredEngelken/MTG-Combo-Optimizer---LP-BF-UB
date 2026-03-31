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

    if state.lp_in_hand and (not state.jhoira or state.library >0):
        actions.append(("LP_HAND", None))

    # Escape Lotus Petal
    if state.graveyard >= 3 and (not state.jhoira or state.library >0):
        actions.append(("LP_ESCAPE", None))

    if state.bf_in_hand and state.mana >= 2 and state.library > 0:
        actions.append(("BF_SELF_HAND", None))

    # Escape Brain Freeze targeting self
    if state.mana >= 2 and state.graveyard >= 3 and state.library > 0:
        actions.append(("BF_SELF_ESCAPE", None))

    if state.bf_in_hand and state.mana >= 2:
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
        return State(
            storm = s + 1,
            mana = state.mana - 2,
            graveyard = state.graveyard + bf_mill,
            library = max(0, state.library - bf_mill),
            opponents = state.opponents,
            lp_in_hand = state.lp_in_hand,
            bf_in_hand = False,
            jhoira = state.jhoira,
            starting_library = state.starting_library
        )
    
    if kind == "BF_SELF_ESCAPE":
        return State(
            storm = s + 1,
            mana = state.mana - 2,
            graveyard = state.graveyard - 3 + bf_mill,
            library = max(0, state.library - bf_mill),
            opponents = state.opponents,
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
    # primary: opponents killed
    kills = sum(1 for x in state.opponents if x == 0)
    # secondary: total mill dealt
    total_mill = sum(99 - x for x in state.opponents)
    # tertiarry: total cards used from library
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

    final_state = initial_state
    for action in result_path:
        final_state = apply_action(final_state, action)

    print("\nBest score (kills, total mill, efficiency):", result_score)
    print("Library remaining:", final_state.library)
    print("Best sequence:")
    for step, action in enumerate(result_path, 1):
        kind, _ = action

        if kind == "BF_OPP_HAND":
            print(f"{step}: Cast Brain Freeze against opponent(s).")
        elif kind == "BF_OPP_ESCAPE":
            print(f"{step}: Escape Brain Freeze against opponent(s).")
        elif kind == "BF_SELF_HAND":
            print(f"{step}: Cast Brain Freeze on yourself.")
        elif kind == "BF_SELF_ESCAPE":
            print(f"{step}: Escape Brain Freeze on yourself.")
        elif kind == "LP_HAND":
            print(f"{step}: Cast and crack Lotus Petal.")
        else:
            print(f"{step}: Escape and crack Lotus Petal.")
