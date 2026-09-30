import pygame
import random
import math
import asyncio
import sys

pygame.init()

WIDTH = 1000
HEIGHT = 800

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("asteroids")
clock = pygame.time.Clock()


async def main():
    font = pygame.font.Font(None, 36)

    def display_message(text, y_offset=0):
        text_surface = font.render(text, True, WHITE)
        text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
        screen.blit(text_surface, text_rect)

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

            screen.fill(BLACK)
            display_message(message + " (Y/N)")
            pygame.display.flip()
            clock.tick(30)
            await asyncio.sleep(0)
        return choice

    mouse_aim = await yes_no_choice("Do you want to use mouse aiming?")
    auto_aim = not mouse_aim and await yes_no_choice("Do you want to use auto aiming?")

    center = pygame.math.Vector2(WIDTH / 2, HEIGHT / 2)

    last_action_time = 0
    global asteroids, spawns

    ASTEROID_SPAWN_RADIUS = 32
    ASTEROID_SPEED_RANGE = 3
    ASTEROID_MIN_SPLIT_RADIUS = 8
    INITIAL_ASTEROID_SPAWNS = 2
    DRAG = 0.97
    SHIP_NOSE_LENGTH = 15
    SHIP_WING_LENGTH = 10
    SHIP_WING_ANGLE = 2.5
    SHIP_TURN_SPEED = 0.1
    ENEMY_TURN_RATE = 0.03
    ENEMY_HIT_RADIUS = 20
    ENEMY_SPAWN_OFFSET = 50

    asteroids = []
    spawns = INITIAL_ASTEROID_SPAWNS

    class Asteroid:
        def __init__(self, r, x, y):
            self.pos = pygame.math.Vector2(x, y)
            self.vel = pygame.math.Vector2(
                random.uniform(-ASTEROID_SPEED_RANGE, ASTEROID_SPEED_RANGE),
                random.uniform(-ASTEROID_SPEED_RANGE, ASTEROID_SPEED_RANGE),
            )
            self.r = r
            asteroids.append(self)

        def draw(self):
            pygame.draw.circle(screen, (75, 75, 75), self.pos.xy, self.r)

        def move(self):
            self.pos += self.vel
            self.pos.x %= WIDTH + self.r * 2
            self.pos.y %= HEIGHT + self.r * 2

        def destroy(self):
            if self.r > ASTEROID_MIN_SPLIT_RADIUS:
                Asteroid(self.r / 2, *self.pos)
                Asteroid(self.r / 2, *self.pos)

    enemies = []

    class Enemy:
        def __init__(self, pos: pygame.math.Vector2, angle_rads: float) -> Enemy:
            self.pos = pos
            self.vel = pygame.math.Vector2(0, 0)
            self.angle_rads = angle_rads
            self.state = "patrol"
            self.lost_player = False
            self.omega = random.choice([-ENEMY_TURN_RATE, ENEMY_TURN_RATE])
            self.attack_start = 0
            enemies.append(self)

        def move(self):
            to_ship = ship_pos - self.pos
            dist = to_ship.length()
            self.pos += self.vel
            self.vel *= DRAG
            self.pos.x %= WIDTH
            self.pos.y %= HEIGHT

            target = math.atan2(to_ship.y, to_ship.x)
            diff = (target - self.angle_rads + math.pi) % (2 * math.pi) - math.pi
            now = pygame.time.get_ticks()

            if dist < 500 and abs(diff) < 0.7:
                if self.state != "attack":
                    self.state = "attack"
                    self.lost_player = True
                    self.last_shot = now
            else:
                self.state = "patrol"

            match self.state:
                case "patrol":
                    if self.lost_player:
                        self.omega = random.choice([-ENEMY_TURN_RATE, ENEMY_TURN_RATE])
                        self.lost_player = False
                    self.angle_rads += self.omega
                case "attack":
                    self.angle_rads += max(
                        -ENEMY_TURN_RATE, min(ENEMY_TURN_RATE, diff * 0.1)
                    )
                    self.vel += (
                        pygame.math.Vector2(
                            math.cos(self.angle_rads), math.sin(self.angle_rads)
                        )
                        * 0.2
                    )
                    if now - self.last_shot > 1000:
                        Projectile(self.angle_rads, self.pos, self.vel, enemy_proj=True)
                        self.last_shot = now

        def draw(self):
            pygame.draw.polygon(
                screen,
                (255, 0, 0),
                [
                    self.pos
                    + pygame.math.Vector2(SHIP_NOSE_LENGTH, 0).rotate_rad(
                        self.angle_rads
                    ),
                    self.pos
                    + pygame.math.Vector2(SHIP_WING_LENGTH, 0).rotate_rad(
                        self.angle_rads + SHIP_WING_ANGLE
                    ),
                    self.pos
                    + pygame.math.Vector2(SHIP_WING_LENGTH, 0).rotate_rad(
                        self.angle_rads - SHIP_WING_ANGLE
                    ),
                ],
            )

    projectiles = []
    PROJECTILE_VELOCITY = 4

    class Projectile:
        def __init__(self, angle_radians, pos, ship_vel, enemy_proj=False):
            self.pos = pos.copy()
            self.vel = (
                pygame.math.Vector2(math.cos(angle_radians), math.sin(angle_radians))
                * PROJECTILE_VELOCITY
                + ship_vel
            )
            self.rect = pygame.Rect(*pos, 5, 5)
            self.enemy_proj = enemy_proj
            projectiles.append(self)

        def move(self):
            self.pos += self.vel
            self.rect.topleft = self.pos.xy
            if not (0 <= self.pos.x <= WIDTH and 0 <= self.pos.y <= HEIGHT):
                projectiles.remove(self)

        def draw(self):
            pygame.draw.rect(screen, WHITE, self.rect)

    global ship_pos, ship_vel
    ship_vel = pygame.math.Vector2(0, 0)
    ship_rads = math.pi / 2
    ship_pos = center.copy()

    COOLDOWN_TIME = 300
    global running
    running = True

    async def reset():
        global running, asteroids, ship_vel, ship_pos, spawns
        running = await yes_no_choice("Do you want to retry?")
        asteroids.clear()
        projectiles.clear()
        enemies.clear()
        ship_vel = pygame.math.Vector2(0, 0)
        ship_pos = center.copy()
        spawns = INITIAL_ASTEROID_SPAWNS
        for _ in range(spawns):
            Asteroid(
                ASTEROID_SPAWN_RADIUS,
                random.randint(0, WIDTH),
                random.randint(0, HEIGHT),
            )
        enemy_locs = [
            pygame.math.Vector2(ENEMY_SPAWN_OFFSET, ENEMY_SPAWN_OFFSET),
            pygame.math.Vector2(
                WIDTH - ENEMY_SPAWN_OFFSET, HEIGHT - ENEMY_SPAWN_OFFSET
            ),
        ]
        for pos in enemy_locs:
            Enemy(pos, math.radians((pos - center).as_polar()[1]))

    for _ in range(spawns):
        Asteroid(
            ASTEROID_SPAWN_RADIUS, random.randint(0, WIDTH), random.randint(0, HEIGHT)
        )

    enemy_locs = [
        pygame.math.Vector2(ENEMY_SPAWN_OFFSET, ENEMY_SPAWN_OFFSET),
        pygame.math.Vector2(WIDTH - ENEMY_SPAWN_OFFSET, HEIGHT - ENEMY_SPAWN_OFFSET),
    ]
    for pos in enemy_locs:
        Enemy(pos, math.radians((pos - center).as_polar()[1]))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and mouse_aim:
                Projectile(
                    (pygame.math.Vector2(event.pos) - ship_pos).as_polar()[1]
                    * math.pi
                    / 180,
                    ship_pos,
                    ship_vel,
                )

        if mouse_aim:
            mouse_pos = pygame.mouse.get_pos()
            ship_rads = (
                (pygame.math.Vector2(mouse_pos) - ship_pos).as_polar()[1]
                * math.pi
                / 180
            )
        for asteroid in asteroids:
            asteroid.move()
        for projectile in projectiles:
            projectile.move()
        for enemy in enemies:
            enemy.move()

        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ship_rads -= SHIP_TURN_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ship_rads += SHIP_TURN_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            ship_vel += (
                pygame.math.Vector2(math.cos(ship_rads), math.sin(ship_rads)) * 0.3
            )
        if (
            keys[pygame.K_SPACE]
            and current_time - last_action_time >= COOLDOWN_TIME
            and not mouse_aim
        ):
            if auto_aim:
                projections = []
                for asteroid in asteroids:
                    asteroid_projection = asteroid.pos
                    relative_vel = asteroid.vel - ship_vel
                    for _ in range(5):
                        time_to_intercept = (
                            ship_pos - asteroid_projection
                        ).length() / PROJECTILE_VELOCITY
                        asteroid_projection = (
                            asteroid.pos + relative_vel * time_to_intercept
                        )
                    projections.append(asteroid_projection)
                for enemy in enemies:
                    projections.append(enemy.pos)
                aim_vec = (
                    min(projections, key=lambda p: (p - ship_pos).length()) - ship_pos
                )
                Projectile(math.radians(aim_vec.as_polar()[1]), ship_pos, ship_vel)
            else:
                Projectile(ship_rads, ship_pos, ship_vel)
            last_action_time = current_time

        if not asteroids and not enemies:
            for i in range(spawns):
                Asteroid(
                    ASTEROID_SPAWN_RADIUS,
                    random.randint(0, WIDTH),
                    random.randint(0, HEIGHT),
                )
                if i >= len(enemy_locs):
                    Enemy(
                        pygame.math.Vector2(
                            random.randrange(WIDTH), random.randrange(HEIGHT)
                        ),
                        random.random() * math.pi * 2,
                    )
                else:
                    Enemy(enemy_locs[i], math.radians((pos - center).as_polar()[1]))
            spawns += 1

        ship_pos += ship_vel
        ship_pos.x %= WIDTH
        ship_pos.y %= HEIGHT
        ship_vel *= DRAG

        for asteroid in asteroids:
            if asteroid.pos.distance_to(ship_pos) < asteroid.r + 10:
                await reset()
        for enemy in enemies:
            if enemy.pos.distance_to(ship_pos) < ENEMY_HIT_RADIUS:
                await reset()
        for projectile in projectiles:
            for asteroid in asteroids:
                if asteroid.pos.distance_to(projectile.pos) < asteroid.r + 2.5:
                    asteroid.destroy()
                    asteroids.remove(asteroid)
                    projectiles.remove(projectile)
                    break
            for enemy in enemies:
                if (
                    not projectile.enemy_proj
                    and enemy.pos.distance_to(projectile.pos) < ENEMY_HIT_RADIUS
                ):
                    enemies.remove(enemy)
                    projectiles.remove(projectile)
            if projectile.enemy_proj and projectile.pos.distance_to(ship_pos) < 15:
                await reset()

        # drawing screen
        screen.fill(BLACK)
        for asteroid in asteroids:
            asteroid.draw()
        for projectile in projectiles:
            projectile.draw()
        for enemy in enemies:
            enemy.draw()
        pygame.draw.polygon(
            screen,
            WHITE,
            [
                ship_pos
                + pygame.math.Vector2(SHIP_NOSE_LENGTH, 0).rotate_rad(ship_rads),
                ship_pos
                + pygame.math.Vector2(SHIP_WING_LENGTH, 0).rotate_rad(
                    ship_rads + SHIP_WING_ANGLE
                ),
                ship_pos
                + pygame.math.Vector2(SHIP_WING_LENGTH, 0).rotate_rad(
                    ship_rads - SHIP_WING_ANGLE
                ),
            ],
        )
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


asyncio.run(main())
