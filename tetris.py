# tetris.py
import pygame
import random
import time
import os
# ========= Tamaño escalable =========
SCALE = 1.2  # Ajusta libremente (1.0, 1.2, 1.5, 2.0)
CELL = int(30 * SCALE)

# ===== Configuración del tablero =====
COLS = 10
ROWS = 20
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL

# Panel lateral 
SIDEBAR_W = int(220 * SCALE)

# Velocidad base 
BASE_SPEED_MS = 600

# Colores
BG_COLOR = (18, 18, 20)
GRID_COLOR = (35, 35, 40)
GHOST_COLOR = (80, 80, 90)
BORDER_COLOR = (28, 28, 32)
TEXT_COLOR = (235, 235, 235)
BTN_BG = (32, 32, 38)
BTN_BG_HOVER = (48, 48, 56)
BTN_BORDER = (70, 70, 80)

COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1],
          [1, 1]],
    'T': [[0, 1, 0],
          [1, 1, 1]],
    'S': [[0, 1, 1],
          [1, 1, 0]],
    'Z': [[1, 1, 0],
          [0, 1, 1]],
    'J': [[1, 0, 0],
          [1, 1, 1]],
    'L': [[0, 0, 1],
          [1, 1, 1]],
}

# Puntuación clásica aproximada
SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
LINES_PER_LEVEL = 10  # cada 10 líneas sube el nivel


def rotate_matrix(mat):
    return [list(row) for row in zip(*mat[::-1])]  # 90° clockwise


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.color = COLORS[kind]
        self.shape = [row[:] for row in SHAPES[kind]]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def rotated(self):
        return rotate_matrix(self.shape)


class TetrisGame:
    def __init__(self):
        pygame.init()

        # Fuentes primero 
        self.font = pygame.font.SysFont("Arial", max(16, int(18 * SCALE)))
        self.big_font = pygame.font.SysFont("Arial", max(20, int(26 * SCALE)), bold=True)

        # Cargar logo 
        self.logo_surface_raw = None
        self.logo_surface = None
        self.logo_path_used = None
        self._load_logo_raw() 

        # Calcula tamaño de ventana 
        self.window_w, self.window_h = self._compute_window_size()

        # Crear ventana
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption("Tetris con gestos")
        self.clock = pygame.time.Clock()

        # Ahora que hay display, finalizamos surface 
        self._finalize_logo_surface()

        # Estado del juego
        self.reset_game(hard_init=True)

        # UI
        self.mensaje_gesto = ""
        self.restart_rect = None
        self._start_time = time.time()

    # ======= Cálculo de layout/ventana =======
    def _compute_window_size(self):
        m = int(16 * SCALE)
        sep = int(12 * SCALE)
        line_h = self.font.get_height()
        big_h = self.big_font.get_height()

        # ALTURA DEL LOGO 
        logo_h = 0
        if getattr(self, "logo_surface", None) is not None:
            logo_h = self.logo_surface.get_height() + m  # margen debajo del logo

        title_h = big_h

        label_value_h = (line_h + big_h)
        stats_h = label_value_h * 3 + sep * 2

        gesto_h = line_h + sep

        next_title_h = big_h
        next_box_h = CELL * 4 + 8
        next_total_h = next_title_h + sep // 2 + next_box_h

        btn_h = int(44 * SCALE)

        instructions = [
            "Controles (cámara):",
            " Paz: mover IZQUIERDA",
            " Índice: mover DERECHA",
            " Puño: ROTAR",
            " Mano abierta: BAJAR",
            "",
            "Teclado:",
            "R: Reiniciar   ESC: Salir",
        ]
        instr_h = len(instructions) * line_h

        sidebar_h = (
            m + logo_h +        
            title_h +             
            m + stats_h +
            m + gesto_h +
            m + next_total_h +
            m + btn_h +
            m + instr_h +
            m
        )

        window_h = max(BOARD_H, sidebar_h)
        window_w = BOARD_W + SIDEBAR_W
        return window_w, window_h

    # ======= Estado =======
    def reset_game(self, hard_init=False):
        self.board = [[(0, (0, 0, 0)) for _ in range(COLS)] for _ in range(ROWS)]
        self.current = self._rand_piece()
        self.next_piece = self._rand_piece()
        self.drop_timer = 0
        self.speed_ms = BASE_SPEED_MS
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        if hard_init:
            self.running = True

    # ======= Lógica de piezas =======
    def _rand_piece(self):
        return Piece(random.choice(list(SHAPES.keys())))

    def _collides(self, dx, dy, shape=None):
        shp = shape if shape is not None else self.current.shape
        for y, row in enumerate(shp):
            for x, cell in enumerate(row):
                if not cell:
                    continue
                nx = self.current.x + x + dx
                ny = self.current.y + y + dy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and self.board[ny][nx][0]:
                    return True
        return False

    def _lock_piece(self):
        for y, row in enumerate(self.current.shape):
            for x, cell in enumerate(row):
                if cell:
                    tx = self.current.x + x
                    ty = self.current.y + y
                    if 0 <= ty < ROWS:
                        self.board[ty][tx] = (1, self.current.color)
                    else:
                        self.game_over = True
                        return

        cleared = self._clear_lines()
        if cleared:
            self._add_score(cleared)

        self.current = self.next_piece
        self.next_piece = self._rand_piece()

        if self._collides(0, 0):
            self.game_over = True

    def _clear_lines(self):
        new_board = [row for row in self.board if not all(v for v, _ in row)]
        cleared = ROWS - len(new_board)
        for _ in range(cleared):
            new_board.insert(0, [(0, (0, 0, 0)) for _ in range(COLS)])
        self.board = new_board
        self.lines += cleared
        while self.lines >= self.level * LINES_PER_LEVEL:
            self.level += 1
            self.speed_ms = max(120, int(BASE_SPEED_MS * (0.85 ** (self.level - 1))))
        return cleared

    def _add_score(self, lines_cleared, soft_drop_steps=0):
        self.score += SCORES.get(lines_cleared, 0)
        self.score += soft_drop_steps

    def _soft_drop(self):
        if not self._collides(0, 1):
            self.current.y += 1
            return 1
        else:
            self._lock_piece()
            return 0

    # ======= Gestos / Controles =======
    def mover(self, dx):
        if self.game_over:
            return
        if not self._collides(dx, 0):
            self.current.x += dx

    def bajar(self):
        if self.game_over:
            return
        gained = self._soft_drop()
        if gained:
            self._add_score(0, soft_drop_steps=gained)

    def rotar(self):
        if self.game_over:
            return
        new_shape = self.current.rotated()
        if not self._collides(0, 0, shape=new_shape):
            self.current.shape = new_shape
        else:
            if not self._collides(-1, 0, shape=new_shape):
                self.current.x -= 1
                self.current.shape = new_shape
            elif not self._collides(1, 0, shape=new_shape):
                self.current.x += 1
                self.current.shape = new_shape

    def handle_gesture(self, gesto):
        if self.game_over:
            self.mensaje_gesto = "Game Over — R para reiniciar"
            return
        self.mensaje_gesto = f"Gesto: {gesto}"
        if gesto == "izquierda":
            self.mover(-1)
        elif gesto == "derecha":
            self.mover(1)
        elif gesto == "abajo":
            self.bajar()
        elif gesto == "rotar":
            self.rotar()

    # ======= Bucle del juego =======
    def update(self):
        self.drop_timer += self.clock.get_rawtime()
        self.clock.tick()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if time.time() - self._start_time < 0.7:
                    continue
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.reset_game()
                elif not self.game_over:
                    if event.key == pygame.K_LEFT:
                        self.mover(-1)
                    elif event.key == pygame.K_RIGHT:
                        self.mover(1)
                    elif event.key == pygame.K_DOWN:
                        self.bajar()
                    elif event.key == pygame.K_UP:
                        self.rotar()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.restart_rect and self.restart_rect.collidepoint(event.pos):
                    self.reset_game()

        if not self.game_over and self.drop_timer > self.speed_ms:
            self._soft_drop()
            self.drop_timer = 0

    # ======= Dibujo / UI =======
    def draw(self):
        self.screen.fill(BG_COLOR)

        # Marco y fondo del tablero
        pygame.draw.rect(self.screen, BORDER_COLOR, (0, 0, BOARD_W, BOARD_H), border_radius=10)
        pygame.draw.rect(self.screen, BG_COLOR, (4, 4, BOARD_W - 8, BOARD_H - 8), border_radius=8)

        # --- LOGO dentro del tablero (antes de rejilla y piezas) ---
        self._draw_board_logo()

        # Rejilla
        for x in range(COLS + 1):
            px = x * CELL
            pygame.draw.line(self.screen, GRID_COLOR, (px, 0), (px, BOARD_H))
        for y in range(ROWS + 1):
            py = y * CELL
            pygame.draw.line(self.screen, GRID_COLOR, (0, py), (BOARD_W, py))

        # Ghost
        if not self.game_over:
            self._draw_ghost()

        # Celdas fijas
        for y in range(ROWS):
            for x in range(COLS):
                val, color = self.board[y][x]
                if val:
                    self._draw_cell(x, y, color)

        # Pieza actual
        for y, row in enumerate(self.current.shape):
            for x, cell in enumerate(row):
                if cell:
                    px = self.current.x + x
                    py = self.current.y + y
                    if py >= 0:
                        self._draw_cell(px, py, self.current.color)

        # Sidebar
        self._draw_sidebar()

        # Overlay de Game Over 
        if self.game_over:
            overlay = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
            txt = self.big_font.render("GAME OVER", True, (255, 255, 255))
            sub = self.font.render("Presiona R o el botón Reiniciar", True, (230, 230, 230))
            self.screen.blit(txt, txt.get_rect(center=(BOARD_W // 2, BOARD_H // 2 - int(14 * SCALE))))
            self.screen.blit(sub, sub.get_rect(center=(BOARD_W // 2, BOARD_H // 2 + int(14 * SCALE))))

        pygame.display.flip()


    def _draw_cell(self, x, y, color):
        rx = x * CELL + 2
        ry = y * CELL + 2
        rw = CELL - 4
        rh = CELL - 4
        pygame.draw.rect(self.screen, color, (rx, ry, rw, rh), border_radius=6)
        overlay = (min(color[0] + 25, 255), min(color[1] + 25, 255), min(color[2] + 25, 255))
        pygame.draw.rect(self.screen, overlay, (rx, ry, rw, rh // 3), border_radius=6)

    def _draw_ghost(self):
        ghost_y = self.current.y
        while not self._collides(0, (ghost_y - self.current.y) + 1):
            ghost_y += 1
        for y, row in enumerate(self.current.shape):
            for x, cell in enumerate(row):
                if cell:
                    gx = self.current.x + x
                    gy = ghost_y + y
                    if gy >= 0:
                        rx = gx * CELL + 2
                        ry = gy * CELL + 2
                        rw = CELL - 4
                        rh = CELL - 4
                        pygame.draw.rect(self.screen, GHOST_COLOR, (rx, ry, rw, rh), width=2, border_radius=6)

    def _draw_sidebar(self):
        left = BOARD_W
        w = SIDEBAR_W
        h = self.window_h

        # Panel base
        pygame.draw.rect(self.screen, BORDER_COLOR, (left, 0, w, h))
        inner = pygame.Rect(left + 4, 4, w - 8, h - 8)
        pygame.draw.rect(self.screen, (22, 22, 26), inner, border_radius=12)

        # Métricas
        m = int(16 * SCALE)     
        sep = int(12 * SCALE)  
        x = left + m
        y = m
        line_h = self.font.get_height()

        # === LOGO como marca de agua (debajo del contenido) ===
        if getattr(self, "logo_surface", None) is not None:
            WATERMARK_ALPHA = 100  
            try:
                self.logo_surface.set_alpha(WATERMARK_ALPHA)
            except Exception:
                pass

            lw = self.logo_surface.get_width()
            lh = self.logo_surface.get_height()
            logo_x = left + (w - lw) // 2
            logo_y = m  
            self.screen.blit(self.logo_surface, (logo_x, logo_y))

        title = self.big_font.render("TETRIS", True, TEXT_COLOR)
        self.screen.blit(title, (x, y))
        y += title.get_height() + m

        # --- Score / Lines / Level ---
        self._label_value("Puntuación", f"{self.score}", x, y)
        y += self.big_font.get_height() + sep

        self._label_value("Líneas", f"{self.lines}", x, y)
        y += self.big_font.get_height() + sep

        self._label_value("Nivel", f"{self.level}", x, y)
        y += self.big_font.get_height() + m

        # --- Mensaje de gesto ---
        gest = self.font.render(self.mensaje_gesto, True, TEXT_COLOR)
        self.screen.blit(gest, (x, y))
        y += line_h + m

        # --- Siguiente pieza ---
        nxt_lbl = self.big_font.render("Siguiente", True, TEXT_COLOR)
        self.screen.blit(nxt_lbl, (x, y))
        y += nxt_lbl.get_height() + sep // 2

        # Caja 4x4
        box_size = CELL * 4
        rect = pygame.Rect(x - 4, y - 4, box_size + 8, box_size + 8)
        pygame.draw.rect(self.screen, (16, 16, 18), rect, border_radius=10)
        pygame.draw.rect(self.screen, (40, 40, 46), rect, width=2, border_radius=10)
        self._draw_next_piece(x, y)
        y += box_size + m

        # --- Botón Reiniciar ---
        btn_h = int(44 * SCALE)
        btn_w = w - 2 * m
        btn_x = x
        btn_y = y
        hovered = pygame.Rect(btn_x, btn_y, btn_w, btn_h).collidepoint(pygame.mouse.get_pos())
        bg = BTN_BG_HOVER if hovered else BTN_BG
        pygame.draw.rect(self.screen, bg, (btn_x, btn_y, btn_w, btn_h), border_radius=10)
        pygame.draw.rect(self.screen, BTN_BORDER, (btn_x, btn_y, btn_w, btn_h), width=2, border_radius=10)
        label = self.big_font.render("Reiniciar (R)", True, (230, 230, 240))
        self.screen.blit(label, label.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2)))
        self.restart_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        y += btn_h + m

        # --- Instrucciones ---
        info = [
            "Controles (cámara):",
            " Paz: mover IZQUIERDA",
            " Índice: mover DERECHA",
            " Puño: ROTAR",
            " Mano abierta: BAJAR",
            "",
            "Teclado:",
            "R: Reiniciar   ESC: Salir",
        ]
        for line in info:
            shadow = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(shadow, (x + 1, y + 1))
            t = self.font.render(line, True, (200, 200, 210))
            self.screen.blit(t, (x, y))
            y += line_h


    def _label_value(self, label, value, x, y):
        l = self.font.render(label, True, (180, 180, 190))
        v = self.big_font.render(value, True, TEXT_COLOR)
        self.screen.blit(l, (x, y))
        self.screen.blit(v, (x, y + self.font.get_height()))

    def _draw_next_piece(self, x, y):
        box_size = CELL * 4
        shp = self.next_piece.shape
        h = len(shp)
        w = len(shp[0])
        offset_x = x + (box_size - w * CELL) // 2
        offset_y = y + (box_size - h * CELL) // 2
        for ry, row in enumerate(shp):
            for rx, cell in enumerate(row):
                if cell:
                    cx = offset_x + rx * CELL
                    cy = offset_y + ry * CELL
                    pygame.draw.rect(self.screen, self.next_piece.color,
                                     (cx + 2, cy + 2, CELL - 4, CELL - 4), border_radius=6)
                    overlay = (
                        min(self.next_piece.color[0] + 25, 255),
                        min(self.next_piece.color[1] + 25, 255),
                        min(self.next_piece.color[2] + 25, 255),
                    )
                    pygame.draw.rect(self.screen, overlay,
                                     (cx + 2, cy + 2, CELL - 4, (CELL - 4)//3), border_radius=6)

    def _load_logo_raw(self):
        """Carga el PNG sin convert_alpha (antes de set_mode). Intenta rutas."""
        rel = os.path.join("Recursos", "CIS-LOGOS.png")
        abs_path = r"C:\Users\makib\Documents\EntornosVirtuales\tetris_hand_control\Recursos\CIS-LOGOS.png"

        candidates = [rel, abs_path]
        print(f"[LOGO] CWD: {os.getcwd()}")
        for p in candidates:
            if os.path.exists(p):
                try:
                    self.logo_surface_raw = pygame.image.load(p)  
                    self.logo_path_used = p
                    print(f"[LOGO] Cargado RAW desde: {p} size={self.logo_surface_raw.get_width()}x{self.logo_surface_raw.get_height()}")
                    return
                except Exception as e:
                    print(f"[LOGO] Falló carga {p}: {e}")
        print("[LOGO] No se encontró el logo en rutas candidatas (relativa ni absoluta).")

    def _finalize_logo_surface(self):
        """Convierte con alpha, escala para el tablero y aplica transparencia."""
        if self.logo_surface_raw is None:
            self.logo_surface = None
            return
        try:
            surf = self.logo_surface_raw.convert_alpha()  # ya hay display

            # Escala para el TABLERO (no para el sidebar)
            # Ocuparemos como máx. 60% del ancho y 30% del alto del tablero
            max_w = int(BOARD_W * 0.60)
            max_h = int(BOARD_H * 0.30)
            rw = max_w / surf.get_width()
            rh = max_h / surf.get_height()
            scale = min(1.0, rw, rh)
            if scale < 1.0:
                new_size = (int(surf.get_width() * scale), int(surf.get_height() * scale))
                surf = pygame.transform.smoothscale(surf, new_size)

            # Marca de agua
            surf.set_alpha(100)  # 80–140 se ve bien

            self.logo_surface = surf
            print(f"[LOGO] Finalizado (convert+scale) {self.logo_surface.get_width()}x{self.logo_surface.get_height()}")
        except Exception as e:
            print(f"[LOGO] No se pudo finalizar el logo: {e}")
            self.logo_surface = None


    def _draw_board_logo(self):
        """Dibuja el logo como marca de agua en el área de juego (centrado)."""
        if self.logo_surface is None:
            return
        lw, lh = self.logo_surface.get_width(), self.logo_surface.get_height()
        # Posición: centrado dentro del tablero
        x = (BOARD_W - lw) // 2
        y = (BOARD_H - lh) // 2
        self.screen.blit(self.logo_surface, (x, y))
