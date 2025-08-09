# Pygame Chess (Human/AI per side)

- Toggle Human/AI per side during game.
- Realistic board colors and vector-drawn pieces with shading.
- AI uses alpha-beta with iterative deepening.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controls
- Left-click: select/move a piece
- R: reset
- U: undo last move
- A: toggle side to move is AI (quick)
- H: toggle White human/AI
- J: toggle Black human/AI
- +/-: change AI depth (or use number keys 1-5)
- ESC: quit

## Notes
- Uses `python-chess` for rules/legality.
- No external images required; pieces are drawn programmatically.