"""Wordle (Вордл) Mini-Game Engine for MOXXI Discord Bot.
Allows users to guess 5-letter Russian words with colored emojis:
🟩 - правильная буква на своём месте
🟨 - буква есть в слове, но на другой позиции
⬛ - такой буквы нет в слове
"""
import random
import time
from typing import Dict, List, Optional, Tuple
import disnake

# Список 5-буквенных слов (русский язык)
WORDLE_WORDS = [
    "поезд", "алмаз", "ветер", "замок", "магия", "земля", "огонь", "ларец",
    "птица", "город", "океан", "книга", "мышка", "волна", "рубин", "титан",
    "арена", "орден", "билет", "спорт", "лимон", "арбуз", "барон", "вирус",
    "герой", "дождь", "звено", "игрок", "канал", "лампа", "марка", "носок",
    "песок", "рыцарь", "сахар", "танец", "факел", "холод", "шторм", "экран",
    "юрист", "якорь", "вождь", "кубик", "монет", "корона", "шлем", "зелье",
    "дракон", "кубок", "сундук", "башня", "шахта", "топор", "копьё", "щит"
]

# Фильтруем ровно 5 букв
WORDS_5 = [w.lower() for w in WORDLE_WORDS if len(w) == 5]

# Активные сессии: user_id -> dict
# {"word": "поезд", "guesses": [("трава", "⬛🟨🟩⬛⬛")], "start_ts": time.time()}
active_sessions: Dict[int, dict] = {}


def start_wordle_session(user_id: int) -> dict:
    word = random.choice(WORDS_5)
    session = {
        "word": word,
        "guesses": [],
        "start_ts": time.time(),
        "won": False,
        "over": False,
    }
    active_sessions[user_id] = session
    return session


def get_wordle_session(user_id: int) -> Optional[dict]:
    s = active_sessions.get(user_id)
    if s:
        # Сессия сгорает через 1 час неактивности
        if time.time() - s.get("start_ts", 0) > 3600:
            del active_sessions[user_id]
            return None
    return s


def evaluate_guess(target: str, guess: str) -> Tuple[str, bool]:
    """Возвращает строку эмодзи (🟩🟨⬛) и флаг победы"""
    target = target.lower()
    guess = guess.lower()
    if target == guess:
        return "🟩 🟩 🟩 🟩 🟩", True

    res = ["⬛"] * 5
    target_chars = list(target)

    # 1. Сначала отмечаем точные совпадения (зелёные)
    for i in range(5):
        if guess[i] == target[i]:
            res[i] = "🟩"
            target_chars[i] = None

    # 2. Затем отмечаем совпадения не на месте (жёлтые)
    for i in range(5):
        if res[i] != "🟩" and guess[i] in target_chars:
            res[i] = "🟨"
            target_chars[target_chars.index(guess[i])] = None

    return " ".join(res), False


def render_board(session: dict) -> str:
    lines = []
    guesses = session.get("guesses", [])
    for idx in range(6):
        if idx < len(guesses):
            g_word, g_emojis = guesses[idx]
            letters_spaced = " ".join(list(g_word.upper()))
            lines.append(f"`{idx + 1}.` **{letters_spaced}**  —  {g_emojis}")
        else:
            lines.append(f"`{idx + 1}.` ▫️ ▫️ ▫️ ▫️ ▫️  —  ⬛ ⬛ ⬛ ⬛ ⬛")
    return "\n".join(lines)


def process_guess(user_id: int, guess: str) -> Tuple[disnake.Embed, bool, bool, int]:
    """Обрабатывает ход игрока.
    Возвращает: (embed, is_won, is_over, reward_coins)
    """
    guess = guess.strip().lower()
    session = get_wordle_session(user_id)
    if not session:
        session = start_wordle_session(user_id)

    if len(guess) != 5:
        embed = disnake.Embed(
            title="⚠️ Неверная длина слова",
            description=f"Слово должно состоять ровно из **5 букв**! Вы ввели: `{guess}` ({len(guess)} букв).\nПопробуйте ещё раз!",
            color=disnake.Color.orange()
        )
        return embed, False, False, 0

    target = session["word"]
    emojis, won = evaluate_guess(target, guess)
    session["guesses"].append((guess, emojis))

    attempts_used = len(session["guesses"])
    board_text = render_board(session)

    if won:
        session["won"] = True
        session["over"] = True
        reward = 500 if attempts_used <= 3 else 300
        embed = disnake.Embed(
            title="🎉 ВОРДЛ — ПОБЕДА!",
            description=(
                f"Вы угадали слово **{target.upper()}** за `{attempts_used}/6` попыток!\n\n"
                f"{board_text}\n\n"
                f"💰 **Награда:** `+{reward:,}` 🌑 монет и `+100 XP`!\n"
                f"Чтобы сыграть снова, напишите `/вордл`!"
            ),
            color=disnake.Color.green()
        )
        del active_sessions[user_id]
        return embed, True, True, reward

    if attempts_used >= 6:
        session["over"] = True
        embed = disnake.Embed(
            title="💔 ВОРДЛ — ИГРА ОКОНЧЕНА",
            description=(
                f"Попытки закончились! Загаданное слово было: **{target.upper()}**.\n\n"
                f"{board_text}\n\n"
                f"Не расстраивайтесь! Чтобы начать новую партию, напишите `/вордл`!"
            ),
            color=disnake.Color.red()
        )
        del active_sessions[user_id]
        return embed, False, True, 0

    # Игра продолжается
    embed = disnake.Embed(
        title=f"🟩 ВОРДЛ (Wordle) — Попытка {attempts_used}/6",
        description=(
            f"{board_text}\n\n"
            f"💡 **Подсказка:**\n"
            f"🟩 — буква на своём месте\n"
            f"🟨 — буква есть в слове, но на другой позиции\n"
            f"⬛ — буквы нет в слове\n\n"
            f"✍️ Введите следующую догадку через `/вордл [слово]` или `вордл [слово]`!"
        ),
        color=disnake.Color.blurple()
    )
    return embed, False, False, 0
