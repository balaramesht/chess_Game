import sys
import math
import time
import threading
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import os

import pygame as pg
import chess

WINDOW_SIZE = 720
BOARD_MARGIN = 32
BOARD_SIZE = WINDOW_SIZE - 2 * BOARD_MARGIN
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 60

# Colors (wood-like board)
LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
BORDER_DARK = (110, 78, 46)
BORDER_LIGHT = (170, 120, 80)
HIGHLIGHT = (246, 246, 105)
MOVE_HINT = (80, 180, 80)
CHECK_RED = (215, 0, 0)

WHITE_PIECE = (245, 245, 245)
WHITE_SHADE = (210, 210, 210)
BLACK_PIECE = (30, 30, 30)
BLACK_SHADE = (65, 65, 65)
EDGE_STROKE = (15, 15, 15)

PIECE_SCALE = 0.8
ASSETS_PIECES_DIR = os.path.join(os.path.dirname(__file__), "assets", "pieces")

@dataclass
class PlayerMode:
    white_is_human: bool = True
    black_is_human: bool = False
    ai_depth: int = 3

class BoardRenderer:
    def __init__(self, surface: pg.Surface):
        self.surface = surface
        self.piece_surfaces: Dict[Tuple[bool, chess.PieceType], pg.Surface] = {}
        self._build_piece_cache()

    def _build_piece_cache(self) -> None:
        # Load image assets if available; fallback to vector-drawn pieces
        for is_white in (True, False):
            for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
                img_surf = self._load_image_for_piece(is_white, piece_type)
                if img_surf is None:
                    surf = pg.Surface((SQUARE_SIZE, SQUARE_SIZE), pg.SRCALPHA)
                    self._draw_piece(surf, is_white, piece_type)
                else:
                    surf = img_surf
                self.piece_surfaces[(is_white, piece_type)] = surf

    def _load_image_for_piece(self, is_white: bool, piece_type: chess.PieceType) -> Optional[pg.Surface]:
        letter_by_type = {
            chess.PAWN: "p",
            chess.KNIGHT: "n",
            chess.BISHOP: "b",
            chess.ROOK: "r",
            chess.QUEEN: "q",
            chess.KING: "k",
        }
        color_prefix = "w" if is_white else "b"
        filename = f"{color_prefix}{letter_by_type[piece_type]}.png"
        path = os.path.join(ASSETS_PIECES_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            img = pg.image.load(path).convert_alpha()
            scaled = pg.transform.smoothscale(img, (SQUARE_SIZE, SQUARE_SIZE))
            return scaled
        except Exception:
            return None

    def draw_board(self, board: chess.Board, selected_sq: Optional[chess.Square], legal_targets: set) -> None:
        self._draw_wood_frame()
        # Squares
        for rank in range(8):
            for file in range(8):
                square_color = LIGHT_SQ if (rank + file) % 2 == 0 else DARK_SQ
                x = BOARD_MARGIN + file * SQUARE_SIZE
                y = BOARD_MARGIN + (7 - rank) * SQUARE_SIZE
                pg.draw.rect(self.surface, square_color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

        # Highlights
        if board.is_check():
            king_square = board.king(board.turn)
            if king_square is not None:
                fx = chess.square_file(king_square)
                fr = chess.square_rank(king_square)
                x = BOARD_MARGIN + fx * SQUARE_SIZE
                y = BOARD_MARGIN + (7 - fr) * SQUARE_SIZE
                pg.draw.rect(self.surface, (255, 80, 80, 90), (x, y, SQUARE_SIZE, SQUARE_SIZE), border_radius=6)

        if selected_sq is not None:
            fx = chess.square_file(selected_sq)
            fr = chess.square_rank(selected_sq)
            x = BOARD_MARGIN + fx * SQUARE_SIZE
            y = BOARD_MARGIN + (7 - fr) * SQUARE_SIZE
            pg.draw.rect(self.surface, HIGHLIGHT, (x, y, SQUARE_SIZE, SQUARE_SIZE), width=4)
            for target in legal_targets:
                tx = chess.square_file(target)
                tr = chess.square_rank(target)
                cx = BOARD_MARGIN + tx * SQUARE_SIZE + SQUARE_SIZE // 2
                cy = BOARD_MARGIN + (7 - tr) * SQUARE_SIZE + SQUARE_SIZE // 2
                pg.draw.circle(self.surface, MOVE_HINT, (cx, cy), 8)

        # Pieces
        for square, piece in board.piece_map().items():
            is_white = piece.color == chess.WHITE
            surf = self.piece_surfaces[(is_white, piece.piece_type)]
            fx = chess.square_file(square)
            fr = chess.square_rank(square)
            x = BOARD_MARGIN + fx * SQUARE_SIZE
            y = BOARD_MARGIN + (7 - fr) * SQUARE_SIZE
            self.surface.blit(surf, (x, y))

        # Coordinates
        self._draw_coords()

    def _draw_wood_frame(self):
        # Outer frame with gradient-like border
        pg.draw.rect(self.surface, BORDER_DARK, (BOARD_MARGIN - 18, BOARD_MARGIN - 18, BOARD_SIZE + 36, BOARD_SIZE + 36), border_radius=10)
        pg.draw.rect(self.surface, BORDER_LIGHT, (BOARD_MARGIN - 12, BOARD_MARGIN - 12, BOARD_SIZE + 24, BOARD_SIZE + 24), border_radius=8)
        pg.draw.rect(self.surface, (90, 60, 30), (BOARD_MARGIN - 6, BOARD_MARGIN - 6, BOARD_SIZE + 12, BOARD_SIZE + 12), border_radius=6)

    def _draw_coords(self):
        font = pg.font.SysFont("DejaVu Sans", 16, bold=True)
        for file in range(8):
            ch = chr(ord('a') + file)
            x = BOARD_MARGIN + file * SQUARE_SIZE + 4
            y = BOARD_MARGIN + BOARD_SIZE + 6
            text = font.render(ch, True, (30, 30, 30))
            self.surface.blit(text, (x, y))
        for rank in range(8):
            ch = str(rank + 1)
            x = BOARD_MARGIN - 18
            y = BOARD_MARGIN + (7 - rank) * SQUARE_SIZE + 4
            text = font.render(ch, True, (30, 30, 30))
            self.surface.blit(text, (x, y))

    def _draw_piece(self, surf: pg.Surface, is_white: bool, piece_type: chess.PieceType) -> None:
        surf.fill((0, 0, 0, 0))
        center = (SQUARE_SIZE // 2, SQUARE_SIZE // 2)
        radius = int(SQUARE_SIZE * 0.38 * PIECE_SCALE)
        main = WHITE_PIECE if is_white else BLACK_PIECE
        shade = WHITE_SHADE if is_white else BLACK_SHADE
        edge = EDGE_STROKE

        def base_pedestal():
            w = int(SQUARE_SIZE * 0.70 * PIECE_SCALE)
            h = int(SQUARE_SIZE * 0.16 * PIECE_SCALE)
            rect = pg.Rect(0, 0, w, h)
            rect.center = (center[0], int(SQUARE_SIZE * (0.82)))
            pg.draw.ellipse(surf, shade, rect)
            pg.draw.ellipse(surf, edge, rect, width=2)

        def crown_dot():
            pg.draw.circle(surf, (255, 255, 255, 40), (center[0] - radius//2, center[1] - radius//2), radius//3)

        if piece_type == chess.PAWN:
            base_pedestal()
            head_center = (center[0], int(SQUARE_SIZE * 0.45))
            pg.draw.circle(surf, main, head_center, int(radius * 0.75))
            pg.draw.circle(surf, edge, head_center, int(radius * 0.75), width=2)
            neck_rect = pg.Rect(0, 0, int(radius * 1.3), int(radius * 0.9))
            neck_rect.center = (center[0], int(SQUARE_SIZE * 0.62))
            pg.draw.ellipse(surf, main, neck_rect)
            pg.draw.ellipse(surf, edge, neck_rect, width=2)
            crown_dot()
            return

        if piece_type == chess.KNIGHT:
            base_pedestal()
            # Stylized horse head silhouette
            points = [
                (center[0] - radius, int(SQUARE_SIZE * 0.70)),
                (center[0] - int(radius*0.4), int(SQUARE_SIZE * 0.50)),
                (center[0] + int(radius*0.2), int(SQUARE_SIZE * 0.38)),
                (center[0] + int(radius*0.5), int(SQUARE_SIZE * 0.32)),
                (center[0] + int(radius*0.1), int(SQUARE_SIZE * 0.48)),
                (center[0] + int(radius*0.2), int(SQUARE_SIZE * 0.64)),
                (center[0] - radius, int(SQUARE_SIZE * 0.70)),
            ]
            pg.draw.polygon(surf, main, points)
            pg.draw.lines(surf, edge, False, points, 2)
            eye = (center[0], int(SQUARE_SIZE * 0.42))
            pg.draw.circle(surf, (220, 220, 220) if is_white else (200, 200, 200), eye, 2)
            return

        if piece_type == chess.BISHOP:
            base_pedestal()
            body_rect = pg.Rect(0, 0, int(radius*1.6), int(radius*2.2))
            body_rect.center = (center[0], int(SQUARE_SIZE * 0.56))
            pg.draw.ellipse(surf, main, body_rect)
            pg.draw.ellipse(surf, edge, body_rect, 2)
            slit_start = (center[0], int(SQUARE_SIZE * 0.44))
            slit_end = (center[0], int(SQUARE_SIZE * 0.64))
            pg.draw.line(surf, (230, 230, 230) if is_white else (200, 200, 200), slit_start, slit_end, 2)
            crown_dot()
            return

        if piece_type == chess.ROOK:
            base_pedestal()
            tower_rect = pg.Rect(0, 0, int(radius*1.7), int(radius*1.7))
            tower_rect.center = (center[0], int(SQUARE_SIZE * 0.54))
            pg.draw.rect(surf, main, tower_rect, border_radius=6)
            pg.draw.rect(surf, edge, tower_rect, 2, border_radius=6)
            battlement_y = tower_rect.top - int(radius*0.25)
            step = tower_rect.width // 4
            for i in range(4):
                br = pg.Rect(tower_rect.left + i*step + 2, battlement_y, step - 4, int(radius*0.3))
                pg.draw.rect(surf, main, br)
                pg.draw.rect(surf, edge, br, 2)
            return

        if piece_type == chess.QUEEN:
            base_pedestal()
            body_rect = pg.Rect(0, 0, int(radius*1.8), int(radius*2.0))
            body_rect.center = (center[0], int(SQUARE_SIZE * 0.58))
            pg.draw.ellipse(surf, main, body_rect)
            pg.draw.ellipse(surf, edge, body_rect, 2)
            # Crown
            crown_points = [
                (body_rect.left, body_rect.top),
                (center[0] - int(radius*0.5), body_rect.top - int(radius*0.4)),
                (center[0], body_rect.top - int(radius*0.2)),
                (center[0] + int(radius*0.5), body_rect.top - int(radius*0.4)),
                (body_rect.right, body_rect.top),
            ]
            pg.draw.polygon(surf, main, crown_points)
            pg.draw.lines(surf, edge, False, crown_points, 2)
            crown_dot()
            return

        if piece_type == chess.KING:
            base_pedestal()
            body_rect = pg.Rect(0, 0, int(radius*1.7), int(radius*2.1))
            body_rect.center = (center[0], int(SQUARE_SIZE * 0.58))
            pg.draw.ellipse(surf, main, body_rect)
            pg.draw.ellipse(surf, edge, body_rect, 2)
            # Cross
            cx, cy = body_rect.topright[0] - body_rect.width//2, body_rect.top - int(radius*0.25)
            pg.draw.rect(surf, main, (cx - 2, cy - int(radius*0.5), 4, int(radius*1.0)))
            pg.draw.rect(surf, main, (cx - int(radius*0.4), cy - 2, int(radius*0.8), 4))
            pg.draw.rect(surf, edge, (cx - 2, cy - int(radius*0.5), 4, int(radius*1.0)), 1)
            pg.draw.rect(surf, edge, (cx - int(radius*0.4), cy - 2, int(radius*0.8), 4), 1)
            crown_dot()
            return

class ChessAI:
    def __init__(self, max_depth: int = 3, time_limit_s: float = 3.0):
        self.max_depth = max_depth
        self.time_limit_s = time_limit_s
        self.stop_time = 0.0

    def choose_move(self, board: chess.Board) -> Optional[chess.Move]:
        self.stop_time = time.time() + self.time_limit_s
        best_move = None
        best_score = -math.inf if board.turn == chess.WHITE else math.inf
        # Iterative deepening
        for depth in range(1, self.max_depth + 1):
            score, move = self._search(board, depth, -math.inf, math.inf, 0)
            if move is not None:
                best_move = move
                best_score = score
            if time.time() > self.stop_time:
                break
        return best_move

    def _search(self, board: chess.Board, depth: int, alpha: float, beta: float, ply: int) -> Tuple[float, Optional[chess.Move]]:
        if time.time() > self.stop_time:
            return self._evaluate(board), None
        if depth == 0 or board.is_game_over():
            return self._evaluate(board), None

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return self._evaluate(board), None

        # Simple move ordering: captures first
        def move_key(m: chess.Move):
            return 1 if board.is_capture(m) else 0
        legal_moves.sort(key=move_key, reverse=True)

        best_move = None
        if board.turn == chess.WHITE:
            value = -math.inf
            for move in legal_moves:
                board.push(move)
                score, _ = self._search(board, depth - 1, alpha, beta, ply + 1)
                board.pop()
                if score > value:
                    value = score
                    best_move = move
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value, best_move
        else:
            value = math.inf
            for move in legal_moves:
                board.push(move)
                score, _ = self._search(board, depth - 1, alpha, beta, ply + 1)
                board.pop()
                if score < value:
                    value = score
                    best_move = move
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value, best_move

    def _evaluate(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return 100000.0 if board.turn == chess.BLACK else -100000.0
        if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
            return 0.0
        material = self._material_count(board)
        mobility = 0.1 * (len(list(board.legal_moves)) if not board.is_game_over() else 0)
        return material + (mobility if board.turn == chess.WHITE else -mobility)

    @staticmethod
    def _material_count(board: chess.Board) -> float:
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }
        score = 0
        for piece_type in values:
            score += values[piece_type] * (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK)))
        return float(score)

class Game:
    def __init__(self):
        pg.init()
        pg.display.set_caption("Pygame Chess - Human/AI")
        self.screen = pg.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        self.clock = pg.time.Clock()
        self.board = chess.Board()
        self.renderer = BoardRenderer(self.screen)
        self.player_mode = PlayerMode()
        self.ai_white = ChessAI(max_depth=self.player_mode.ai_depth)
        self.ai_black = ChessAI(max_depth=self.player_mode.ai_depth)
        self.selected_square: Optional[chess.Square] = None
        self.legal_targets_for_selected: set[chess.Square] = set()
        self.status_font = pg.font.SysFont("DejaVu Sans", 18, bold=True)
        self.ai_thinking = False
        self.ai_thread: Optional[threading.Thread] = None
        self.pending_ai_move: Optional[chess.Move] = None

    def reset(self):
        self.board.reset()
        self.selected_square = None
        self.legal_targets_for_selected.clear()
        self.pending_ai_move = None
        self.ai_thinking = False

    def handle_mouse(self, pos):
        file = (pos[0] - BOARD_MARGIN) // SQUARE_SIZE
        rank = 7 - ((pos[1] - BOARD_MARGIN) // SQUARE_SIZE)
        if 0 <= file < 8 and 0 <= rank < 8:
            square = chess.square(file, rank)
            if self.selected_square is None:
                piece = self.board.piece_at(square)
                if piece and piece.color == self.board.turn and self._is_human_to_move():
                    self.selected_square = square
                    self.legal_targets_for_selected = {m.to_square for m in self.board.legal_moves if m.from_square == square}
            else:
                move = chess.Move(self.selected_square, square)
                # Handle promotion
                if chess.square_rank(self.selected_square) in (6, 1) and chess.square_rank(square) in (7, 0):
                    if self.board.piece_at(self.selected_square).piece_type == chess.PAWN:
                        move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)
                if move in self.board.legal_moves:
                    self.board.push(move)
                self.selected_square = None
                self.legal_targets_for_selected.clear()

    def _is_human_to_move(self) -> bool:
        return (self.board.turn == chess.WHITE and self.player_mode.white_is_human) or (
            self.board.turn == chess.BLACK and self.player_mode.black_is_human
        )

    def _is_ai_to_move(self) -> bool:
        return not self._is_human_to_move()

    def _kick_ai_if_needed(self):
        if self.ai_thinking or not self._is_ai_to_move() or self.board.is_game_over():
            return
        self.ai_thinking = True
        ai = self.ai_white if self.board.turn == chess.WHITE else self.ai_black
        def think():
            move = ai.choose_move(self.board.copy(stack=False))
            self.pending_ai_move = move
            self.ai_thinking = False
        self.ai_thread = threading.Thread(target=think, daemon=True)
        self.ai_thread.start()

    def _apply_pending_ai_move(self):
        if self.pending_ai_move is not None and not self.board.is_game_over():
            if self.pending_ai_move in self.board.legal_moves:
                self.board.push(self.pending_ai_move)
            self.pending_ai_move = None

    def _draw_status(self):
        status = []
        status.append(f"Turn: {'White' if self.board.turn == chess.WHITE else 'Black'}")
        pm = self.player_mode
        status.append(f"White: {'Human' if pm.white_is_human else 'AI'}  Black: {'Human' if pm.black_is_human else 'AI'}  Depth: {pm.ai_depth}")
        if self.board.is_game_over():
            if self.board.is_checkmate():
                status.append(f"Checkmate! Winner: {'Black' if self.board.turn == chess.WHITE else 'White'}")
            else:
                status.append("Draw")
        if self.ai_thinking:
            status.append("AI thinking...")
        text = " | ".join(status)
        text_surf = self.status_font.render(text, True, (20, 20, 20))
        self.screen.blit(text_surf, (BOARD_MARGIN - 6, 4))

    def run(self):
        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        running = False
                    elif event.key == pg.K_r:
                        self.reset()
                    elif event.key == pg.K_u and self.board.move_stack:
                        self.board.pop()
                        self.selected_square = None
                        self.legal_targets_for_selected.clear()
                    elif event.key == pg.K_h:
                        self.player_mode.white_is_human = not self.player_mode.white_is_human
                    elif event.key == pg.K_j:
                        self.player_mode.black_is_human = not self.player_mode.black_is_human
                    elif event.key == pg.K_a:
                        # quick toggle: side to move AI
                        if self._is_human_to_move():
                            if self.board.turn == chess.WHITE:
                                self.player_mode.white_is_human = False
                            else:
                                self.player_mode.black_is_human = False
                    elif event.key in (pg.K_PLUS, pg.K_EQUALS):
                        self.player_mode.ai_depth = min(5, self.player_mode.ai_depth + 1)
                        self.ai_white.max_depth = self.player_mode.ai_depth
                        self.ai_black.max_depth = self.player_mode.ai_depth
                    elif event.key in (pg.K_MINUS, pg.K_UNDERSCORE):
                        self.player_mode.ai_depth = max(1, self.player_mode.ai_depth - 1)
                        self.ai_white.max_depth = self.player_mode.ai_depth
                        self.ai_black.max_depth = self.player_mode.ai_depth
                    elif event.key in (pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5):
                        self.player_mode.ai_depth = int(event.unicode)
                        self.ai_white.max_depth = self.player_mode.ai_depth
                        self.ai_black.max_depth = self.player_mode.ai_depth
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if self._is_human_to_move() and not self.board.is_game_over():
                        self.handle_mouse(event.pos)

            # AI move management
            self._kick_ai_if_needed()
            self._apply_pending_ai_move()

            # Rendering
            self.screen.fill((230, 220, 200))
            self.renderer.draw_board(self.board, self.selected_square, self.legal_targets_for_selected)
            self._draw_status()

            pg.display.flip()
            self.clock.tick(FPS)
        pg.quit()

if __name__ == "__main__":
    Game().run()