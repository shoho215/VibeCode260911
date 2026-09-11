"""NEON TETRIS - Python/Pygame port of the original HTML5 game."""

import random
from pathlib import Path

import pygame

COLS, ROWS = 10, 20
CELL = 30
BOARD_WIDTH, BOARD_HEIGHT = COLS * CELL, ROWS * CELL
WINDOW_WIDTH, WINDOW_HEIGHT = 720, 720

INK = (16, 21, 27)
PAPER = (231, 240, 232)
MINT = (181, 230, 200)
LIME = (200, 241, 105)
ORANGE = (255, 120, 79)
PINK = (255, 93, 147)
CYAN = (87, 217, 232)
YELLOW = (247, 214, 91)
PURPLE = (157, 135, 237)
DARK_BOARD = (23, 36, 42)
BLOCK_COLORS = [None, CYAN, YELLOW, ORANGE, PURPLE, (87, 200, 120), PINK, LIME]
SHAPES = (
    ((1, 1, 1, 1),),
    ((2, 2), (2, 2)),
    ((0, 3, 0), (3, 3, 3)),
    ((4, 0, 0), (4, 4, 4)),
    ((0, 0, 5), (5, 5, 5)),
    ((0, 6, 6), (6, 6, 0)),
    ((7, 7, 0), (0, 7, 7)),
)
HIGH_SCORE_FILE = Path(__file__).with_name(".neon_tetris_high_score")


def make_board():
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


def rotate_shape(shape):
    return [list(row) for row in zip(*shape[::-1])]


class Piece:
    def __init__(self, shape):
        self.shape = [list(row) for row in shape]
        self.x = (COLS - len(self.shape[0])) // 2
        self.y = 0


class TetrisGame:
    def __init__(self):
        self.high_score = self.load_high_score()
        self.reset()

    @staticmethod
    def load_high_score():
        try:
            return int(HIGH_SCORE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0

    def save_high_score(self):
        try:
            HIGH_SCORE_FILE.write_text(str(self.high_score), encoding="utf-8")
        except OSError:
            pass

    def reset(self):
        self.board = make_board()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.drop_timer = 0
        self.paused = False
        self.game_over = False
        self.bag = []
        self.current = self.new_piece()
        self.next_piece = self.new_piece()

    def new_piece(self):
        if not self.bag:
            self.bag = list(range(len(SHAPES)))
            random.shuffle(self.bag)
        return Piece(SHAPES[self.bag.pop()])

    def collides(self, piece):
        for row_index, row in enumerate(piece.shape):
            for column_index, value in enumerate(row):
                if not value:
                    continue
                board_x = piece.x + column_index
                board_y = piece.y + row_index
                if board_x < 0 or board_x >= COLS or board_y >= ROWS:
                    return True
                if board_y >= 0 and self.board[board_y][board_x]:
                    return True
        return False

    def move(self, direction):
        if self.paused or self.game_over:
            return
        self.current.x += direction
        if self.collides(self.current):
            self.current.x -= direction

    def rotate(self):
        if self.paused or self.game_over:
            return
        previous_shape = self.current.shape
        self.current.shape = rotate_shape(previous_shape)
        if self.collides(self.current):
            self.current.x += 1
            if self.collides(self.current):
                self.current.x -= 2
            if self.collides(self.current):
                self.current.x += 1
                self.current.shape = previous_shape

    def drop(self, manual=False):
        if self.paused or self.game_over:
            return
        self.current.y += 1
        if self.collides(self.current):
            self.current.y -= 1
            self.merge_piece()
            self.clear_lines()
            self.current = self.next_piece
            self.next_piece = self.new_piece()
            if self.collides(self.current):
                self.game_over = True
        elif manual:
            self.score += 1
            self.update_high_score()
        self.drop_timer = 0

    def hard_drop(self):
        if self.paused or self.game_over:
            return
        distance = 0
        while not self.collides(self.current):
            self.current.y += 1
            distance += 1
        self.current.y -= 1
        self.score += max(0, distance - 1) * 2
        self.update_high_score()
        self.drop()

    def merge_piece(self):
        for row_index, row in enumerate(self.current.shape):
            for column_index, value in enumerate(row):
                board_y = self.current.y + row_index
                board_x = self.current.x + column_index
                if value and board_y >= 0:
                    self.board[board_y][board_x] = value

    def clear_lines(self):
        complete_rows = [row for row in self.board if all(row)]
        if not complete_rows:
            return
        self.board = [row for row in self.board if not all(row)]
        self.board = [[0] * COLS for _ in range(len(complete_rows))] + self.board
        count = len(complete_rows)
        self.score += (0, 100, 300, 500, 800)[count] * self.level
        self.lines += count
        self.level = self.lines // 10 + 1
        self.update_high_score()

    def update_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def update(self, elapsed_ms):
        if self.paused or self.game_over:
            return
        self.drop_timer += elapsed_ms
        interval = max(110, 750 - (self.level - 1) * 55)
        if self.drop_timer > interval:
            self.drop()


def draw_block(surface, x, y, size, color):
    rect = pygame.Rect(x * size + 1, y * size + 1, size - 2, size - 2)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, tuple(min(255, channel + 45) for channel in color), (rect.x + 2, rect.y + 2, max(1, size - 7), 3))
    pygame.draw.rect(surface, (90, 100, 100), rect, 1)


def draw_board(surface, game):
    surface.fill(DARK_BOARD)
    for x in range(COLS + 1):
        pygame.draw.line(surface, (34, 52, 58), (x * CELL, 0), (x * CELL, BOARD_HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, (34, 52, 58), (0, y * CELL), (BOARD_WIDTH, y * CELL))
    for y, row in enumerate(game.board):
        for x, value in enumerate(row):
            if value:
                draw_block(surface, x, y, CELL, BLOCK_COLORS[value])
    for y, row in enumerate(game.current.shape):
        for x, value in enumerate(row):
            if value:
                draw_block(surface, game.current.x + x, game.current.y + y, CELL, BLOCK_COLORS[value])


def draw_next(surface, game):
    surface.fill((255, 210, 180))
    size = 24
    offset_x = (5 - len(game.next_piece.shape[0])) * size // 2
    offset_y = (5 - len(game.next_piece.shape)) * size // 2
    for y, row in enumerate(game.next_piece.shape):
        for x, value in enumerate(row):
            if value:
                draw_block(surface, (offset_x // size) + x, (offset_y // size) + y, size, BLOCK_COLORS[value])


def text(surface, font, message, position, color=INK):
    surface.blit(font.render(message, True, color), position)


def draw_panel(surface, game, fonts, board_surface, next_surface):
    title_font, label_font, value_font, small_font = fonts
    surface.fill(MINT)
    pygame.draw.polygon(surface, (206, 244, 211), [(0, 0), (WINDOW_WIDTH, 0), (WINDOW_WIDTH, 160), (0, 90)])
    text(surface, label_font, "ARCADE / 001", (45, 34))
    text(surface, title_font, "NEON", (42, 52))
    text(surface, title_font, "TETRIS", (190, 52), ORANGE)
    draw_board(board_surface, game)
    surface.blit(board_surface, (45, 145))

    panel_x = 405
    stat_colors = (PAPER, YELLOW, CYAN, PINK)
    stat_labels = (("SCORE", game.score), ("HIGH SCORE", game.high_score), ("LEVEL", game.level), ("LINES", game.lines))
    for index, ((label, value), color) in enumerate(zip(stat_labels, stat_colors)):
        x = panel_x + (index % 2) * 143
        y = 145 + (index // 2) * 88
        rect = pygame.Rect(x, y, 134, 78)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, INK, rect, 3)
        text(surface, small_font, label, (x + 11, y + 10))
        text(surface, value_font, str(value), (x + 11, y + 35))

    next_rect = pygame.Rect(panel_x, 330, 277, 177)
    pygame.draw.rect(surface, ORANGE, next_rect)
    pygame.draw.rect(surface, INK, next_rect, 3)
    text(surface, small_font, "NEXT BLOCK", (panel_x + 16, 346))
    pygame.draw.rect(surface, (255, 210, 180), (panel_x + 16, 373, 120, 120))
    pygame.draw.rect(surface, INK, (panel_x + 16, 373, 120, 120), 2)
    draw_next(next_surface, game)
    surface.blit(next_surface, (panel_x + 16, 373))

    text(surface, small_font, "CONTROLS", (panel_x, 545))
    controls = ["ARROWS   MOVE / ROTATE", "DOWN     SOFT DROP", "SPACE    HARD DROP", "P        PAUSE"]
    for index, control in enumerate(controls):
        text(surface, small_font, control, (panel_x, 570 + index * 21))

    if game.paused or game.game_over:
        overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((16, 21, 27, 225))
        board_surface.blit(overlay, (0, 0))
        message = "GAME OVER" if game.game_over else "PAUSED"
        message_surface = title_font.render(message, True, PAPER)
        board_surface.blit(message_surface, message_surface.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 - 15)))
        hint = small_font.render("R  RESTART", True, PAPER)
        board_surface.blit(hint, hint.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 35)))

    text(surface, small_font, "COMPLETE LINES. KEEP THE FLOW.", (45, 675))


def main():
    pygame.init()
    pygame.display.set_caption("NEON TETRIS")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 74)
    label_font = pygame.font.Font(None, 20)
    value_font = pygame.font.Font(None, 38)
    small_font = pygame.font.Font(None, 17)
    fonts = (title_font, label_font, value_font, small_font)
    board_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    next_surface = pygame.Surface((120, 120))
    game = TetrisGame()
    running = True

    while running:
        elapsed = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    game.move(-1)
                elif event.key == pygame.K_RIGHT:
                    game.move(1)
                elif event.key == pygame.K_DOWN:
                    game.drop(manual=True)
                elif event.key == pygame.K_UP:
                    game.rotate()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
                elif event.key == pygame.K_p:
                    if not game.game_over:
                        game.paused = not game.paused
                elif event.key == pygame.K_r:
                    game.reset()
        game.update(elapsed)
        draw_panel(screen, game, fonts, board_surface, next_surface)
        pygame.display.flip()

    game.save_high_score()
    pygame.quit()


if __name__ == "__main__":
    main()
