"""
TFT Set 17 Bot v3 - Mecha Fast 8
Phase 1 (1-1 to 3-7): Econ. Buy cheap frontline only. Save gold.
Phase 2 (4-1): Level to 8. Roll down for AurelionSol/TahmKench/Karma.
Phase 3 (4-1+): Fill board, place items, play for top 4.
"""
import time, json, sys, threading
import pyautogui
import comps, game_assets, arena_functions, mk_functions, screen_coords, ocr
from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
from difflib import SequenceMatcher
from pynput import keyboard

# --- Global kill switch: press F12 to stop ---
BOT_RUNNING = True
def on_press(key):
    global BOT_RUNNING
    if key == keyboard.Key.f12:
        BOT_RUNNING = False
        print("\n\n🛑 F12 pressed — stopping bot!\n")
        return False  # stop listener

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

LOG = f"/tmp/tft_mecha_{int(time.time())}.jsonl"
def log(t, **d):
    with open(LOG, "a") as f:
        f.write(json.dumps({"t": time.time(), "type": t, **d}) + "\n")

print(f"=== MECHA FAST 8 BOT ===")
print(f"Strategy: Econ to 3-7, level 8 at 4-1, roll for ASol/Tahm/Karma")
print(f"Press F12 at any time to stop the bot")
print(f"Log: {LOG}\n")

phase = "ECON"  # ECON -> ROLLDOWN -> LATEGAME
board_size = 0


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


def read_shop():
    img = ocr._grab(screen_coords.SHOP_POS.get_coords())
    shop = []
    for idx, np in enumerate(screen_coords.CHAMP_NAME_POS):
        crop = img.crop(np.get_coords())
        raw = ocr.get_text_from_image(crop).strip()
        shop.append((idx, fuzzy(raw)))
    return shop


def click_buy(slot):
    mk_functions.left_click(screen_coords.BUY_LOC[slot].get_coords())
    time.sleep(0.25)


def click_reroll():
    mk_functions.left_click(screen_coords.REFRESH_LOC.get_coords())
    time.sleep(0.4)


def click_buy_xp():
    mk_functions.left_click(screen_coords.BUY_XP_LOC.get_coords())
    time.sleep(0.2)


def place_all_bench():
    """Move all bench units to board"""
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
        time.sleep(0.06)


def pickup_loot():
    print("  Picking up loot")
    for idx, coords in enumerate(screen_coords.ITEM_PICKUP_LOC):
        mk_functions.right_click(coords.get_coords())
        time.sleep(0.8 if idx % 2 else 1.2)


def pick_augment():
    print("  Picking augment")
    time.sleep(1.5)
    # Just pick first augment for now
    mk_functions.left_click(screen_coords.AUGMENT_LOC[0].get_coords())
    time.sleep(1)


# ============ MAIN LOOP ============
try:
    cycle = 0
    while True:
        # F12 kill switch
        if not BOT_RUNNING:
            print("Bot stopped via F12.")
            break

        # Safety check
        if not mouse_in_game():
            print("  [PAUSED] Move mouse into game to resume...")
            while not mouse_in_game():
                time.sleep(0.5)
            pyautogui.click(w[2]//2, w[3]//2)
            time.sleep(0.3)
            print("  [RESUMED]")

        gold = arena_functions.get_gold()
        level = arena_functions.get_level()
        health = arena_functions.get_health()

        print(f"[{phase}] C{cycle} | Gold:{gold} Lvl:{level} HP:{health}")
        log("tick", gold=gold, level=level, health=health, phase=phase, cycle=cycle)

        if health <= 0:
            print("\n=== GAME OVER ===")
            log("gameover", cycle=cycle)
            break

        # ========== PHASE: ECON (1-1 to 3-7) ==========
        if phase == "ECON":
            # Buy only cheap frontline from natural shop (don't reroll)
            shop = read_shop()
            for slot, name in shop:
                if name in comps.EARLY_GAME_BUYS and gold >= game_assets.CHAMPIONS.get(name, {}).get("Gold", 99):
                    click_buy(slot)
                    print(f"    Early buy: {name}")
                    gold -= game_assets.CHAMPIONS[name]["Gold"]

            place_all_bench()

            # Level naturally — buy XP only if we have excess gold above 50
            if gold > 54 and level < 5:
                click_buy_xp()
                print(f"    Bought XP -> {arena_functions.get_level()}")

            # Transition to rolldown when we have enough gold and it's late enough
            # Heuristic: if gold > 50 and level >= 5, or if health is getting low
            if (gold >= 50 and level >= 5 and cycle > 20) or health < 40:
                phase = "ROLLDOWN"
                print("\n>>> TRANSITIONING TO ROLLDOWN <<<\n")

        # ========== PHASE: ROLLDOWN (4-1) ==========
        elif phase == "ROLLDOWN":
            # Step 1: Level to 8
            while arena_functions.get_level() < 8 and arena_functions.get_gold() > 4:
                click_buy_xp()
            level = arena_functions.get_level()
            print(f"  Leveled to {level}")

            # Step 2: Sell bench to make room
            sell_bench()
            time.sleep(0.3)

            # Step 3: Roll down for core units
            rolls = 0
            found = []
            while arena_functions.get_gold() > 10 and rolls < 30:
                click_reroll()
                shop = read_shop()
                for slot, name in shop:
                    if name in comps.ROLLDOWN_BUYS:
                        click_buy(slot)
                        found.append(name)
                        print(f"    FOUND: {name}")
                    elif name in comps.EARLY_GAME_BUYS and arena_functions.get_gold() > 20:
                        click_buy(slot)  # fill board
                rolls += 1

            print(f"  Rolled {rolls}x, found: {found}")
            place_all_bench()
            log("rolldown", rolls=rolls, found=found)
            phase = "LATEGAME"
            print("\n>>> ENTERING LATEGAME <<<\n")

        # ========== PHASE: LATEGAME ==========
        elif phase == "LATEGAME":
            # Keep rolling for upgrades when above 20 gold
            if gold > 30:
                click_reroll()
                shop = read_shop()
                for slot, name in shop:
                    if name in comps.ROLLDOWN_BUYS or name in comps.EARLY_GAME_BUYS:
                        if gold >= game_assets.CHAMPIONS.get(name, {}).get("Gold", 99):
                            click_buy(slot)
                            print(f"    Upgrade: {name}")
                            gold -= game_assets.CHAMPIONS[name]["Gold"]
                place_all_bench()

            # Level to 9 if rich
            if gold > 60 and level < 9:
                click_buy_xp()

        # Loot pickup every 12 cycles
        if cycle > 0 and cycle % 12 == 0:
            pickup_loot()

        # Augment check every 18 cycles
        if cycle > 0 and cycle % 18 == 0:
            pick_augment()

        mk_functions.move_mouse(screen_coords.DEFAULT_LOC.get_coords())
        cycle += 1
        time.sleep(3)

except KeyboardInterrupt:
    print("\nBot stopped.")

print(f"Log: {LOG}")
