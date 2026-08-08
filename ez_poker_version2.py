import pygame
import random
import sys
from collections import Counter

# Initialize Pygame
pygame.init()
pygame.font.init()

# Display Config
WIDTH, HEIGHT = 1100, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("5-Card Draw Poker vs AI")
clock = pygame.time.Clock()

# Colors
DARK_GREEN = (18, 92, 49)
LIGHT_GREEN = (30, 130, 68)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (200, 40, 40)
BLUE = (40, 100, 220)
GOLD = (230, 180, 40)
GRAY = (120, 120, 120)
LIGHT_GRAY = (200, 200, 200)

# Fonts
FONT = pygame.font.SysFont("Arial", 18, bold=True)
BIG_FONT = pygame.font.SysFont("Arial", 28, bold=True)

# Card Data
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, start=2)}

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = RANK_VALUES[rank]
        self.selected = False

    def get_color(self):
        return RED if self.suit in ['♥', '♦'] else BLACK

class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def draw(self, count=1):
        drawn = []
        for _ in range(count):
            if self.cards:
                drawn.append(self.cards.pop())
        return drawn

# --- Hand Evaluator ---
def evaluate_hand(hand):
    values = sorted([c.value for c in hand], reverse=True)
    suits = [c.suit for c in hand]
    
    is_flush = len(set(suits)) == 1
    is_straight = len(set(values)) == 5 and (max(values) - min(values) == 4)
    
    if set(values) == {14, 5, 4, 3, 2}:
        is_straight = True
        values = [5, 4, 3, 2, 1]

    counts = Counter(values)
    freq_sorted = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    sorted_vals = [val for val, count in freq_sorted for _ in range(count)]

    if is_straight and is_flush:
        return (8, values)
    if freq_sorted[0][1] == 4:
        return (7, sorted_vals)
    if freq_sorted[0][1] == 3 and freq_sorted[1][1] == 2:
        return (6, sorted_vals)
    if is_flush:
        return (5, values)
    if is_straight:
        return (4, values)
    if freq_sorted[0][1] == 3:
        return (3, sorted_vals)
    if freq_sorted[0][1] == 2 and freq_sorted[1][1] == 2:
        return (2, sorted_vals)
    if freq_sorted[0][1] == 2:
        return (1, sorted_vals)
    return (0, values)

HAND_NAMES = {
    8: "Straight Flush", 7: "Four of a Kind", 6: "Full House",
    5: "Flush", 4: "Straight", 3: "Three of a Kind",
    2: "Two Pair", 1: "One Pair", 0: "High Card"
}

# --- Bot Model ---
class Bot:
    def __init__(self, bot_id):
        self.name = f"Bot {bot_id}"
        self.chips = 1000
        self.hand = []
        self.current_bet = 0
        self.folded = False

# --- Game Engine ---
class PokerGame:
    def __init__(self):
        self.player_chips = 1000
        self.num_bots = 2
        self.bots = [Bot(i + 1) for i in range(self.num_bots)]
        
        self.pot = 0
        self.highest_bet = 0
        self.player_bet = 0
        
        self.difficulty = "Medium"
        self.state = "DEAL"        # DEAL, BET1, DISCARD, BET2, SHOWDOWN, ROUND_OVER
        self.message = "Welcome! Choose bot count and click DEAL to start."
        
        self.deck = Deck()
        self.player_hand = []
        
        self.camera_shake_time = 0
        self.camera_shake_intensity = 0
        self.player_folded = False

    def trigger_shake(self, intensity=10, duration=15):
        self.camera_shake_intensity = intensity
        self.camera_shake_time = duration

    def set_bot_count(self, count):
        if self.state in ["DEAL", "SHOWDOWN", "ROUND_OVER"]:
            self.num_bots = count
            self.bots = [Bot(i + 1) for i in range(self.num_bots)]
            self.message = f"Set to {self.num_bots} AI Bot(s)."

    def recharge_chips(self):
        self.player_chips += 500
        self.message = "Recharged +$500 chips!"

    def start_new_round(self):
        if self.player_chips <= 0:
            self.message = "Out of chips! Click RECHARGE to continue."
            return

        self.deck = Deck()
        self.player_hand = self.deck.draw(5)
        
        # Reset cards selection state
        for card in self.player_hand:
            card.selected = False

        # Reset Bots & draw hands
        for bot in self.bots:
            bot.hand = self.deck.draw(5)
            bot.current_bet = 0
            bot.folded = False
            if bot.chips <= 0:
                bot.chips = 500

        # Ante $10
        ante = 10
        p_ante = min(self.player_chips, ante)
        self.player_chips -= p_ante
        self.pot = p_ante
        self.player_bet = p_ante

        for bot in self.bots:
            b_ante = min(bot.chips, ante)
            bot.chips -= b_ante
            bot.current_bet = b_ante
            self.pot += b_ante

        self.highest_bet = ante
        self.player_folded = False
        self.state = "BET1"
        self.message = "Round Started! $10 Antes placed."
        self.trigger_shake(6, 10)

    def process_bot_turns(self):
        actions = []
        bluff_chance = {"Easy": 0.05, "Medium": 0.15, "Hard": 0.30}[self.difficulty]

        for bot in self.bots:
            if bot.folded:
                continue

            call_needed = self.highest_bet - bot.current_bet
            score, _ = evaluate_hand(bot.hand)
            is_bluffing = random.random() < bluff_chance

            if call_needed == 0:
                if score >= 2 or (self.difficulty == "Hard" and score >= 1) or is_bluffing:
                    raise_amt = 20
                    if bot.chips >= raise_amt:
                        bot.chips -= raise_amt
                        bot.current_bet += raise_amt
                        self.highest_bet = bot.current_bet
                        self.pot += raise_amt
                        actions.append(f"{bot.name} Raised $20")
                        self.trigger_shake(10, 15)
                        continue
                actions.append(f"{bot.name} Checked")

            else:
                if call_needed > bot.chips:
                    call_needed = bot.chips

                if score >= 1 or is_bluffing or call_needed <= 20:
                    bot.chips -= call_needed
                    bot.current_bet += call_needed
                    self.pot += call_needed
                    actions.append(f"{bot.name} Called")
                else:
                    bot.folded = True
                    actions.append(f"{bot.name} Folded")

        active_bots = [b for b in self.bots if not b.folded]
        if not active_bots:
            self.state = "ROUND_OVER"
            self.player_chips += self.pot
            self.message = "All bots folded! You win the pot!"
        elif actions:
            self.message = " | ".join(actions)

    def bots_discard(self):
        for bot in self.bots:
            if bot.folded:
                continue
            vals = [c.value for c in bot.hand]
            counts = Counter(vals)
            score, _ = evaluate_hand(bot.hand)

            keep_indices = []
            if score >= 4:
                keep_indices = list(range(5))
            elif score in [1, 2, 3, 6, 7]:
                for i, c in enumerate(bot.hand):
                    if counts[c.value] >= 2:
                        keep_indices.append(i)
            else:
                sorted_indices = sorted(range(5), key=lambda i: bot.hand[i].value, reverse=True)
                num_keep = 2 if self.difficulty == "Hard" else 1
                keep_indices = sorted_indices[:num_keep]

            new_hand = []
            for i in range(5):
                if i in keep_indices:
                    new_hand.append(bot.hand[i])
                else:
                    drawn = self.deck.draw(1)
                    new_hand.append(drawn[0] if drawn else bot.hand[i])
            bot.hand = new_hand

    def resolve_showdown(self):
        self.state = "SHOWDOWN"
        contenders = []

        if not self.player_folded:
            p_score, p_vals = evaluate_hand(self.player_hand)
            contenders.append(("You", p_score, p_vals, "player"))

        for bot in self.bots:
            if not bot.folded:
                b_score, b_vals = evaluate_hand(bot.hand)
                contenders.append((bot.name, b_score, b_vals, bot))

        if not contenders:
            self.message = "Everyone folded!"
            return

        contenders.sort(key=lambda x: (x[1], x[2]), reverse=True)
        winner_name, win_score, _, winner_obj = contenders[0]

        desc = HAND_NAMES[win_score]
        if winner_obj == "player":
            self.player_chips += self.pot
            self.message = f"You Win ${self.pot} with {desc}!"
        else:
            winner_obj.chips += self.pot
            self.message = f"{winner_name} Wins ${self.pot} with {desc}!"

# --- UI Renderer ---
def draw_card(surface, card, x, y, face_up=True, small=False):
    w, h = (50, 75) if small else (65, 95)
    
    # Lift selected cards slightly up so it's obvious they are picked
    if card.selected and face_up and not small:
        y -= 15

    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, (0, 0, 0, 50), rect.move(2, 2), border_radius=5)
    
    if card.selected and face_up and not small:
        pygame.draw.rect(surface, GOLD, rect.inflate(8, 8), border_radius=7)

    if face_up:
        pygame.draw.rect(surface, WHITE, rect, border_radius=5)
        pygame.draw.rect(surface, GRAY, rect, 2, border_radius=5)
        
        color = card.get_color()
        font_c = pygame.font.SysFont("Arial", 14 if small else 18, bold=True)
        txt = font_c.render(f"{card.rank}{card.suit}", True, color)
        surface.blit(txt, (x + 3, y + 3))
    else:
        pygame.draw.rect(surface, BLUE, rect, border_radius=5)
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=5)

def draw_button(surface, text, x, y, w, h, bg_color=LIGHT_GRAY, text_color=BLACK):
    rect = pygame.Rect(x, y, w, h)
    mouse_pos = pygame.mouse.get_pos()
    
    color = bg_color
    if rect.collidepoint(mouse_pos):
        color = (min(bg_color[0]+30, 255), min(bg_color[1]+30, 255), min(bg_color[2]+30, 255))
        
    pygame.draw.rect(surface, color, rect, border_radius=6)
    pygame.draw.rect(surface, BLACK, rect, 2, border_radius=6)
    
    txt_surf = FONT.render(text, True, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)
    return rect

# --- Main Loop ---
def main():
    game = PokerGame()
    
    running = True
    while running:
        offset_x, offset_y = 0, 0
        if game.camera_shake_time > 0:
            game.camera_shake_time -= 1
            offset_x = random.randint(-game.camera_shake_intensity, game.camera_shake_intensity)
            offset_y = random.randint(-game.camera_shake_intensity, game.camera_shake_intensity)

        canvas = pygame.Surface((WIDTH, HEIGHT))
        canvas.fill(DARK_GREEN)

        # Poker Table
        pygame.draw.ellipse(canvas, LIGHT_GREEN, (100, 70, 900, 560))
        pygame.draw.ellipse(canvas, GOLD, (95, 65, 910, 570), 4)

        # Header Info
        canvas.blit(FONT.render(f"Your Chips: ${game.player_chips}", True, GOLD), (40, 20))
        pot_txt = BIG_FONT.render(f"POT: ${game.pot}", True, WHITE)
        canvas.blit(pot_txt, pot_txt.get_rect(center=(WIDTH // 2, 100)))

        # Dynamic Layout for Bots
        bot_positions = [
            [(WIDTH // 2 - 130, 140)],                             # 1 Bot
            [(220, 160), (WIDTH - 440, 160)],                      # 2 Bots
            [(200, 170), (WIDTH // 2 - 130, 130), (WIDTH - 420, 170)] # 3 Bots
        ][game.num_bots - 1]

        for idx, bot in enumerate(game.bots):
            bx, by = bot_positions[idx]
            status = "FOLDED" if bot.folded else f"${bot.chips}"
            name_txt = FONT.render(f"{bot.name} ({status})", True, WHITE if not bot.folded else GRAY)
            canvas.blit(name_txt, (bx, by - 25))

            for i, card in enumerate(bot.hand):
                show_cards = (game.state in ["SHOWDOWN", "ROUND_OVER"]) and not bot.folded
                draw_card(canvas, card, bx + i * 55, by, face_up=show_cards, small=True)

        # Player Cards
        px_start = WIDTH // 2 - 170
        for i, card in enumerate(game.player_hand):
            draw_card(canvas, card, px_start + i * 70, 460, face_up=not game.player_folded)

        if game.player_hand and not game.player_folded:
            p_score, _ = evaluate_hand(game.player_hand)
            canvas.blit(FONT.render(f"Hand: {HAND_NAMES[p_score]}", True, WHITE), (px_start, 565))

        # Banner Message
        msg_surf = FONT.render(game.message, True, GOLD)
        canvas.blit(msg_surf, msg_surf.get_rect(center=(WIDTH // 2, 380)))

        # Control Buttons
        btn_deal, btn_call, btn_raise, btn_fold, btn_discard = None, None, None, None, None
        btn_diff, btn_recharge, btn_bots = None, None, None

        btn_recharge = draw_button(canvas, "+ Recharge $500", 30, 680, 150, 40, GOLD, BLACK)
        btn_diff = draw_button(canvas, f"Diff: {game.difficulty}", 190, 680, 130, 40, LIGHT_GRAY, BLACK)
        btn_bots = draw_button(canvas, f"Bots: {game.num_bots}", 330, 680, 110, 40, LIGHT_GRAY, BLACK)

        if game.state in ["DEAL", "SHOWDOWN", "ROUND_OVER"]:
            label = "DEAL HAND ($10)" if game.state == "DEAL" else "NEXT ROUND ($10)"
            btn_deal = draw_button(canvas, label, 480, 680, 200, 40, BLUE, WHITE)

        elif game.state in ["BET1", "BET2"]:
            call_cost = game.highest_bet - game.player_bet
            call_label = "CHECK" if call_cost == 0 else f"CALL ${call_cost}"
            
            btn_call = draw_button(canvas, call_label, 470, 680, 120, 40, BLUE, WHITE)
            btn_raise = draw_button(canvas, "RAISE $20", 600, 680, 110, 40, GOLD, BLACK)
            btn_fold = draw_button(canvas, "FOLD", 720, 680, 90, 40, RED, WHITE)

        elif game.state == "DISCARD":
            btn_discard = draw_button(canvas, "DRAW / SWAP", 480, 680, 160, 40, BLUE, WHITE)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                mx -= offset_x
                my -= offset_y

                # Card Selection ONLY during DISCARD state
                if game.state == "DISCARD":
                    for i, card in enumerate(game.player_hand):
                        card_rect = pygame.Rect(px_start + i * 70, 460, 65, 95)
                        if card_rect.collidepoint((mx, my)):
                            card.selected = not card.selected

                # System Buttons
                if btn_recharge and btn_recharge.collidepoint((mx, my)):
                    game.recharge_chips()

                if btn_diff and btn_diff.collidepoint((mx, my)):
                    modes = ["Easy", "Medium", "Hard"]
                    game.difficulty = modes[(modes.index(game.difficulty) + 1) % len(modes)]

                if btn_bots and btn_bots.collidepoint((mx, my)):
                    new_count = (game.num_bots % 3) + 1
                    game.set_bot_count(new_count)

                # Game Phase Buttons
                if btn_deal and btn_deal.collidepoint((mx, my)):
                    game.start_new_round()

                elif game.state in ["BET1", "BET2"]:
                    if btn_call and btn_call.collidepoint((mx, my)):
                        call_amt = min(game.highest_bet - game.player_bet, game.player_chips)
                        game.player_chips -= call_amt
                        game.player_bet += call_amt
                        game.pot += call_amt
                        
                        game.process_bot_turns()
                        if game.state != "ROUND_OVER":
                            if game.state == "BET1":
                                game.state = "DISCARD"
                                game.message = "Click cards to swap, then click DRAW / SWAP!"
                            else:
                                game.resolve_showdown()

                    elif btn_raise and btn_raise.collidepoint((mx, my)):
                        call_amt = game.highest_bet - game.player_bet
                        total_needed = call_amt + 20
                        
                        if game.player_chips >= total_needed:
                            game.player_chips -= total_needed
                            game.player_bet += total_needed
                            game.highest_bet = game.player_bet
                            game.pot += total_needed
                            game.trigger_shake(12, 18)
                            
                            game.process_bot_turns()
                            if game.state != "ROUND_OVER":
                                if game.state == "BET1":
                                    game.state = "DISCARD"
                                    game.message = "Click cards to swap, then click DRAW / SWAP!"
                                else:
                                    game.resolve_showdown()

                    elif btn_fold and btn_fold.collidepoint((mx, my)):
                        game.player_folded = True
                        game.process_bot_turns()
                        if game.state != "ROUND_OVER":
                            game.resolve_showdown()

                elif btn_discard and btn_discard.collidepoint((mx, my)):
                    new_hand = []
                    swapped_count = 0
                    for card in game.player_hand:
                        if card.selected:
                            drawn = game.deck.draw(1)
                            if drawn:
                                new_hand.append(drawn[0])
                                swapped_count += 1
                            else:
                                new_hand.append(card)
                        else:
                            new_hand.append(card)
                    
                    game.player_hand = new_hand
                    game.bots_discard()  # AI discards cards as well
                    
                    game.state = "BET2"
                    game.message = f"Swapped {swapped_count} cards. Final betting round!"

        screen.fill(BLACK)
        screen.blit(canvas, (offset_x, offset_y))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()