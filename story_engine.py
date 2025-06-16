from typing import Callable, Dict, List
import threading
import json
import time
import re
import hashlib
from rich.console import Console
from textual.app import App, ComposeResult
from textual.widgets import Button, Static
from textual.containers import Vertical

class Inventory:
    def __init__(self):
        self._items: Dict[str, List] = {
            "Head": [], "Neck": [], "Ears": [], "Mouth": [],
            "Right hand": [], "Left hand": [], "Back": [],
            "Right leg": [], "Left leg": [],
            "Right leg bottom": [], "Left leg bottom": []
        }

    def add_item(self, slot: str, item: str, description: str, function: Callable) -> None:
        self._items[slot] = [item, description, function]

    def remove_item(self, slot: str) -> None:
        self._items[slot] = []

    def get_items(self) -> Dict[str, List]:
        return self._items

class Achievements:
    def __init__(self):
        self._achievements: Dict[str, str] = {}

    def add_achievement(self, achievement: str, description: str) -> None:
        self._achievements[achievement] = description

    def get_achievements(self) -> Dict[str, str]:
        return self._achievements

class HealthSystem:
    def __init__(self, initial_hp: int = 10):
        self._hp = initial_hp

    def modify_hp(self, amount: int) -> None:
        self._hp += amount
        if self._hp < 0:
            self._hp = 0

    def get_hp(self) -> int:
        return self._hp

class StoryApp(App):
    CSS = """
    Button {
        width: 100%;
        margin: 1;
        background: $primary;
        color: $text;
    }
    Static.condition {
        padding: 1;
        background: $panel;
        color: cyan;
    }
    Static.hp {
        padding: 1;
        background: $panel;
        color: red;
        border: round red;
        height: auto;
        margin-bottom: 1;
    }
    
    Static.achievements {
        padding: 1;
        background: $panel;
        color: green;
        border: round green;
        height: auto;
        margin-bottom: 1;
    }
    
    Static.inventory {
        padding: 1;
        background: $panel;
        color: yellow;
        border: round yellow;
        height: auto;
        margin-bottom: 1;
    }
    
    Static.condition {
        padding: 1;
        background: $panel;
        color: cyan;
        margin-bottom: 1;
    }
    
    Static.end {
        padding: 1;
        background: $panel;
        color: magenta;
        margin-top: 1;
    }
    Static.messages {
        padding: 1;
        background: $panel;
        color: white;
        border: round blue;
        height: 6;
        overflow: auto;
        margin-top: 1;
    }


    """

    def __init__(self, story, path: List[str]):
        super().__init__()
        self.story = story
        self.path = path
        self.current_node = self._get_node()

    def _get_node(self) -> Dict:
        node = self.story._database
        try:
            for p in self.path:
                node = node[p]
            return node
        except KeyError as e:
            self.story.print(f"Ошибка в пути сценария: {e}", style="bold red")
            return {}

    def _generate_button_id(self, answer: str) -> str:
        h = hashlib.md5(answer.encode("utf-8")).hexdigest()[:8]
        return f"btn_{h}"

    def _get_condition_text(self) -> str:
        return self.current_node.get("condition", "")

    def compose(self) -> ComposeResult:
        """Создание интерфейса пользователя."""
        # Получаем текущее здоровье, инвентарь, достижения
        hp = self.story.get_hp()
        items = self.story.get_items()
        achievements = self.story.get_achievements()

        # Показываем здоровье
        yield Static(f"[bold red]Здоровье:[/bold red] {hp}", classes="hp")

        # Показываем инвентарь (по слотам)
        if items:
            items_text = "\n".join(
                f"[bold blue]{slot}[/bold blue]: {item['name']} — {item['description']}"
                for slot, item in items.items()
            )
        else:
            items_text = "Инвентарь пуст."
        yield Static(f"[bold green]Инвентарь:[/bold green]\n{items_text}", classes="inventory")

        # Показываем достижения
        if achievements:
            achievements_text = "\n".join(
                f"🏆 [bold]{name}[/bold]: {desc}" for name, desc in achievements.items()
            )
        else:
            achievements_text = "Достижений пока нет."
        yield Static(f"[bold yellow]Достижения:[/bold yellow]\n{achievements_text}", classes="achievements")

        # Показываем условие (сцену)
        condition = self.current_node.get("condition", "Нет описания.")
        yield Static(f"[bold white]{condition}[/bold white]", classes="condition")

        # Показываем сообщения, созданные функциями (например, story.print(...))
        messages = self.story.get_messages()
        if messages:
            messages_text = "\n".join(f"[{style or 'white'}]{msg}[/{style or 'white'}]" for msg, style in messages)
        else:
            messages_text = "[dim]Нет сообщений.[/dim]"
        yield Static(messages_text, classes="messages")

        # Очищаем сообщения после отображения
        self.story.clear_messages()

        # Обработка кнопок-ответов
        answers = self.current_node.get("answers", {})
        if not answers:
            yield Static("\n[bold magenta]Дальше вариантов нет. Конец пути.[/bold magenta]", classes="end")
            return

        # Создаём кнопки
        buttons = [Button(label=answer, id=self._generate_button_id(answer)) for answer in answers]
        yield Vertical(*buttons)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        selected = None
        for ans in self.current_node.get("answers", {}):
            if self._generate_button_id(ans) == event.button.id:
                selected = ans
                break
        if selected is None:
            self.story.print("Такого варианта нет!", style="bold red")
            return

        self.story.print(f"Выбрано: {selected}", style="italic green")

        fn = self.current_node.get("function")
        if callable(fn):
            fn()

        self.path += ["answers", selected]
        self.current_node = self._get_node()
        await self._replace_compose()

    async def _replace_compose(self):
        for w in list(self.query()):
            await w.remove()
        for w in self.compose():
            await self.mount(w)

class Story:
    def __init__(self, database: Dict, values: Dict, tick_function: Callable = None, tick_interval: float = 5.0):
        self._console = Console(force_terminal=True)
        self._database = database
        self._values = values
        self._stop = False
        self._inventory = Inventory()
        self._achievements = Achievements()
        self._health = HealthSystem()
        self._output_lock = threading.Lock()
        self._tick_function = tick_function
        self._tick_interval = tick_interval
        self._tick_thread = None
        self._messages = []
        if tick_function:
            self._tick_thread = threading.Thread(target=self._run_tick, daemon=True)
            self._tick_thread.start()

    def _run_tick(self):
        while not self._stop:
            self._tick_function(self)
            time.sleep(self._tick_interval)

    def run(self, path: List[str]) -> None:
        app = StoryApp(self, path)
        app.run()

    def stop(self) -> None:
        self._stop = True
        if self._tick_thread:
            self._tick_thread.join()

    def modify_hp(self, amount: int) -> None:
        self._health.modify_hp(amount)

    def get_hp(self) -> int:
        return self._health.get_hp()

    def add_achievement(self, achievement: str, description: str) -> None:
        self._achievements.add_achievement(achievement, description)

    def get_achievements(self) -> Dict[str, str]:
        return self._achievements.get_achievements()

    def clear_messages(self) -> None:
        """Очищает буфер сообщений (например, после обновления UI)."""
        self._messages.clear()
    def get_messages(self) -> List[tuple]:
        """Возвращает список сообщений для отображения (текст, стиль)."""
        return self._messages
    def add_item(self, slot: str, item: str, description: str, function: Callable) -> None:
        self._inventory.add_item(slot, item, description, function)

    def remove_item(self, slot: str) -> None:
        self._inventory.remove_item(slot)

    def get_items(self):
        return {
            slot: {
                "name": items[0],
                "description": items[1]
            }
            for slot, items in self._inventory.get_items().items() if items  # ✅ добавил if items
        }

    def print(self, message: str, style: str = None) -> None:
        with self._output_lock:
            self._console.print(message, style=style)
            # Добавляем в буфер сообщений, чтобы UI мог показать
            self._messages.append((message, style))
    def save_state(self, filename: str) -> None:
        state = {
            "hp": self._health.get_hp(),
            "inventory": {slot: items[:2] for slot, items in self._inventory.get_items().items() if items},
            "achievements": self._achievements.get_achievements()
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self, filename: str) -> None:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._health = HealthSystem(state["hp"])
            self._achievements = Achievements()
            for ach, desc in state["achievements"].items():
                self._achievements.add_achievement(ach, desc)
            self._inventory = Inventory()
            for slot, item in state["inventory"].items():
                self._inventory.add_item(slot, item[0], item[1], lambda: None)
        except Exception as e:
            self.print(f"Ошибка загрузки состояния: {e}", style="bold red")
