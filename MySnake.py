"""A small Snake game built with pygame."""

import random

import pygame


CELL_SIZE = 24
GRID_WIDTH = 25
GRID_HEIGHT = 20
PLAY_WIDTH = CELL_SIZE * GRID_WIDTH
PLAY_HEIGHT = CELL_SIZE * GRID_HEIGHT
WINDOW_WIDTH = PLAY_WIDTH
WINDOW_HEIGHT = PLAY_HEIGHT + 64
FPS = 12

BACKGROUND = (18, 24, 32)
BOARD = (26, 36, 45)
GRID = (37, 51, 61)
SNAKE_HEAD = (102, 214, 128)
SNAKE_BODY = (61, 166, 99)
FOOD = (246, 104, 92)
TEXT = (237, 242, 235)


def new_food(snake):
    available = [
        (x, y)
        for y in range(GRID_HEIGHT)
        for x in range(GRID_WIDTH)
        if (x, y) not in snake
    ]
    return random.choice(available) if available else None


def reset_game():
    snake = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
    direction = (1, 0)
    return snake, direction, direction, new_food(snake), 0, False


def draw_board(screen, snake, food):
    pygame.draw.rect(screen, BOARD, (0, 0, PLAY_WIDTH, PLAY_HEIGHT))
    for x in range(GRID_WIDTH + 1):
        pygame.draw.line(screen, GRID, (x * CELL_SIZE, 0), (x * CELL_SIZE, PLAY_HEIGHT))
    for y in range(GRID_HEIGHT + 1):
        pygame.draw.line(screen, GRID, (0, y * CELL_SIZE), (PLAY_WIDTH, y * CELL_SIZE))

    if food is not None:
        food_rect = pygame.Rect(
            food[0] * CELL_SIZE + 3,
            food[1] * CELL_SIZE + 3,
            CELL_SIZE - 6,
            CELL_SIZE - 6,
        )
        pygame.draw.rect(screen, FOOD, food_rect, border_radius=5)

    for index, (x, y) in enumerate(snake):
        color = SNAKE_HEAD if index == 0 else SNAKE_BODY
        body_rect = pygame.Rect(
            x * CELL_SIZE + 2,
            y * CELL_SIZE + 2,
            CELL_SIZE - 4,
            CELL_SIZE - 4,
        )
        pygame.draw.rect(screen, color, body_rect, border_radius=5)


def draw_status(screen, font, score, game_over, paused):
    pygame.draw.rect(screen, BACKGROUND, (0, PLAY_HEIGHT, WINDOW_WIDTH, 64))
    score_text = font.render(f"SCORE  {score}", True, TEXT)
    screen.blit(score_text, (16, PLAY_HEIGHT + 18))

    if game_over:
        message = "GAME OVER - Press R to restart"
    elif paused:
        message = "PAUSED - Press P to continue"
    else:
        message = "Arrow keys move  |  P pause"
    message_text = font.render(message, True, TEXT)
    screen.blit(message_text, (WINDOW_WIDTH - message_text.get_width() - 16, PLAY_HEIGHT + 18))


def main():
    pygame.init()
    pygame.display.set_caption("My Snake")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 26)

    snake, direction, next_direction, food, score, game_over = reset_game()
    paused = False
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_p and not game_over:
                    paused = not paused
                elif event.key == pygame.K_r and game_over:
                    snake, direction, next_direction, food, score, game_over = reset_game()
                    paused = False
                elif event.key in (pygame.K_UP, pygame.K_w) and direction != (0, 1):
                    next_direction = (0, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_s) and direction != (0, -1):
                    next_direction = (0, 1)
                elif event.key in (pygame.K_LEFT, pygame.K_a) and direction != (1, 0):
                    next_direction = (-1, 0)
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and direction != (-1, 0):
                    next_direction = (1, 0)

        if not paused and not game_over:
            direction = next_direction
            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])
            hits_wall = not (0 <= new_head[0] < GRID_WIDTH and 0 <= new_head[1] < GRID_HEIGHT)
            is_eating = new_head == food
            hits_body = new_head in (snake if is_eating else snake[:-1])

            if hits_wall or hits_body:
                game_over = True
            else:
                snake.insert(0, new_head)
                if is_eating:
                    score += 1
                    food = new_food(snake)
                else:
                    snake.pop()

        draw_board(screen, snake, food)
        draw_status(screen, font, score, game_over, paused)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()