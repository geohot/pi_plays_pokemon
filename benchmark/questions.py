"""The question each category asks, and how an answer is parsed and scored. One place, used by run.py and score.py."""
import json
import re
import unicodedata

SYSTEM = ("You are looking at one screenshot from the Game Boy game Pokemon Red. Answer the question about this exact "
          "screenshot from what is visible in it. Reply with only a JSON object of the form {\"answer\": ...}.")

PLACES = ["outdoors", "house", "lab", "pokemon_center", "poke_mart", "gym", "gate", "forest", "museum"]

QUESTIONS = {
    "text": ('Transcribe the text in the dialogue box at the bottom of the screen exactly as it is shown: both lines, '
             'in order, joined with a newline (\\n). Ignore the small blinking prompt arrow. {"answer": "..."}'),
    "cursor": ('A menu is open. Which entry is the filled triangle cursor (▶) pointing at? Give the entry text exactly '
               'as displayed. {"answer": "..."}'),
    "enemy_name": ('This is a battle. What is the name of the opposing Pokemon, as displayed at the top left of the '
                   'screen? {"answer": "NAME"}'),
    "enemy_level": ('This is a battle. What level is the opposing Pokemon (the one whose name is shown at the top '
                    'left)? {"answer": <number>}'),
    "player_hp": ("This is a battle. What are the player's Pokemon's current and maximum HP, as shown by the numbers "
                  'under its HP bar? {"answer": "current/max"}'),
    "enemy_hp_bar": ("This is a battle. How full is the opposing Pokemon's HP bar (top left)? Choose one of: "
                     '"full" (completely full), "more_than_half" (more than half but not full), '
                     '"less_than_half" (less than half but not empty), "empty" (nothing left). {"answer": "..."}'),
    "facing": ('The player character is the sprite in the middle of the screen. Which direction is the player facing? '
               'Choose one of "up", "down", "left", "right" (screen directions; "up" means toward the top of the '
               'screen, i.e. we see the back). {"answer": "..."}'),
    "npc_count": ('Not counting the player character in the middle of the screen, how many other characters (people or '
                  'Pokemon) are visible on the screen? {"answer": <number>}'),
    "walkable": ('The player character is the sprite in the middle of the screen. If the player pressed {dir} once, '
                 'would they move one tile {dir}? Answer false if a wall, object, sign, tree, fence, person, water, '
                 'ledge or the edge of the area blocks that step; true otherwise (also true if the step enters a door '
                 'or exit). {"answer": true or false}'),
    "place": ('What kind of place does this screenshot show? Choose one of: "outdoors" (a town or route), "house", '
              '"lab" (a Pokemon research lab), "pokemon_center", "poke_mart", "gym", "gate" (a gate building), '
              '"forest", "museum". {"answer": "..."}'),
}


def question(item):
    q = QUESTIONS[item["category"]]
    if item["category"] == "walkable":
        q = q.replace("{dir}", item["direction"])
    return q


def parse(text):
    """The model's answer: the 'answer' field of the last JSON object in the reply; else None (invalid)."""
    if not text:
        return None
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    t = t.replace("```json", "```").replace("```JSON", "```")
    found = None
    dec = json.JSONDecoder()
    i = 0
    while True:
        j = t.find("{", i)
        if j < 0:
            break
        try:
            obj, end = dec.raw_decode(t[j:])
            if isinstance(obj, dict) and "answer" in obj:
                found = obj["answer"]
            i = j + max(end, 1)
        except ValueError:
            i = j + 1
    return found


def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).replace("♂", "\x01").replace("♀", "\x02")
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))   # é è e: one letter
    s = s.replace("\x01", "♂").replace("\x02", "♀")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("…", "...")
    s = s.replace("▼", "").replace("\\n", " ")
    return " ".join(s.split()).upper()


def name_norm(s):
    s = norm(s).replace("(MALE)", "♂").replace("(FEMALE)", "♀")
    s = re.sub(r"\s*♂|\s+M$", "", s) if "♀" not in s else s
    return s.replace(" ", "")


def ints(v):
    return [int(x) for x in re.findall(r"\d+", str(v))]


def correct(item, ans):
    """True / False; None answers are wrong (and counted as invalid separately)."""
    if ans is None:
        return False
    cat, truth = item["category"], item["answer"]
    if cat == "text":
        return norm(ans) == norm(truth)
    if cat == "cursor":
        return norm(ans).replace(" ", "") == norm(truth).replace(" ", "")
    if cat == "enemy_name":
        return name_norm(ans) == name_norm(truth)
    if cat in ("enemy_level", "npc_count"):
        n = ints(ans)
        return len(n) == 1 and n[0] == int(truth)
    if cat == "player_hp":
        return ints(ans) == ints(truth)
    if cat == "walkable":
        if isinstance(ans, bool):
            return ans == truth
        a = norm(ans)
        return (a in ("TRUE", "YES")) == truth if a in ("TRUE", "YES", "FALSE", "NO") else False
    # one-of choices
    return norm(ans).replace(" ", "_").replace("POKEMON_CENTER", "POKEMON_CENTER") == norm(truth).replace(" ", "_")


def cer(a, b):
    """Character error rate of a vs truth b (Levenshtein / len(b)) on normalized text."""
    a, b = norm(a), norm(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(b))
