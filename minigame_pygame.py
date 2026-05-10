import pygame
import random
import sys

# Pygame Mini Game for Trigonometry
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Trigo Mini Game - X-E3")
    
    # Colors
    NEON_BLUE = (0, 255, 255)
    NEON_PINK = (255, 0, 255)
    BLACK = (13, 2, 33)
    WHITE = (255, 255, 255)
    
    font = pygame.font.SysFont('Arial', 32)
    small_font = pygame.font.SysFont('Arial', 24)
    
    questions = [
        {"q": "Sin(30°)?", "a": "1/2"},
        {"q": "Cos(60°)?", "a": "1/2"},
        {"q": "Tan(45°)?", "a": "1"},
        {"q": "Sin(150°)?", "a": "1/2"},
        {"q": "Cos(180°)?", "a": "-1"}
    ]
    
    current_q = random.choice(questions)
    score = 0
    running = True
    input_text = ""
    feedback = ""
    
    while running:
        screen.fill(BLACK)
        
        # UI
        title = font.render("CYBER TRIGO - PYGAME EDITION", True, NEON_PINK)
        screen.blit(title, (200, 50))
        
        q_surface = font.render(f"Soal: {current_q['q']}", True, NEON_BLUE)
        screen.blit(q_surface, (100, 150))
        
        input_surface = font.render(f"Jawabanmu: {input_text}", True, WHITE)
        screen.blit(input_surface, (100, 250))
        
        feedback_surface = small_font.render(feedback, True, (0, 255, 0) if "Benar" in feedback else (255, 0, 0))
        screen.blit(feedback_surface, (100, 350))
        
        instruction = small_font.render("Ketik jawaban (misal: 1/2 atau -1) lalu Tekan ENTER", True, (150, 150, 150))
        screen.blit(instruction, (100, 500))

        score_surface = small_font.render(f"Skor: {score}", True, WHITE)
        screen.blit(score_surface, (650, 20))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if input_text == current_q['a']:
                        feedback = "BENAR! (NICE!)"
                        score += 10
                    else:
                        feedback = f"SALAH! Jawaban: {current_q['a']}"
                    input_text = ""
                    current_q = random.choice(questions)
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
                    
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
