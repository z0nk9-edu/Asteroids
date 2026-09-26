import pygame
import random
import math
import asyncio
import sys

pygame.init()

WIDTH = 1000
HEIGHT = 800

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("asteroids")
clock = pygame.time.Clock()

async def main():
    font = pygame.font.Font(None, 36)  # Default font with size 36

    # Function to display a message on the screen
    def display_message(text, y_offset=0):
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
        screen.blit(text_surface, text_rect)

    # Wait for user input on the screen
    async def yes_no_choice(message):
        choice = None
        while choice is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        choice = True
                    elif event.key == pygame.K_n:
                        choice = False

            screen.fill((0, 0, 0))
            display_message(message + " (Y/N)")
            pygame.display.flip()
            clock.tick(30)
            await asyncio.sleep(0)
        return choice


    mouse_aim = await yes_no_choice("Do you want to use mouse aiming?")
    auto_aim = not mouse_aim and await yes_no_choice("Do you want to use auto aiming?")

    last_action_time = 0
    asteroids = []
    spawns = 2

    class Asteroid:
        def __init__(self, r, x, y):
            self.pos = pygame.math.Vector2(x, y)
            self.vel = pygame.math.Vector2(random.uniform(-3, 3), random.uniform(-3, 3))
            self.r = r
            asteroids.append(self)

        def draw(self):
            pygame.draw.circle(screen, (75, 75, 75), self.pos.xy, self.r)

        def move(self):
            self.pos += self.vel
            self.pos.x %= WIDTH + self.r * 2  
            self.pos.y %= HEIGHT + self.r * 2  

        def destroy(self):
            if self.r > 8:
                Asteroid(self.r / 2, *self.pos)  
                Asteroid(self.r / 2, *self.pos)
            

        def apply_force(self, force):
            self.vel += force


    projectiles = []
    PROJECTILE_VELOCITY = 4

    class Projectile:
        def __init__(self, angle_radians, x, y, ship_vel):
            self.pos = pygame.math.Vector2(x, y)
            self.vel = pygame.math.Vector2(math.cos(angle_radians), math.sin(angle_radians)) * PROJECTILE_VELOCITY + ship_vel
            self.rect = pygame.Rect(x, y, 5, 5)
            projectiles.append(self)

        def move(self):
            self.pos += self.vel
            self.rect.topleft = self.pos.xy
            if not (0 <= self.pos.x <= WIDTH and 0 <= self.pos.y <= HEIGHT):
                projectiles.remove(self)

        def draw(self):
            pygame.draw.rect(screen, (255, 255, 255), self.rect)


    ship_vel = pygame.math.Vector2(0, 0)
    ship_rads = math.pi / 2
    ship_pos = pygame.math.Vector2(WIDTH / 2, HEIGHT / 2)

    COOLDOWN_TIME = 300

    running = True

    for _ in range(spawns):
        Asteroid(32, random.randint(0, WIDTH), random.randint(0, HEIGHT))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and mouse_aim:
                Projectile((pygame.math.Vector2(event.pos) - ship_pos).as_polar()[1]*math.pi/180, *ship_pos, ship_vel)

        if mouse_aim:
            mouse_pos = pygame.mouse.get_pos()
            ship_rads = (pygame.math.Vector2(mouse_pos) - ship_pos).as_polar()[1] * math.pi / 180
        for asteroid in asteroids:
            asteroid.move()
        for projectile in projectiles:
            projectile.move()

        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()

        if keys[pygame.K_LEFT]:
            ship_rads -= 0.1
        if keys[pygame.K_RIGHT]:
            ship_rads += 0.1
        if keys[pygame.K_UP]:
            ship_vel += pygame.math.Vector2(math.cos(ship_rads), math.sin(ship_rads)) * 0.3
        if keys[pygame.K_SPACE] and current_time - last_action_time >= COOLDOWN_TIME and not mouse_aim:
            if auto_aim and asteroids:
                projections = []
                for asteroid in asteroids:
                    asteroid_projection = asteroid.pos
                    relative_vel = asteroid.vel - ship_vel
                    for _ in range(5):
                        time_to_intercept = (ship_pos - asteroid_projection).length() / PROJECTILE_VELOCITY
                        asteroid_projection = asteroid.pos + relative_vel * time_to_intercept
                    projections.append(asteroid_projection)
                aim_vec = min(projections, key=lambda p: (p - ship_pos).length()) - ship_pos
                Projectile(math.radians(aim_vec.as_polar()[1]), *ship_pos, ship_vel)
            else: 
                Projectile(ship_rads, *ship_pos, ship_vel)  
            last_action_time = current_time
        
        if not asteroids:
            for _ in range(spawns):
                Asteroid(32, random.randint(0, WIDTH), random.randint(0, HEIGHT))
                spawns += 1

        ship_pos += ship_vel
        ship_pos.x %= WIDTH  
        ship_pos.y %= HEIGHT  
        ship_vel *= 0.97 

        for asteroid in asteroids:
            if asteroid.pos.distance_to(ship_pos) < asteroid.r + 10:
                running = False
        for projectile in projectiles:
            for asteroid in asteroids:
                if asteroid.pos.distance_to(projectile.pos) < asteroid.r + 2.5:
                    asteroid.destroy()
                    asteroids.remove(asteroid)
                    projectiles.remove(projectile)
                    break

        # drawing screen
        screen.fill((0, 0, 0))
        for asteroid in asteroids:
            asteroid.draw()
        for projectile in projectiles:
            projectile.draw()
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [
                ship_pos + pygame.math.Vector2(15, 0).rotate_rad(ship_rads),
                ship_pos + pygame.math.Vector2(10, 0).rotate_rad(ship_rads + 2.5),
                ship_pos + pygame.math.Vector2(10, 0).rotate_rad(ship_rads - 2.5),
            ],
        )
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()
asyncio.run(main())