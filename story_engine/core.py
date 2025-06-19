from typing import Callable, Dict, List, Any, Optional, Tuple
import threading
import json
import time
from enum import Enum

# Типы стилей сообщений для UI
class MessageType(Enum):
    INFO = "info"
    IMPORTANT = "important"
    SOUND = "sound"
    ANIMATION = "animation"

# Эффекты с длительностью
class Effect:
    def __init__(self, name: str, duration: int, apply: Callable[["Story"], None], expire: Callable[["Story"], None] = None):
        self.name = name
        self.duration = duration
        self.apply = apply
        self.expire = expire

# Мини-головоломка
class Puzzle:
    def __init__(self, question: str, options: List[str], answer_index: int, on_success: Callable[["Story"], None] = None, on_fail: Callable[["Story"], None] = None):
        self.question = question
        self.options = options
        self.answer_index = answer_index
        self.on_success = on_success
        self.on_fail = on_fail

    def attempt(self, story: "Story", choice_index: int) -> bool:
        if choice_index == self.answer_index:
            if self.on_success:
                self.on_success(story)
            story.log.log(story, f"Puzzle solved: {self.question}", MessageType.INFO)
            return True
        else:
            if self.on_fail:
                self.on_fail(story)
            story.log.log(story, f"Puzzle failed: {self.question}", MessageType.INFO)
            return False

# NPC с диалогами
class NPC:
    def __init__(self, name: str, dialogue: Dict[str, Any]):
        self.name = name
        self.dialogue = dialogue
        self.dialogue_path: List[str] = []

    def talk(self, story: "Story", choice: Optional[str] = None) -> Dict:
        node = self._get_node()
        story.log.log(story, f"Talking to {self.name}: {node.get('text', '')}", MessageType.INFO)
        if choice:
            answers = node.get("responses", {})
            if choice in answers:
                self.dialogue_path = answers[choice].get("next", [])
                return self._get_node()
            else:
                return {"error": "Invalid choice."}
        return node

    def _get_node(self) -> Dict:
        node = self.dialogue
        for p in self.dialogue_path:
            node = node[p]
        return node

# Генерация карты истории
class StoryMap:
    def __init__(self):
        self.nodes: Dict[Tuple[str,...], Dict[str, Any]] = {}

    def register(self, path: List[str], node: Dict[str, Any]) -> None:
        self.nodes[tuple(path)] = node

    def generate_map(self) -> Dict[str, Any]:
        tree: Dict[str, Any] = {}
        for path in self.nodes:
            current = tree
            for step in path:
                current = current.setdefault(step, {})
        return tree

# Инвентарь
class Inventory:
    def __init__(self):
        self._items: Dict[str, List[Any]] = {slot: [] for slot in [
            "Head","Neck","Ears","Mouth","Right hand","Left hand","Back",
            "Right leg","Left leg","Right leg bottom","Left leg bottom"
        ]}

    def add_item(self, slot: str, item: str, description: str, function: Callable[["Story"], None]) -> None:
        self._items[slot] = [item, description, function]

    def remove_item(self, slot: str) -> None:
        self._items[slot] = []

    def get_items(self) -> Dict[str, List[Any]]:
        return {slot: data for slot, data in self._items.items() if data}

# Достижения
class Achievements:
    def __init__(self):
        self._achievements: Dict[str, str] = {}

    def add_achievement(self, name: str, description: str) -> None:
        self._achievements[name] = description

    def get_achievements(self) -> Dict[str, str]:
        return self._achievements

# Система здоровья
class HealthSystem:
    def __init__(self, initial_hp: int = 10):
        self._hp = initial_hp

    def modify_hp(self, amount: int) -> None:
        self._hp = max(0, self._hp + amount)

    def get_hp(self) -> int:
        return self._hp

# Журнал событий
class EventLog:
    def __init__(self):
        self.entries: List[Tuple[str, Optional[str]]] = []

    def log(self, story: "Story", message: str, style: Optional[str] = None) -> None:
        self.entries.append((message, style))
        story.print(message, style)

    def get_log(self) -> List[Tuple[str, Optional[str]]]:
        return self.entries

# Основной класс Story
class Story:
    def __init__(
        self,
        database: Dict[str, Any],
        values: Dict[str, bool] = None,
        tick_function: Callable[["Story"], None] = None,
        tick_interval: float = 5.0,
        auto_save: Optional[str] = None
    ):
        self._database = database
        self._flags = values or {}
        self._inventory = Inventory()
        self._achievements = Achievements()
        self._health = HealthSystem()
        self._log = EventLog()
        self._messages: List[Tuple[str, Optional[str]]] = []
        self.map = StoryMap()
        self.npcs: Dict[str, NPC] = {}
        self.effects: Dict[str, Effect] = {}
        self.current_puzzle: Optional[Puzzle] = None
        self.tick_function = tick_function
        self.tick_interval = tick_interval
        self.auto_save = auto_save
        self.path: List[str] = []
        self._stop = False
        self._tick_thread: Optional[threading.Thread] = None

        if tick_function:
            self._tick_thread = threading.Thread(target=self._run_tick, daemon=True)
            self._tick_thread.start()

    def _run_tick(self) -> None:
        while not self._stop:
            if self.tick_function:
                self.tick_function(self)
            self._update_effects()
            if self.auto_save:
                self.save_state(self.auto_save)
            time.sleep(self.tick_interval)

    def _update_effects(self) -> None:
        expired = []
        for name, effect in list(self.effects.items()):
            effect.duration -= 1
            if effect.duration <= 0:
                if effect.expire:
                    effect.expire(self)
                expired.append(name)
        for name in expired:
            del self.effects[name]

    def stop(self) -> None:
        self._stop = True
        if self._tick_thread:
            self._tick_thread.join()

    def jump_to(self, new_path: List[str]) -> None:
        self.path = new_path.copy()

    def step(self, answer: Optional[str] = None) -> Dict[str, Any]:
        node = self._get_node()
        if not node:
            return {"error": "Неверный путь."}
        if "function" in node and callable(node["function"]):
            node["function"](self)
        if answer is not None:
            answers = node.get("answers", {})
            if answer not in answers:
                return {"error": "Неверный выбор."}
            choice_data = answers[answer]
            if "function" in choice_data and callable(choice_data["function"]):
                choice_data["function"](self)
            next_path = choice_data.get("next_path")
            if next_path is not None:
                self.path = next_path.copy()
        return self._get_node()

    def _get_node(self) -> Dict[str, Any]:
        node = self._database
        try:
            for step in self.path:
                node = node[step]
            self.map.register(self.path.copy(), node)
            return node
        except KeyError:
            return {}

    def add_item(self, slot: str, item: str, description: str, function: Callable[["Story"], None]) -> None:
        self._inventory.add_item(slot, item, description, function)

    def remove_item(self, slot: str) -> None:
        self._inventory.remove_item(slot)

    def get_items(self) -> Dict[str, Dict[str, str]]:
        return {slot: {"name": data[0], "description": data[1]} for slot, data in self._inventory.get_items().items()}

    def set_flag(self, key: str, value: bool) -> None:
        self._flags[key] = value

    def get_flag(self, key: str) -> bool:
        return self._flags.get(key, False)

    def get_all_flags(self) -> Dict[str, bool]:
        return self._flags

    def modify_hp(self, amount: int) -> None:
        self._health.modify_hp(amount)

    def get_hp(self) -> int:
        return self._health.get_hp()

    def add_achievement(self, name: str, description: str) -> None:
        self._achievements.add_achievement(name, description)

    def get_achievements(self) -> Dict[str, str]:
        return self._achievements.get_achievements()

    def print(self, message: str, style: Optional[str] = None) -> None:
        self._messages.append((message, style))

    def clear_messages(self) -> None:
        self._messages.clear()

    def get_messages(self) -> List[Tuple[str, Optional[str]]]:
        return self._messages

    @property
    def log(self) -> EventLog:
        return self._log

    def apply_effect(self, effect: Effect) -> None:
        self.effects[effect.name] = effect
        effect.apply(self)

    def register_npc(self, npc: NPC) -> None:
        self.npcs[npc.name] = npc

    def talk_to(self, npc_name: str, choice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        npc = self.npcs.get(npc_name)
        if npc:
            return npc.talk(self, choice)

    def save_state(self, filename: str) -> None:
        state = {
            "hp": self._health.get_hp(),
            "inventory": {slot: data[:2] for slot, data in self._inventory.get_items().items()},
            "achievements": self._achievements.get_achievements(),
            "flags": self._flags,
            "path": self.path
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self, filename: str) -> None:
        with open(filename, "r", encoding="utf-8") as f:
            state = json.load(f)
        self._health = HealthSystem(state.get("hp", 0))
        self._achievements = Achievements()
        for ach, desc in state.get("achievements", {}).items():
            self._achievements.add_achievement(ach, desc)
        self._inventory = Inventory()
        for slot, data in state.get("inventory", {}).items():
            self._inventory.add_item(slot, data[0], data[1], lambda s: None)
        self._flags = state.get("flags", {})
        self.path = state.get("path", [])
