import pygame
import random
import sys
from collections import Counter

# Initialize Pygame
pygame.init()
pygame.font.init()

# Display Config
WIDTH, HEIGHT = 1024, 720
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
FONT = pygame.font.SysFont("Arial", 20, bold=True)
BIG_FONT = pygame.font.SysFont("Arial", 32, bold=True)

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
    """
    Returns a tuple (rank_score, tie_breaker_values)
    Scores:
    8: Straight Flush, 7: 4 of a Kind, 6: Full House, 5: Flush,
    4: Straight, 3: 3 of a Kind, 2: Two Pair, 1: One Pair, 0: High Card
    """
    values = sorted([c.value for c in hand], reverse=True)
    suits = [c.suit for c in hand]
    
    is_flush = len(set(suits)) == 1
    is_straight = len(set(values)) == 5 and (max(values) - min(values) == 4)
    
    # Wheel straight check A-2-3-4-5
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

# --- Game Engine ---
class PokerGame:
    def __init__(self):
        self.player_chips = 1000
        self.bot_chips = 1000
        self.pot = 0
        self.current_bet = 0
        self.player_bet = 0
        self.bot_bet = 0
        
        self.difficulty = "Medium"  # Easy, Medium, Hard
        self.state = "DEAL" # DEAL, BET1, DISCARD, BET2, SHOWDOWN, ROUND_OVER
        self.message = "Welcome! Click DEAL to start."
        
        self.deck = Deck()
        self.player_hand = []
        self.bot_hand = []
        
        self.camera_shake_time = 0
        self.camera_shake_intensity = 0
        self.bot_folded = False
        self.player_folded = False

    def trigger_shake(self, intensity=10, duration=15):
        self.camera_shake_intensity = intensity
        self.camera_shake_time = duration

    def recharge_chips(self):
        self.player_chips += 500
        self.message = "Recharged +$500!"

    def start_new_round(self):
        if self.player_chips <= 0:
            self.message = "Out of chips! Click RECHARGE to continue."
            return

        self.deck = Deck()
        
        # Rig deck slightly depending on bot difficulty
        if self.difficulty == "Easy" and random.random() < 0.6:
            # Player gets a better hand baseline on easy
            self.player_hand = self.deck.draw(5)
            self.bot_hand = self.deck.draw(5)
        elif self.difficulty == "Hard" and random.random() < 0.5:
            # Bot draws first with higher overall chance of good starting hand
            self.bot_hand = self.deck.draw(5)
            self.player_hand = self.deck.draw(5)
        else:
            self.player_hand = self.deck.draw(5)
            self.bot_hand = self.deck.draw(5)

        # Ante $10
        ante = 10
        p_ante = min(self.player_chips, ante)
        b_ante = min(self.bot_chips, ante)
        self.player_chips -= p_ante
        self.bot_chips -= b_ante
        self.pot = p_ante + b_ante
        self.player_bet = 0
        self.bot_bet = 0
        self.current_bet = 0
        
        self.bot_folded = False
        self.player_folded = False
        self.state = "BET1"
        self.message = "Round Started! Ante $10 placed."
        self.trigger_shake(6, 10)

    def bot_decision(self, is_second_bet=False):
        """ AI Logic for betting and bluffing """
        score, _ = evaluate_hand(self.bot_hand)
        bluff_roll = random.random()
        
        # Difficulty parameters
        bluff_chance = {"Easy": 0.05, "Medium": 0.15, "Hard": 0.30}[self.difficulty]
        folds_easily = self.difficulty == "Easy"
        
        call_amount = self.player_bet - self.bot_bet
        is_bluffing = bluff_roll < bluff_chance

        # If facing a call/check
        if call_amount == 0:
            if score >= 2 or (self.difficulty == "Hard" and score >= 1) or is_bluffing:
                raise_amt = 20 if is_bluffing else 20 * (score + 1)
                raise_amt = min(raise_amt, self.bot_chips)
                if raise_amt > 0:
                    self.bot_chips -= raise_amt
                    self.bot_bet += raise_amt
                    self.pot += raise_amt
                    self.current_bet = self.bot_bet
                    self.trigger_shake(12, 18)
                    return f"Bot raised ${raise_amt}" + (" (Bluffing!)" if is_bluffing and self.state == "SHOWDOWN" else "")
            return "Bot Checked"

        # Facing a raise
        if call_amount > 0:
            if call_amount > self.bot_chips:
                call_amount = self.bot_chips

            if is_bluffing and self.difficulty != "Easy":
                # Call or re-raise
                self.bot_chips -= call_amount
                self.bot_bet += call_amount
                self.pot += call_amount
                self.trigger_shake(8, 12)
                return "Bot Called your raise!"

            if score >= (1 if not folds_easily else 2) or call_amount <= 20:
                self.bot_chips -= call_amount
                self.bot_bet += call_amount
                self.pot += call_amount
                self.trigger_shake(8, 12)
                return "Bot Called"
            else:
                self.bot_folded = True
                self.state = "ROUND_OVER"
                self.player_chips += self.pot
                return "Bot Folded! You Win!"

    def bot_discard(self):
        """ AI Discard strategy based on hand evaluation """
        vals = [c.value for c in self.bot_hand]
        counts = Counter(vals)
        score, _ = evaluate_hand(self.bot_hand)

        keep_indices = []
        if score >= 4:  # Straight or better: keep all
            keep_indices = list(range(5))
        elif score in [1, 2, 3, 6, 7]:  # Pairs/Sets: keep matched rank cards
            for i, c in enumerate(self.bot_hand):
                if counts[c.value] >= 2:
                    keep_indices.append(i)
        else:
            # Keep highest card on Easy/Med, keep top 2 on Hard
            sorted_indices = sorted(range(5), key=lambda i: self.bot_hand[i].value, reverse=True)
            num_keep = 2 if self.difficulty == "Hard" else 1
            keep_indices = sorted_indices[:num_keep]

        # Draw replacement cards
        new_hand = []
        for i in range(5):
            if i in keep_indices:
                new_hand.append(self.bot_hand[i])
            else:
                drawn = self.deck.draw(1)
                if drawn:
                    new_hand.append(drawn[0])
                else:
                    new_hand.append(self.bot_hand[i])
        self.bot_hand = new_hand

    def resolve_showdown(self):
        self.state = "SHOWDOWN"
        p_score, p_vals = evaluate_hand(self.player_hand)
        b_score, b_vals = evaluate_hand(self.bot_hand)

        p_desc = HAND_NAMES[p_score]
        b_desc = HAND_NAMES[b_score]

        if (p_score, p_vals) > (b_score, b_vals):
            self.player_chips += self.pot
            self.message = f"You Win ${self.pot}! ({p_desc} vs {b_desc})"
        elif (b_score, b_vals) > (p_score, p_vals):
            self.bot_chips += self.pot
            self.message = f"Bot Wins ${self.pot}! ({b_desc} vs {p_desc})"
        else:
            split = self.pot // 2
            self.player_chips += split
            self.bot_chips += split
            self.message = f"Split Pot! Both had {p_desc}"

# --- UI Renderer ---
def draw_card(surface, card, x, y, face_up=True):
    rect = pygame.Rect(x, y, 70, 100)
    
    # Shadow
    pygame.draw.rect(surface, (0, 0, 0, 50), rect.move(3, 3), border_radius=6)
    
    if card.selected and face_up:
        pygame.draw.rect(surface, GOLD, rect.inflate(8, 8), border_radius=8)

    if face_up:
        pygame.draw.rect(surface, WHITE, rect, border_radius=6)
        pygame.draw.rect(surface, GRAY, rect, 2, border_radius=6)
        
        color = card.get_color()
        # Rank & Suit top-left
        txt = FONT.render(f"{card.rank}{card.suit}", True, color)
        surface.blit(txt, (x + 5, y + 5))
        
        # Big Suit Center
        big_txt = BIG_FONT.render(card.suit, True, color)
        surface.blit(big_txt, (x + 22, y + 35))
    else:
        # Card Back
        pygame.draw.rect(surface, BLUE, rect, border_radius=6)
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=6)
        pygame.draw.rect(surface, (20, 60, 160), rect.inflate(-12, -12), border_radius=4)

def draw_button(surface, text, x, y, w, h, bg_color=LIGHT_GRAY, text_color=BLACK):
    rect = pygame.Rect(x, y, w, h)
    mouse_pos = pygame.mouse.get_pos()
    
    color = bg_color
    if rect.collidepoint(mouse_pos):
        color = (min(bg_color[0]+30, 255), min(bg_color[1]+30, 255), min(bg_color[2]+30, 255))
        
    pygame.draw.rect(surface, color, rect, border_radius=8)
    pygame.draw.rect(surface, BLACK, rect, 2, border_radius=8)
    
    txt_surf = FONT.render(text, True, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)
    return rect

# --- Main Game Loop ---
def main():
    game = PokerGame()
    
    running = True
    while running:
        # Screen Shake calculation
        offset_x, offset_y = 0, 0
        if game.camera_shake_time > 0:
            game.camera_shake_time -= 1
            offset_x = random.randint(-game.camera_shake_intensity, game.camera_shake_intensity)
            offset_y = random.randint(-game.camera_shake_intensity, game.camera_shake_intensity)

        # Offscreen canvas for shaking
        canvas = pygame.Surface((WIDTH, HEIGHT))
        canvas.fill(DARK_GREEN)

        # Table decorative circle
        pygame.draw.ellipse(canvas, LIGHT_GREEN, (100, 80, 824, 520))
        pygame.draw.ellipse(canvas, GOLD, (95, 75, 834, 530), 4)

        # UI Header (Chips & Pot)
        canvas.blit(FONT.render(f"Your Chips: ${game.player_chips}", True, GOLD), (40, 20))
        canvas.blit(FONT.render(f"Bot Chips: ${game.bot_chips}", True, GOLD), (WIDTH - 200, 20))
        
        pot_txt = BIG_FONT.render(f"POT: ${game.pot}", True, WHITE)
        canvas.blit(pot_txt, pot_txt.get_rect(center=(WIDTH // 2, 120)))

        # Difficulty Display
        diff_txt = FONT.render(f"Difficulty: {game.difficulty}", True, WHITE)
        canvas.blit(diff_txt, (40, 50))

        # Render Bot Hand
        for i, card in enumerate(game.bot_hand):
            show_cards = (game.state in ["SHOWDOWN", "ROUND_OVER"]) and not game.bot_folded
            draw_card(canvas, card, 330 + i * 75, 160, face_up=show_cards)

        # Render Player Hand
        for i, card in enumerate(game.player_hand):
            draw_card(canvas, card, 330 + i * 75, 420, face_up=not game.player_folded)

        # Show Player Hand Rank Name
        if game.player_hand and not game.player_folded:
            p_score, _ = evaluate_hand(game.player_hand)
            p_desc_txt = FONT.render(f"Hand: {HAND_NAMES[p_score]}", True, WHITE)
            canvas.blit(p_desc_txt, (330, 535))

        # Banner Message
        msg_surf = FONT.render(game.message, True, GOLD)
        canvas.blit(msg_surf, msg_surf.get_rect(center=(WIDTH // 2, 360)))

        # --- Interactive Buttons ---
        btn_deal, btn_call, btn_raise, btn_fold, btn_discard = None, None, None, None, None
        btn_diff, btn_recharge = None, None

        # Recharge and Difficulty are always available
        btn_recharge = draw_button(canvas, "+ Recharge $500", 40, 640, 160, 45, GOLD, BLACK)
        btn_diff = draw_button(canvas, f"Diff: {game.difficulty}", 210, 640, 140, 45, LIGHT_GRAY, BLACK)

        if game.state in ["DEAL", "ROUND_OVER"]:
            btn_deal = draw_button(canvas, "DEAL HAND ($10)", 400, 640, 220, 45, BLUE, WHITE)

        elif game.state in ["BET1", "BET2"]:
            call_cost = game.bot_bet - game.player_bet
            call_label = "CHECK" if call_cost == 0 else f"CALL ${call_cost}"
            
            btn_call = draw_button(canvas, call_label, 380, 640, 120, 45, BLUE, WHITE)
            btn_raise = draw_button(canvas, "RAISE $20", 510, 640, 120, 45, GOLD, BLACK)
            btn_fold = draw_button(canvas, "FOLD", 640, 640, 100, 45, RED, WHITE)

        elif game.state == "DISCARD":
            btn_discard = draw_button(canvas, "DRAW / SWAP", 420, 640, 180, 45, BLUE, WHITE)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Adjust mouse for camera shake
                mx -= offset_x
                my -= offset_y

                # Card Selection for Discarding Phase
                if game.state == "DISCARD":
                    for i, card in enumerate(game.player_hand):
                        card_rect = pygame.Rect(330 + i * 75, 420, 70, 100)
                        if card_rect.collidepoint((mx, my)):
                            card.selected = not card.selected

                # Button Clicks
                if btn_recharge and btn_recharge.collidepoint((mx, my)):
                    game.recharge_chips()

                if btn_diff and btn_diff.collidepoint((mx, my)):
                    modes = ["Easy", "Medium", "Hard"]
                    game.difficulty = modes[(modes.index(game.difficulty) + 1) % len(modes)]

                if btn_deal and btn_deal.collidepoint((mx, my)):
                    game.start_new_round()

                elif game.state in ["BET1", "BET2"]:
                    if btn_call and btn_call.collidepoint((mx, my)):
                        call_amt = game.bot_bet - game.player_bet
                        call_amt = min(call_amt, game.player_chips)
                        game.player_chips -= call_amt
                        game.player_bet += call_amt
                        game.pot += call_amt
                        if call_amt > 0:
                            game.trigger_shake(6, 10)

                        if game.state == "BET1":
                            bot_msg = game.bot_decision(is_second_bet=False)
                            if not game.bot_folded:
                                game.state = "DISCARD"
                                game.message = f"{bot_msg}. Select cards to swap & click DRAW."
                        else:  # BET2
                            bot_msg = game.bot_decision(is_second_bet=True)
                            if not game.bot_folded:
                                game.resolve_showdown()

                    elif btn_raise and btn_raise.collidepoint((mx, my)):
                        raise_amt = 20
                        call_amt = game.bot_bet - game.player_bet
                        total_needed = call_amt + raise_amt
                        
                        if game.player_chips >= total_needed:
                            game.player_chips -= total_needed
                            game.player_bet += total_needed
                            game.pot += total_needed
                            game.trigger_shake(12, 18)
                            
                            bot_msg = game.bot_decision(is_second_bet=(game.state == "BET2"))
                            if not game.bot_folded:
                                if game.state == "BET1":
                                    game.state = "DISCARD"
                                    game.message = f"{bot_msg}. Select cards to swap."
                                else:
                                    game.resolve_showdown()
                        else:
                            game.message = "Not enough chips to raise!"

                    elif btn_fold and btn_fold.collidepoint((mx, my)):
                        game.player_folded = True
                        game.bot_chips += game.pot
                        game.state = "ROUND_OVER"
                        game.message = "You Folded! Bot wins the pot."

                elif btn_discard and btn_discard.collidepoint((mx, my)):
                    # Swap selected cards
                    new_hand = []
                    for card in game.player_hand:
                        if card.selected:
                            drawn = game.deck.draw(1)
                            if drawn:
                                new_hand.append(drawn[0])
                        else:
                            new_hand.append(card)
                    game.player_hand = new_hand
                    
                    # Bot discards and draws
                    game.bot_discard()
                    
                    # Move to final betting stage
                    game.state = "BET2"
                    game.message = "Cards swapped. Final betting round!"

        # Render Main Surface with Shake offset
        screen.fill(BLACK)
        screen.blit(canvas, (offset_x, offset_y))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()