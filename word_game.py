# Word Connect - a 5x5 word-search game
#
# Double-click build_exe.bat to build a standalone Windows executable.
# The script prepares a local build environment and puts the .exe in dist\.
# PyInstaller command (when the script is named WordConnect.py):
#   pyinstaller --onefile --noconsole --icon=app_icon.ico WordConnect.py
# This project's script is named word_game.py; build_exe.bat includes the icon.
#
# The game uses Python's standard library, a local offline word list file, and
# bundled splash artwork. On Windows, winsound.Beep provides sound effects.

import random
import sys
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import winsound
except ImportError:
    winsound = None

BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_ICON_PATH = Path(__file__).resolve().with_name("app_icon.ico")
WORD_LIST_PATH = BUNDLE_DIR / "word_list.txt"
WORD_LIST = WORD_LIST_PATH.read_text(encoding="utf-8").strip() if WORD_LIST_PATH.exists() else ""
WORDS = frozenset(WORD_LIST.split())
VOWELS = "AEIOU"
CONSONANTS = "BCDFGHJKLMNPQRSTVWXYZ"
GRID_SIZE = 5
ROUND_SECONDS = 120
MIN_WORD_LENGTH = 3
MAX_WORD_LENGTH = 5


def _resource_path(relative_path):
    return BUNDLE_DIR / relative_path


def _generate_app_icon(icon_path):
    """Create a custom 256x256 app icon if the project icon is missing."""
    if icon_path.exists():
        return icon_path

    if Image is None or ImageDraw is None:
        raise RuntimeError(
            "Pillow is required to generate app_icon.ico. "
            "Install the project dependencies with 'pip install -r requirements.txt'."
        )

    size = 256
    image = Image.new("RGBA", (size, size), (15, 25, 35, 255))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((12, 12, size - 12, size - 12), radius=34, fill=(15, 25, 35, 255))
    draw.rounded_rectangle((44, 40, 212, 212), radius=46, fill=(34, 197, 94, 255))
    draw.rounded_rectangle((62, 58, 194, 194), radius=38, fill=(26, 160, 74, 255))

    highlight = (154, 255, 182, 80)
    draw.polygon(
        [(80, 82), (96, 52), (128, 124), (160, 52), (176, 82), (148, 82), (148, 184), (128, 162), (108, 184), (108, 82)],
        fill=highlight,
    )

    font = None
    for font_path in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ):
        try:
            font = ImageFont.truetype(font_path, 120)
            break
        except OSError:
            font = None

    if font is None:
        font = ImageFont.load_default()

    draw.text((128, 138), "W", font=font, fill=(10, 18, 22, 255), anchor="mm")

    image.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    return icon_path


def _ensure_app_icon():
    return _generate_app_icon(APP_ICON_PATH)


def _set_app_icon(root):
    _ensure_app_icon()
    try:
        root.iconbitmap(str(APP_ICON_PATH))
    except (OSError, tk.TclError, AttributeError):
        pass


def _neighbors(index):
    """Return the in-bounds eight-direction neighbors of a cell."""
    row, column = divmod(index, GRID_SIZE)
    result = []
    for row_delta in (-1, 0, 1):
        for column_delta in (-1, 0, 1):
            if row_delta == 0 and column_delta == 0:
                continue
            next_row = row + row_delta
            next_column = column + column_delta
            if 0 <= next_row < GRID_SIZE and 0 <= next_column < GRID_SIZE:
                result.append(next_row * GRID_SIZE + next_column)
    return result


def _path_for_word(word, board):
    """Find a non-repeating adjacent path whose cells fit the word."""
    visits = 0
    max_visits = 5000

    def search(position, offset, used):
        nonlocal visits
        visits += 1
        if visits > max_visits:
            return None
        if offset == len(word):
            return []

        choices = [
            cell for cell in _neighbors(position)
            if cell not in used and board[cell] in (None, word[offset])
        ]
        random.shuffle(choices)

        for cell in choices:
            rest = search(cell, offset + 1, used | {cell})
            if rest is not None:
                return [cell] + rest
        return None

    starts = list(range(GRID_SIZE * GRID_SIZE))
    random.shuffle(starts)

    for start in starts:
        if board[start] not in (None, word[0]):
            continue
        path = search(start, 1, {start})
        if path is not None:
            return [start] + path
    return None


def generate_grid():
    """Generate a balanced grid containing several guaranteed dictionary words."""
    candidates = [word.upper() for word in WORDS if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH]

    for _attempt in range(60):
        board = [None] * (GRID_SIZE * GRID_SIZE)
        hidden_words = random.sample(candidates, 5)
        placed_words = []

        for word in hidden_words:
            path = _path_for_word(word, board)
            if path is None:
                break
            for index, letter in zip(path, word):
                board[index] = letter
            placed_words.append(word)

        if len(placed_words) != len(hidden_words):
            continue

        vowel_count = sum(letter in VOWELS for letter in board if letter is not None)
        target_vowels = random.randint(9, 11)
        empty_cells = [i for i, letter in enumerate(board) if letter is None]
        extra_vowels = max(0, min(len(empty_cells), target_vowels - vowel_count))
        random.shuffle(empty_cells)
        vowel_cells = set(empty_cells[:extra_vowels])

        for index in empty_cells:
            if index in vowel_cells:
                board[index] = random.choice(VOWELS)
            else:
                board[index] = random.choice(CONSONANTS)

        return [board[i : i + GRID_SIZE] for i in range(0, len(board), GRID_SIZE)]

    board = [None] * (GRID_SIZE * GRID_SIZE)
    fallback_words = random.sample(
        [word.upper() for word in WORDS if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH],
        GRID_SIZE,
    )
    for row, word in enumerate(fallback_words):
        for column, letter in enumerate(word):
            board[row * GRID_SIZE + column] = letter

    vowel_count = sum(letter in VOWELS for letter in board if letter is not None)
    target_vowels = max(vowel_count, 10)
    empty_cells = [i for i, letter in enumerate(board) if letter is None]
    random.shuffle(empty_cells)
    vowel_cells = set(empty_cells[: min(len(empty_cells), target_vowels - vowel_count)])
    for index in empty_cells:
        board[index] = random.choice(VOWELS if index in vowel_cells else CONSONANTS)

    return [board[i : i + GRID_SIZE] for i in range(0, 25, GRID_SIZE)]


class SplashScreen(tk.Tk):
    """Show the bundled artwork briefly before opening the game."""

    def __init__(self):
        super().__init__()
        _set_app_icon(self)
        self.launch_game = False
        self.overrideredirect(True)
        self.configure(bg="#d9dddf")

        self.splash_image = tk.PhotoImage(file=str(_resource_path("assets/word_connect_splash.png")))
        width = self.splash_image.width()
        height = self.splash_image.height()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        tk.Label(self, image=self.splash_image, borderwidth=0).pack()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(2500, self._finish)

    def _finish(self):
        self.launch_game = True
        self.destroy()

    def _close(self):
        self.destroy()


class WordConnectApp(tk.Tk):
    """A timed, single-player word search with adjacent-letter selection."""

    BACKGROUND = "#101820"
    PANEL = "#1b2a36"
    TILE = "#263b4a"
    TILE_HOVER = "#344f60"
    TEXT = "#f4f7f9"
    MUTED = "#aab9c4"
    ACCENT = "#50d2aa"
    WARNING = "#ffbd69"
    GRID_SIZE = 5

    def __init__(self):
        super().__init__()
        _set_app_icon(self)
        self.title("Word Connect")
        self.configure(bg=self.BACKGROUND)
        self.resizable(False, False)

        self.grid_letters = []
        self.selected = []
        self.found_words = set()
        self.valid_words = set()
        self.score = 0
        self.high_score = 0
        self.seconds_left = ROUND_SECONDS
        self.game_active = True
        self.timer_job = None
        self.message_job = None
        self.hints_used = 0
        self.max_hints = 3

        self._build_ui()
        self.new_game()
        self._center_window()

    def _build_ui(self):
        container = tk.Frame(self, bg=self.BACKGROUND, padx=24, pady=20)
        container.pack()

        tk.Label(
            container,
            text="WORD CONNECT",
            bg=self.BACKGROUND,
            fg=self.TEXT,
            font=("Segoe UI", 24, "bold"),
        ).pack()
        tk.Label(
            container,
            text="Connect neighboring letters to discover words",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).pack(pady=(2, 14))

        stats = tk.Frame(container, bg=self.BACKGROUND)
        stats.pack(fill="x", pady=(0, 12))
        self.score_value = self._make_stat(stats, "SCORE", "0")
        self.words_value = self._make_stat(stats, "WORDS FOUND", "0")
        self.left_value = self._make_stat(stats, "WORDS LEFT", "0")
        self.high_score_value = self._make_stat(stats, "HIGH SCORE", "0")
        self.timer_value = self._make_stat(stats, "TIME LEFT", "02:00")

        body = tk.Frame(container, bg=self.BACKGROUND)
        body.pack()

        game_area = tk.Frame(body, bg=self.BACKGROUND)
        game_area.pack(side="left", padx=(0, 18))

        self.current_word = tk.Label(
            game_area,
            text="",
            bg=self.PANEL,
            fg=self.ACCENT,
            font=("Consolas", 20, "bold"),
            width=18,
            height=1,
            padx=10,
            pady=10,
        )
        self.current_word.pack(fill="x", pady=(0, 10))

        self.length_label = tk.Label(
            game_area,
            text="Word length: 0/5 (need 3-5)",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.length_label.pack(fill="x", pady=(0, 8))

        board_frame = tk.Frame(game_area, bg=self.BACKGROUND)
        board_frame.pack()
        self.letter_buttons = []
        button_font = tkfont.Font(family="Segoe UI", size=19, weight="bold")

        for row in range(self.GRID_SIZE):
            button_row = []
            for column in range(self.GRID_SIZE):
                index = row * self.GRID_SIZE + column
                button = tk.Button(
                    board_frame,
                    text="",
                    command=lambda i=index: self.select_letter(i),
                    width=3,
                    height=1,
                    bg=self.TILE,
                    fg=self.TEXT,
                    activebackground=self.TILE_HOVER,
                    activeforeground=self.TEXT,
                    disabledforeground=self.TEXT,
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    font=button_font,
                    highlightthickness=0,
                )
                button.grid(row=row, column=column, padx=4, pady=4, ipadx=2, ipady=5)
                button.bind("<Enter>", lambda _event, b=button, i=index: self._hover_tile(b, i, True))
                button.bind("<Leave>", lambda _event, b=button, i=index: self._hover_tile(b, i, False))
                button_row.append(button)
            self.letter_buttons.append(button_row)

        actions = tk.Frame(game_area, bg=self.BACKGROUND)
        actions.pack(fill="x", pady=(10, 0))

        self._button(actions, "Submit Word", self.submit_word, primary=True).pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._button(actions, "Clear Selection", self.clear_selection).pack(side="left", expand=True, fill="x", padx=(4, 0))
        self.hint_button = self._button(actions, "Hint", self.show_hint)
        self.hint_button.pack(side="left", expand=True, fill="x", padx=(4, 0))

        sidebar = tk.Frame(body, bg=self.PANEL, padx=12, pady=12)
        sidebar.pack(side="left", fill="y")

        tk.Label(
            sidebar,
            text="FOUND WORDS",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        list_frame = tk.Frame(sidebar, bg=self.PANEL)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.found_words_listbox = tk.Listbox(
            list_frame,
            width=18,
            height=16,
            bg="#14222d",
            fg=self.ACCENT,
            selectbackground=self.TILE_HOVER,
            selectforeground=self.TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            yscrollcommand=scrollbar.set,
        )
        self.found_words_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.found_words_listbox.yview)

        self._button(sidebar, "New Game / Shuffle Grid", self.new_game, primary=True).pack(fill="x", pady=(10, 0))

        self.status_label = tk.Label(
            container,
            text="",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(12, 0))

        tk.Label(
            container,
            text="Select 3 to 5 neighboring letters. Diagonal neighbors count; do not reuse a tile.",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(5, 0))

    def _make_stat(self, parent, title, value):
        card = tk.Frame(parent, bg=self.PANEL, padx=12, pady=8)
        card.pack(side="left", expand=True, fill="x", padx=3)

        tk.Label(
            card,
            text=title,
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack()

        value_label = tk.Label(
            card,
            text=value,
            bg=self.PANEL,
            fg=self.ACCENT if title != "TIME LEFT" else self.TEXT,
            font=("Segoe UI", 15, "bold"),
        )
        value_label.pack(pady=(2, 0))
        return value_label

    def _button(self, parent, text, command, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.ACCENT if primary else self.PANEL,
            fg="#10221d" if primary else self.TEXT,
            activebackground=self.TILE_HOVER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=9,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _hover_tile(self, button, index, hovering):
        if str(button["state"]) != tk.DISABLED and index not in self.selected:
            button.configure(bg=self.TILE_HOVER if hovering else self.TILE)

    def _sound(self, effect):
        if winsound is None:
            return
        tones = {
            "click": ((620, 45),),
            "success": ((660, 90), (784, 90), (988, 150)),
            "error": ((260, 160),),
        }
        try:
            for frequency, duration in tones[effect]:
                winsound.Beep(frequency, duration)
        except (RuntimeError, OSError):
            pass

    def _find_valid_words(self):
        board = [letter for row in self.grid_letters for letter in row]
        valid = set()
        playable_words = {word for word in WORDS if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH}
        word_prefixes = {
            word[:i]
            for word in playable_words
            for i in range(1, min(len(word), MAX_WORD_LENGTH) + 1)
        }

        def search(position, current, visited):
            if MIN_WORD_LENGTH <= len(current) <= MAX_WORD_LENGTH and current.lower() in playable_words:
                valid.add(current.lower())
            if len(current) >= MAX_WORD_LENGTH:
                return
            for neighbor in _neighbors(position):
                if neighbor in visited:
                    continue
                next_word = current + board[neighbor]
                if next_word.lower() not in word_prefixes:
                    continue
                search(neighbor, next_word, visited | {neighbor})

        for start in range(len(board)):
            search(start, board[start], {start})

        return valid

    def _update_word_counts(self):
        total = len(self.valid_words)
        found = len(self.found_words)
        left = max(0, total - found)
        self.words_value.configure(text=f"{found}/{total}")
        self.left_value.configure(text=str(left))

    def show_hint(self):
        if not self.game_active:
            return
        if self.hints_used >= self.max_hints:
            self._show_message("No hints left this round.", error=True)
            self._sound("error")
            return

        remaining = sorted(word for word in self.valid_words if word not in self.found_words)
        if not remaining:
            self._show_message("No more hidden words remain.", success=True)
            return

        hint_word = random.choice(remaining)
        hint_pattern = hint_word[0].upper() + " " + " ".join("_" for _ in hint_word[1:])
        self.hints_used += 1
        self.score = max(0, self.score - 10)
        self.high_score = max(self.high_score, self.score)
        self.score_value.configure(text=str(self.score))
        self.high_score_value.configure(text=str(self.high_score))

        self._show_message(
            f"Hint: {hint_pattern} ({len(hint_word)} letters, {len(remaining)} left)",
            success=True,
        )

        if self.hints_used >= self.max_hints:
            self.hint_button.configure(state=tk.DISABLED)

    def new_game(self):
        if self.timer_job is not None:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        if self.message_job is not None:
            self.after_cancel(self.message_job)
            self.message_job = None

        self.grid_letters = generate_grid()
        self.selected = []
        self.found_words = set()
        self.valid_words = self._find_valid_words()
        self.score = 0
        self.seconds_left = ROUND_SECONDS
        self.game_active = True
        self.hints_used = 0
        self.score_value.configure(text="0")
        self._update_word_counts()
        self.high_score_value.configure(text=str(self.high_score))
        self.found_words_listbox.delete(0, tk.END)
        self.status_label.configure(
            text=f"Find {MIN_WORD_LENGTH}-{MAX_WORD_LENGTH} letter words. {len(self.valid_words)} words available.",
            fg=self.MUTED,
        )
        if hasattr(self, "hint_button"):
            self.hint_button.configure(state=tk.NORMAL)

        for row in range(self.GRID_SIZE):
            for column in range(self.GRID_SIZE):
                self.letter_buttons[row][column].configure(
                    text=self.grid_letters[row][column],
                    bg=self.TILE,
                    fg=self.TEXT,
                    state=tk.NORMAL,
                )

        self._render_selection()
        self._update_timer()
        self.timer_job = self.after(1000, self._tick)

    def select_letter(self, index):
        if not self.game_active:
            return
        if self.selected and index == self.selected[-1]:
            self.selected.pop()
            self._render_selection()
            return
        if index in self.selected:
            self._show_message("A tile can only be used once.", error=True)
            self._sound("error")
            return
        if len(self.selected) >= MAX_WORD_LENGTH:
            self._show_message(f"Words can only be {MIN_WORD_LENGTH}-{MAX_WORD_LENGTH} letters.", error=True)
            self._sound("error")
            return
        if self.selected:
            last_row, last_col = divmod(self.selected[-1], self.GRID_SIZE)
            row, col = divmod(index, self.GRID_SIZE)
            row_step, col_step = row - last_row, col - last_col
            if max(abs(row_step), abs(col_step)) != 1:
                self._show_message("Choose a neighboring letter.", error=True)
                self._sound("error")
                return
        self.selected.append(index)
        self._render_selection()
        self._sound("click")

    def _render_selection(self):
        letters = []
        selected_set = set(self.selected)

        for index in self.selected:
            row, column = divmod(index, self.GRID_SIZE)
            letters.append(self.grid_letters[row][column])

        word_length = len(letters)
        self.current_word.configure(text="  ".join(letters))
        length_color = self.ACCENT if MIN_WORD_LENGTH <= word_length <= MAX_WORD_LENGTH else self.MUTED
        self.length_label.configure(
            text=f"Word length: {word_length}/{MAX_WORD_LENGTH} (need {MIN_WORD_LENGTH}-{MAX_WORD_LENGTH})",
            fg=length_color,
        )

        for index in range(self.GRID_SIZE * self.GRID_SIZE):
            row, column = divmod(index, self.GRID_SIZE)
            button = self.letter_buttons[row][column]
            if index in selected_set:
                button.configure(bg=self.ACCENT, fg="#10221d")
            else:
                button.configure(bg=self.TILE, fg=self.TEXT)

    def clear_selection(self):
        self.selected = []
        self._render_selection()

    def submit_word(self):
        if not self.game_active:
            return

        word = "".join(
            self.grid_letters[index // self.GRID_SIZE][index % self.GRID_SIZE]
            for index in self.selected
        ).lower()

        if word in self.found_words:
            self._sound("error")
            self._show_message("Already Found", error=True)
            self.clear_selection()
            return

        if not (MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH):
            self._sound("error")
            self._show_message(f"Word must be {MIN_WORD_LENGTH} to {MAX_WORD_LENGTH} letters.", error=True)
            self.clear_selection()
            return

        if word not in self.valid_words:
            self._sound("error")
            self._show_message("Invalid Word", error=True)
            self.clear_selection()
            return

        self.found_words.add(word)
        points = len(word) * 10
        self.score += points
        self.high_score = max(self.high_score, self.score)
        self.score_value.configure(text=str(self.score))
        self._update_word_counts()
        self.high_score_value.configure(text=str(self.high_score))
        self.found_words_listbox.insert(tk.END, f"• {word} ({len(word)})")
        self.found_words_listbox.see(tk.END)
        self._sound("success")
        self._show_message(f"Great word! +{points} points", success=True)
        self.clear_selection()

    def _show_message(self, message, error=False, success=False):
        if self.message_job is not None:
            self.after_cancel(self.message_job)
        color = self.WARNING if error else self.ACCENT if success else self.MUTED
        self.status_label.configure(text=message, fg=color)
        self.message_job = self.after(1600, self._restore_status)

    def _restore_status(self):
        self.message_job = None
        if self.game_active:
            left = max(0, len(self.valid_words) - len(self.found_words))
            self.status_label.configure(
                text=f"Find {MIN_WORD_LENGTH}-{MAX_WORD_LENGTH} letter words. {left} words left.",
                fg=self.MUTED,
            )

    def _update_timer(self):
        minutes, seconds = divmod(self.seconds_left, 60)
        self.timer_value.configure(text=f"{minutes:02d}:{seconds:02d}")
        self.timer_value.configure(fg=self.WARNING if self.seconds_left <= 15 else self.TEXT)

    def _tick(self):
        if not self.game_active:
            return
        self.seconds_left -= 1
        self._update_timer()
        if self.seconds_left <= 0:
            self._end_round()
            return
        self.timer_job = self.after(1000, self._tick)

    def _end_round(self):
        self.game_active = False
        self.timer_job = None
        self.seconds_left = 0
        self._update_timer()
        self.current_word.configure(text="")
        self.selected = []
        for row in self.letter_buttons:
            for button in row:
                button.configure(state=tk.DISABLED)
        self.status_label.configure(
            text=(
                f"Time's up! You found {len(self.found_words)}/{len(self.valid_words)} "
                f"word(s), {max(0, len(self.valid_words) - len(self.found_words))} left, score {self.score}."
            ),
            fg=self.ACCENT,
        )
        if hasattr(self, "hint_button"):
            self.hint_button.configure(state=tk.DISABLED)


if __name__ == "__main__":
    splash = SplashScreen()
    splash.mainloop()
    if splash.launch_game:
        WordConnectApp().mainloop()
