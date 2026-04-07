"""
TFT Set 17 Bot v4 - Mecha Fast 8
Fixes: timing (only act in planning), god selection, loot pickup, item placement, F12 stop
"""
import time, json, sys, threading
import pyautogui
import comps, game_assets, arena_functions, mk_functions, screen_coords, ocr
from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
from difflib import SequenceMatcher
from pynput import keyboard

# --- F12 kill switch ---
BOT_RUNNING = True
def on_press(key):
    global BOT_RUNNING
    if key == keyboard.Key.f12:
        BOT_RUNNING = False
        print("\n🛑 F12 — stopping bot!\n")
        return False
kb_listener = keyboard.Listener(on_press=on_press)
kb_listener.daemon = True
kb_listener.start()

# --- Setup ---
w = find_league_window()
if not w:
    print("No game window! Start TFT first.")
    sys.exit(1)

x, y, width, height = w
y_off = y + round(height * 0.028)
eff_h = height - round(height * 0.028)
Vec4.setup_screen(x, y_off, width, eff_h)
Vec2.setup_screen(x, y_off, width, eff_h)

pyautogui.click(w[2]//2, w[3]//2)
time.sleep(0.3)

LOG = f"/tmp/tft_v4_{int(time.time())}.jsonl"
def log(t, **d):
    with open(LOG, "a") as f:
        f.write(json.dumps({"t": time.time(), "type": t, **d}) + "\n")

print("=== MECHA FAST 8 BOT v4 ===")
print("Press F12 to stop")
print(f"Log: {LOG}\n")

# --- State ---
phase = "ECON"
board_size = 0
last_round = ""
god_rounds_handled = set()
items_on_bench = []

# --- Helpers ---
def mouse_in_game():
    mx, my = pyautogui.position()
    return 0 <= mx <= width + 50 and 0 <= my <= height + 80

def fuzzy(raw):
    raw = raw.strip()
    if not raw or len(raw) < 2:
        return ""
    if raw in game_assets.CHAMPIONS:
        return raw
    best, best_r = "", 0
    for c in game_assets.CHAMPIONS:
        r = SequenceMatcher(a=c.lower(), b=raw.lower()).ratio()
        if r > best_r:
            best_r = r
            best = c
    return best if best_r >= 0.55 else ""

def get_round():
    """Read current round from screen"""
    import game_functions
    return game_functions.get_round()

def is_planning_phase():
    """Detect if we're in planning phase by checking if shop is visible.
    During combat, the shop area looks different."""
    # Simple heuristic: try to read a shop champion name
    # If we can read text, we're in planning phase
    try:
        shop_img = ocr._grab(screen_coords.SHOP_POS.get_coords())
        crop = shop_img.crop(screen_coords.CHAMP_NAME_POS[0].get_coords())
        text = ocr.get_text_from_image(crop).strip()
        return len(text) > 1  # If we can read a name, shop is visible = planning
    except:
        return False

def read_shop():
    shop_img = ocr._grab(screen_coords.SHOP_POS.get_coords())
    shop = []
    for idx, np in enumerate(screen_coords.CHAMP_NAME_POS):
        crop = shop_img.crop(np.get_coords())
        raw = ocr.get_text_from_image(crop).strip()
        shop.append((idx, fuzzy(raw)))
    return shop

def click_buy(slot):
    mk_functions.left_click(screen_coords.BUY_LOC[slot].get_coords())
    time.sleep(0.2)

def click_reroll():
    mk_functions.left_click(screen_coords.REFRESH_LOC.get_coords())
    time.sleep(0.35)

def click_buy_xp():
    mk_functions.left_click(screen_coords.BUY_XP_LOC.get_coords())
    time.sleep(0.15)

def buy_champs(targets):
    """Buy champions from shop that match target set. Returns list of bought names."""
    shop = read_shop()
    gold = arena_functions.get_gold()
    bought = []
    for slot, name in shop:
        if name and name in targets and gold >= game_assets.CHAMPIONS.get(name, {}).get("Gold", 99):
            click_buy(slot)
            bought.append(name)
            gold -= game_assets.CHAMPIONS[name]["Gold"]
    return bought

def place_all_bench():
    """Move bench units to board"""
    global board_size
    level = arena_functions.get_level()
    for i in range(9):
        if board_size >= level:
            break
        mk_functions.left_click(screen_coords.BENCH_LOC[i].get_coords())
        time.sleep(0.1)
        pos = 21 + (board_size % 7)
        mk_functions.left_click(screen_coords.BOARD_LOC[pos].get_coords())
        time.sleep(0.1)
        board_size += 1
    board_size = min(board_size, level)

def sell_bench():
    for i in range(9):
        mk_functions.press_e(screen_coords.BENCH_LOC[i].get_coords())
        time.sleep(0.05)

def pickup_loot():
    """Pick up items/loot from board"""
    print("  📦 Picking up loot")
    for idx, coords in enumerate(screen_coords.ITEM_PICKUP_LOC):
        mk_functions.right_click(coords.get_coords())
        time.sleep(0.6 if idx % 2 else 1.0)

def handle_god_selection():
    """At god rounds (2-4, 3-4, 4-4), click the left god blessing.
    The god selection screen shows two options side by side."""
    print("  ⚡ God selection — picking left blessing")
    time.sleep(2)
    # Left blessing is roughly at 35% of screen width, center height
    left_x = int(width * 0.35)
    left_y = int(y_off + eff_h * 0.45)
    pyautogui.click(left_x, left_y)
    time.sleep(1)
    # After god selection, Pengu drops rewards — click center to collect
    print("  🎁 Collecting Pengu rewards")
    time.sleep(2)
    center_x = width // 2
    center_y = int(y_off + eff_h * 0.5)
    pyautogui.click(center_x, center_y)
    time.sleep(1)
    pyautogui.click(center_x, center_y)
    time.sleep(0.5)

def place_items_on_carries():
    """Try to place items from item bench onto carry champions.
    Items sit on the left side, carries are on the board."""
    print("  🔧 Placing items on carries")
    # Item positions are on the left side of the board
    # Try dragging each item slot to the carry positions
    carry_positions = []
    for name, data in comps.COMP.items():
        if data.get("priority", 99) <= 2 and data.get("items"):
            carry_positions.append(data["board_position"])

    if not carry_positions:
        return

    for i, item_pos in enumerate(screen_coords.ITEM_POS[:6]):
        if not carry_positions:
            break
        # Pick up item
        item_coords = item_pos[0].get_coords()
        # Place on first carry
        target = carry_positions[i % len(carry_positions)]
        board_coords = screen_coords.BOARD_LOC[target].get_coords()

        mk_functions.left_click(item_coords)
        time.sleep(0.15)
        mk_functions.left_click(board_coords)
        time.sleep(0.15)

def pick_augment():
    """Pick first augment"""
    print("  🎯 Picking augment")
    time.sleep(1.5)
    mk_functions.left_click(screen_coords.AUGMENT_LOC[0].get_coords())
    time.sleep(1)

# --- God round set ---
GOD_ROUNDS = {"2-4", "3-4", "4-4"}
AUGMENT_ROUNDS = {"2-1", "3-2", "4-2"}
LOOT_ROUNDS = {"2-1", "3-1", "4-1", "5-1", "6-1", "7-1"}
ITEM_ROUNDS = {"2-2", "3-2", "4-2", "5-2", "6-2", "2-5", "3-5", "4-5", "5-5"}

# ============ MAIN LOOP ============
try:
    cycle = 0
    while BOT_RUNNING:
        # Mouse safety
        if not mouse_in_game():
            print("  ⏸ Mouse outside game — paused")
            while not mouse_in_game() and BOT_RUNNING:
                time.sleep(0.5)
            if not BOT_RUNNING:
                break
            pyautogui.click(w[2]//2, w[3]//2)
            time.sleep(0.3)
            print("  ▶ Resumed")

        gold = arena_functions.get_gold()
        level = arena_functions.get_level()
        health = arena_functions.get_health()
        current_round = get_round()

        # Track round changes
        round_changed = current_round != last_round and current_round in game_assets.ROUNDS
        if round_changed:
            last_round = current_round
            print(f"\n{'='*50}")
            print(f"[{phase}] Round {current_round} | Gold:{gold} Lvl:{level} HP:{health}")
            print(f"{'='*50}")
            log("round", round=current_round, gold=gold, level=level, health=health, phase=phase)

        if health <= 0:
            print("\n💀 GAME OVER")
            break

        # --- WAIT FOR PLANNING PHASE ---
        if not is_planning_phase():
            # We're in combat — do nothing, just wait
            time.sleep(1)
            cycle += 1
            continue

        # --- Handle special rounds ---
        if current_round in GOD_ROUNDS and current_round not in god_rounds_handled:
            handle_god_selection()
            god_rounds_handled.add(current_round)
            time.sleep(2)
            continue

        if round_changed and current_round in AUGMENT_ROUNDS:
            pick_augment()
            time.sleep(2)

        if round_changed and current_round in LOOT_ROUNDS:
            pickup_loot()

        if round_changed and current_round in ITEM_ROUNDS:
            place_items_on_carries()

        # --- PHASE TRANSITIONS ---
        # Switch to rolldown at 4-1 or when we have 50+ gold and level >= 5 and enough cycles
        if phase == "ECON" and ((current_round in game_assets.ROUNDS and current_round >= "4-1") or
                                (gold >= 50 and level >= 5 and cycle > 25) or health < 35):
            phase = "ROLLDOWN"
            print("\n>>> 🚀 ROLLDOWN PHASE <<<\n")

        if phase == "ROLLDOWN_DONE":
            phase = "LATEGAME"

        # ========== ECON PHASE ==========
        if phase == "ECON":
            # Only buy cheap frontline from natural shop (NO rerolling)
            bought = buy_champs(comps.EARLY_GAME_BUYS)
            if bought:
                print(f"    Bought: {bought}")
                place_all_bench()

            # Buy XP only if above 50 gold
            if gold > 54 and level < 5:
                click_buy_xp()

        # ========== ROLLDOWN PHASE ==========
        elif phase == "ROLLDOWN":
            # Level to 8
            while arena_functions.get_level() < 8 and arena_functions.get_gold() > 4:
                click_buy_xp()
            level = arena_functions.get_level()
            print(f"  Leveled to {level}")

            sell_bench()
            time.sleep(0.3)

            # Roll for core
            rolls = 0
            found = []
            all_targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
            while arena_functions.get_gold() > 10 and rolls < 30 and BOT_RUNNING:
                click_reroll()
                bought = buy_champs(all_targets)
                if bought:
                    found.extend(bought)
                    print(f"    Found: {bought}")
                rolls += 1

            place_all_bench()
            place_items_on_carries()
            print(f"  Rolled {rolls}x, found: {found}")
            log("rolldown", rolls=rolls, found=found)
            phase = "LATEGAME"
            print("\n>>> 🏆 LATEGAME PHASE <<<\n")

        # ========== LATEGAME PHASE ==========
        elif phase == "LATEGAME":
            if gold > 30:
                click_reroll()
                all_targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
                bought = buy_champs(all_targets)
                if bought:
                    print(f"    Upgrade: {bought}")
                    place_all_bench()

            if gold > 60 and level < 9:
                click_buy_xp()

        mk_functions.move_mouse(screen_coords.DEFAULT_LOC.get_coords())
        cycle += 1
        time.sleep(2)

except KeyboardInterrupt:
    print("\nBot stopped.")

print(f"Log: {LOG}")
