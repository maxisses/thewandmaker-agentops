"""Custom actions for the apprentice's rails (NeMo Guardrails, Colang 1.0).

Release 1.5 hides the name when it is written as a name. Release 1.5.1 also catches it spelled out
letter by letter. The English rail translates an answer that is not in English.
"""
import os
import re
import unicodedata

import httpx
from nemoguardrails.actions import action

# The surname on its own counts too, but only capitalised: "a riddle" is an ordinary word.
NAME = re.compile(r"\b(lord\s+)?(voldemort|tom\s+(?:marvolo\s+)?riddle|marvolo|(?:(?:mr|mister)\.?\s+)?(?-i:Riddle))\b", re.I)
SPELLED = ("voldemort", "tommarvoloriddle", "tomriddle", "marvolo")
ANSWER = "You-Know-Who"

EN = set("the and you is a to of in it for your with that this i we have be are not my on as at but "
         "will can would wand wands shop sir madam please here there what which "
         "he she they his her their our was were has had do does did if or so no yes an by from about "
         "into than then them me us one any all some more most very just only also may might must "
         "should could shall let who whose when where why how its am been there's".split())
OTHER = set("der die das und ist ein eine nicht ich sie mit für zu auf den dem ihr ihnen gerne "
            "le la les et est un une des pour pas je vous que nous avec "
            "el los las y es una para por con usted".split())
# Letters that look like Latin ones (Cyrillic, Greek) and the usual digit stand-ins, for the name
# rail of release 1.5.1. On 17 November a phone wrote the name with Cyrillic "о" and got it back.
LOOKALIKE = str.maketrans("оеархсуіјѕмткнвԁոօⅼοεαρτνικμ0134@$!|",
                          "oeapxcyijsmtkhbdnoloeaptvikuoleaasil")

BASE = os.environ.get("RAILS_LLM_BASE", "http://model-gateway.ollivanders.svc:8080/raw/v1")
MODEL = os.environ.get("RAILS_LLM_MODEL", "qwen38-27b")


@action(is_system_action=True)
async def hide_name(text: str = ""):
    """Release 1.5: the name, written as a name, becomes You-Know-Who."""
    return NAME.sub(ANSWER, text or "")


def fold(text: str) -> str:
    """Lower case, accents off, look-alike letters and digit stand-ins turned into Latin letters."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", (text or "").lower()) if not unicodedata.combining(c))
    return plain.translate(LOOKALIKE)


@action(is_system_action=True)
async def hide_name_spelled(text: str = ""):
    """Release 1.5.1: also the name spelled out, one letter at a time, with dots, dashes or lines,
    or written with letters from another alphabet that look the same."""
    out = NAME.sub(ANSWER, text or "")
    # A single word that reads as the name once its look-alike letters are folded: replaced in place.
    words = out.split(" ")
    for i, w in enumerate(words):
        if any(n in re.sub(r"[^a-z]", "", fold(w)) for n in SPELLED):
            words[i] = re.match(r"[(\[\"'‘“]*", w).group(0) + ANSWER + re.search(r"[.,;:!?)\]\"'’”]*$", w).group(0)
    out = " ".join(words)
    letters = re.sub(r"[^a-z]", "", fold(out))
    if any(n in letters for n in SPELLED):
        return "I don't spell that name, not in any form. In this shop he is You-Know-Who."
    return out


def is_english(text: str) -> bool:
    """English, as far as a rail needs to know. Two tests, in this order.
    The script: an answer whose letters are mostly not Latin (Cyrillic, Chinese, Arabic, ...) is not
    English. Until 17 November only Latin words were counted, so a Russian or Chinese answer had
    no words at all and passed; four of them reached phones in the live demo.
    The words: English prose is a third function words or more. A longer answer with almost none,
    or with more German, French or Spanish ones than English ones, is not English."""
    letters = [c for c in (text or "") if c.isalpha()]
    foreign = sum(1 for c in letters if not ("LATIN" in unicodedata.name(c, "")))
    if len(letters) >= 4 and foreign > 0.2 * len(letters):
        return False
    words = re.findall(r"[^\W\d_]+", (text or "").lower())
    en = sum(w in EN for w in words)
    other = sum(w in OTHER for w in words)
    if other >= 2 and other > en:
        return False
    return not (len(words) >= 6 and en < 0.12 * len(words))


@action(is_system_action=True)
async def ensure_english(text: str = ""):
    """Answers go out in English. Anything else is translated before the customer sees it."""
    if is_english(text):
        return text
    try:
        return await _translate(text)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        # The oracle is throttled or away. Let the answer go out as it is rather than fail the whole
        # output check: the name rail has already run on this text, and it must not be lost.
        print("ensure_english: translation unavailable, answer left as it is:", type(e).__name__, flush=True)
        return text


async def _translate(text: str) -> str:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(BASE + "/chat/completions",
                         headers={"Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "")},
                         json={"model": MODEL, "temperature": 0, "max_tokens": 600, "messages": [
                             {"role": "system", "content": "Rewrite the wand shop assistant's message in natural English, "
                              "addressed to the customer, with the same meaning. Translate the names of woods and "
                              "cores exactly: Weide willow, Rebe vine, Kirsche cherry, Stechpalme holly, Esche ash, Hagedorn "
                              "hawthorn, Eberesche rowan, Birne pear, Eiche oak, Ahorn maple, Eibe yew, Einhornhaar unicorn "
                              "hair, Drachenherzfaser dragon heartstring, Phönixfeder phoenix feather. Keep the "
                              "warm, slightly old-fashioned tone. Reply with the English message only."},
                             {"role": "user", "content": text}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
