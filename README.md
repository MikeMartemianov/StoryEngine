
# story_engine

**story_engine** is a lightweight Python library for creating interactive text adventure games with a graphical interface based on [Textual](https://github.com/Textualize/textual). It supports inventory management, achievements, health system, and branching storylines with buttons for choices.

---

## Features

- Interactive branching stories with multiple choices
- Inventory system with equipment slots
- Achievements tracking
- Health system with hit points
- Threaded tick function for timed events
- Save and load game state (health, inventory, achievements)
- Stylish console UI with Rich and Textual widgets
- Message output buffer synchronized with UI
- Easy story database structure in Python dictionaries

---

## Installation

You need Python 3.8+ and the following packages:

```bash
pip install textual rich
```

Then you can include `story_engine.py` in your project or install it as a package.

---

## Usage

### Basic structure

Your story is represented as a nested dictionary with nodes. Each node can contain:

- `condition`: Text description of the current scene
- `answers`: Dictionary of answer text to next nodes
- `function`: Optional function to call when this node is entered

Example story snippet:

```python
story_data = {
    "start": {
        "condition": "You are in a dark forest. What do you do?",
        "answers": {
            "Go north": {
                "condition": "You see a mountain.",
                "answers": {}
            },
            "Go south": {
                "condition": "You encounter a river.",
                "answers": {}
            }
        }
    }
}
```

### Creating and running a story

```python
from story_engine import Story

# Your story data and initial path
story = Story(database=story_data, values={})
start_path = ["start"]

# Run the app
story.run(start_path)
```

### Inventory and achievements

You can add or remove inventory items and achievements dynamically:

```python
# Add an item to the "Right hand" slot
story.add_item("Right hand", "Sword", "A sharp blade", lambda: print("Swing sword"))

# Add an achievement
story.add_achievement("First Steps", "Started your adventure")

# Modify health
story.modify_hp(-2)
```

### Save and load game state

```python
story.save_state("savefile.json")
story.load_state("savefile.json")
```

---

## Advanced

- Use the optional `tick_function` parameter to add timed updates to your game logic (called every `tick_interval` seconds).
- Customize node functions to execute code on entering nodes.
- The UI displays current health, inventory, achievements, and story text with interactive buttons.

---

## License

MIT License
