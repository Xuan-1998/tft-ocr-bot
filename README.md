# Intelligent TFT Agent

An AI-powered Teamfight Tactics bot that learns and evolves through gameplay.

Built on top of [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT) with macOS support.

## Architecture

```
┌─────────────────────────────────────────┐
│              Game Interface              │
│  Screen Capture (mss) + Riot API        │
│  Mouse/Keyboard (pyautogui)             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│            Game State Engine             │
│  - Round, Gold, Level, HP (API)         │
│  - Shop champions (OCR)                 │
│  - Board state, Items                   │
│  - Phase detection (planning/combat)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Decision Engine                 │
│  Phase 1: Rule-based (current)          │
│  Phase 2: LLM-assisted (Gemma vision)   │
│  Phase 3: RL fine-tuned                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Memory & Evolution              │
│  - Game logs (JSONL)                    │
│  - Win/loss tracking                    │
│  - Decision replay buffer               │
│  - Self-improvement loop                │
└─────────────────────────────────────────┘
```

## Current Status (Set 17: Space Gods)

- ✅ macOS support (Quartz window detection, mss screen capture, pyautogui input)
- ✅ Riot Live Client API for gold/level/HP
- ✅ OCR shop reading with fuzzy champion matching
- ✅ Champion buying and board placement
- ✅ Econ strategy (save → rolldown at level 8)
- ✅ Cmd+= global hotkey to stop
- 🔧 Item building and placement (WIP)
- 🔧 God selection (Set 17 mechanic)
- 🔧 Loot pickup
- 🔧 LLM integration for decision making
- 🔧 Game memory and evolution

## Strategy: Mecha Fast 8

1. **Rounds 1-1 to 3-7**: Econ. Buy cheap frontline only. Save to 50+ gold.
2. **Round 4-1**: Level to 8, roll down for AurelionSol, TahmKench, Karma, Urgot, TheMightyMech.
3. **Late game**: Upgrade units, level to 9.

## Usage

```bash
cd ~/tft-ocr-bot-macos
source venv/bin/activate
python3 play_now.py    # Cmd+= to stop
```

## Requirements

- macOS with TFT installed (PBE or Live)
- Python 3.9+
- Tesseract OCR (`brew install tesseract`)
- Screen Recording + Accessibility permissions granted

## Credits

- Original OCR bot: [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT)
- macOS port + Set 17 + AI agent: [Xuan-1998](https://github.com/Xuan-1998)
