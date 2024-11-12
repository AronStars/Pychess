import pygame
import sys
import sqlite3
import datetime


# Initialize Pygame modules
pygame.init()
pygame.font.init()

# Set up the display window dimensions
screen_width, screen_height = (800, 800)
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
pygame.display.set_caption("Chess")

# Create or connect to a database
conn = sqlite3.connect('game_history.db')
c = conn.cursor()

# Create the table to store game results if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS game_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        winner TEXT,
        loser TEXT,
        timestamp TEXT
    )
''')
conn.commit()


def generate_game_id():
    # Generate a unique game ID by finding the maximum existing ID and adding 1
    c.execute('SELECT MAX(id) FROM game_results')
    result = c.fetchone()
    if result[0] is None:
        return 1  # No existing entries, start with ID 1
    else:
        return result[0] + 1

def get_current_timestamp():
    return str(datetime.datetime.now())


def save_game_result(game_id, winner, loser, timestamp):
    c.execute('INSERT INTO game_results (id, winner, loser, timestamp) VALUES (?, ?, ?, ?)', (game_id, winner, loser, timestamp))
    conn.commit()


def save_simple_result(currentplayer, opponentplayer):
    # Generate the necessary parameters for save_game_result
    game_id = generate_game_id()  # Generate a unique game ID
    timestamp = get_current_timestamp()  # Get the current timestamp

    # Call the original save_game_result function with all required parameters
    save_game_result(game_id, currentplayer, opponentplayer,  timestamp)

# Move these variables to the module level
promotion_pending = False  # Flag to indicate if a pawn promotion is pending
promoting_pawn = None      # Reference to the pawn being promoted

# Load the piece images
Blackpieces = [
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_Pawn.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_Rook.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_Knight.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_Bishop.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_Queen.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\Black_King.svg')
]

Whitepieces = [
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_Pawn.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_Rook.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_Knight.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_Bishop.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_Queen.svg'),
    pygame.image.load(r'C:\Users\arong\OneDrive\Desktop\Computer Science\Project\Game\Images\White_King.svg')
]


# noinspection PyUnresolvedReferences,PyTypeChecker
def startgame(auto_promotes):
    global promotion_pending, promoting_pawn  # Declare globals
    en_passant_target = None  # Variable to track en passant target square

    # Set up the board
    board_size = 8  # Chessboard is 8x8 squares
    square_size = screen_width // board_size  # Size of each square on the board
    board_colors = [pygame.Color("lightgrey"), pygame.Color("azure4")]  # Colors for the squares
    board = [[None for _ in range(board_size)] for _ in range(board_size)]  # Initialize empty board
    
    # Font for displaying messages
    message_font = pygame.font.SysFont(None, 36)

    # Keep track of the current player ('white' or 'black')
    current_player = 'white'
    selected_piece = None  # The piece currently selected by the player
    valid_moves = []  # List of valid moves for the selected piece

    game_over = False  # Flag to indicate if the game has ended
    check_status = False  # Flag to indicate if the current player is in check

    # noinspection PyShadowingNames
    class Piece:
        # Base class for all chess pieces.
        def __init__(self, color, position, image):
            self.color = color  # 'white' or 'black'
            self.position = position  # Tuple (row, col)
            self.image = image  # Image of the piece

        def move(self, new_position):
            self.position = new_position  # Update the piece's position

        def get_valid_moves(self, board):
            # Return a list of valid moves for this piece.
            raise NotImplementedError("This method should be overridden in each piece subclass.")

    class King(Piece):
        # Class representing the King piece.
        def __init__(self, color, position, symbol):
            super().__init__(color, position, symbol)
            self.has_moved = False  # To track if the king has moved (for castling)

        def move(self, new_position):
            # Update the king's position and set has_moved to True.
            super().move(new_position)
            self.has_moved = True


        def get_valid_moves(self, board):
            row, col = self.position
            # Possible directions the King can move (one square in any direction)
            directions = [(-1, -1), (-1, 0), (-1, 1),
                          (0, -1),          (0, 1),
                          (1, -1),  (1, 0),  (1, 1)]
            moves = []
            for delta_row, delta_col in directions:
                new_row, new_col = row + delta_row, col + delta_col
                # Check if new position is within the board limits
                if 0 <= new_row < board_size and 0 <= new_col < board_size:
                    target_piece = board[new_row][new_col]
                    # Check if the target square is empty or has an opponent's piece
                    if target_piece is None or target_piece.color != self.color:
                        moves.append((new_row, new_col))

            # Castling moves
            if not self.has_moved and not is_square_under_attack(row, col, self.color, board):
                # King-side castling
                if self.can_castle_short(board):
                    moves.append((row, col + 2))
                # Queen-side castling
                if self.can_castle_long(board):
                    moves.append((row, col - 2))

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)

            return valid_moves

        def can_castle_short(self, board):
            # Check if short (king-side) castling is possible.
            row, col = self.position
            rook_col = 7
            # Check if the squares between king and rook are empty
            if all(board[row][col_index] is None for col_index in range(col + 1, rook_col)):
                rook = board[row][rook_col]
                if isinstance(rook, Rook) and rook.color == self.color and not rook.has_moved:
                    # Ensure squares king passes through are not under attack
                    for col_index in range(col + 1, col + 3):
                        if is_square_under_attack(row, col_index, self.color, board):
                            return False
                    return True
            return False

        def can_castle_long(self, board):
            # Check if long (queen-side) castling is possible.
            row, col = self.position
            rook_col = 0
            # Check if the squares between king and rook are empty
            if all(board[row][col_index] is None for col_index in range(rook_col + 1, col)):
                rook = board[row][rook_col]
                if isinstance(rook, Rook) and rook.color == self.color and not rook.has_moved:
                    # Ensure squares king passes through are not under attack
                    for col_index in range(col - 2, col):
                        if is_square_under_attack(row, col_index, self.color, board):
                            return False
                    return True
            return False

    class Queen(Piece):
        # Class representing the Queen piece.
        def get_valid_moves(self, board):
            row, col = self.position
            # Possible directions the Queen can move (any number of squares in any direction)
            directions = [(-1, -1), (-1, 0), (-1, 1),
                          (0, -1),          (0, 1),
                          (1, -1),  (1, 0),  (1, 1)]
            moves = []
            for delta_row, delta_col in directions:
                new_row, new_col = row, col
                while True:
                    new_row += delta_row
                    new_col += delta_col
                    # Check if new position is within the board limits
                    if 0 <= new_row < board_size and 0 <= new_col < board_size:
                        target_piece = board[new_row][new_col]
                        if target_piece is None:
                            # The square is empty; add to valid moves
                            moves.append((new_row, new_col))
                        elif target_piece.color != self.color:
                            # The square has an opponent's piece; add to valid moves and stop in this direction
                            moves.append((new_row, new_col))
                            break
                        else:
                            # The square has a friendly piece; stop in this direction
                            break
                    else:
                        # Out of board bounds; stop in this direction
                        break

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)

            return valid_moves

    class Bishop(Piece):
        # Class representing the Bishop piece.
        def get_valid_moves(self, board):
            row, col = self.position
            # Possible directions the Bishop can move (diagonally any number of squares)
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            moves = []
            for delta_row, delta_col in directions:
                new_row, new_col = row, col
                while True:
                    new_row += delta_row
                    new_col += delta_col
                    # Check if new position is within the board limits
                    if 0 <= new_row < board_size and 0 <= new_col < board_size:
                        target_piece = board[new_row][new_col]
                        if target_piece is None:
                            moves.append((new_row, new_col))
                        elif target_piece.color != self.color:
                            moves.append((new_row, new_col))
                            break
                        else:
                            break
                    else:
                        break

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)
            return valid_moves

    class Knight(Piece):
        # Class representing the Knight piece.
        def get_valid_moves(self, board):
            row, col = self.position
            # Possible moves for the Knight (L-shaped moves)
            moves = [(-2, -1), (-2, 1),
                     (-1, -2), (-1, 2),
                     (1, -2),  (1, 2),
                     (2, -1),  (2, 1)]
            potential_moves = []
            for delta_row, delta_col in moves:
                new_row, new_col = row + delta_row, col + delta_col
                if 0 <= new_row < board_size and 0 <= new_col < board_size:
                    target_piece = board[new_row][new_col]
                    if target_piece is None or target_piece.color != self.color:
                        potential_moves.append((new_row, new_col))

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in potential_moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)

            return valid_moves

    class Rook(Piece):
        # Class representing the Rook piece.
        def __init__(self, color, position, symbol):
            super().__init__(color, position, symbol)
            self.has_moved = False  # To track if the rook has moved (for castling)

        def move(self, new_position):
            # Update the rook's position and set has_moved to True.
            super().move(new_position)
            self.has_moved = True

        def get_valid_moves(self, board):
            row, col = self.position
            # Possible directions the Rook can move (vertical and horizontal any number of squares)
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            moves = []
            for delta_row, delta_col in directions:
                new_row, new_col = row, col
                while True:
                    new_row += delta_row
                    new_col += delta_col
                    if 0 <= new_row < board_size and 0 <= new_col < board_size:
                        target_piece = board[new_row][new_col]
                        if target_piece is None:
                            moves.append((new_row, new_col))
                        elif target_piece.color != self.color:
                            moves.append((new_row, new_col))
                            break
                        else:
                            break
                    else:
                        break

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)
            return valid_moves

    class Pawn(Piece):
        # Class representing the Pawn piece.
        def get_valid_moves(self, board):
            row, col = self.position
            direction = -1 if self.color == 'white' else 1
            start_row = 6 if self.color == 'white' else 1
            moves = []

            # Move forward one square
            if 0 <= row + direction < board_size and board[row + direction][col] is None:
                moves.append((row + direction, col))
                # Move forward two squares from starting position
                if row == start_row and board[row + 2 * direction][col] is None:
                    moves.append((row + 2 * direction, col))

            # Capture diagonally and en passant
            for delta_col in [-1, 1]:
                new_row, new_col = row + direction, col + delta_col
                if 0 <= new_row < board_size and 0 <= new_col < board_size:
                    target_piece = board[new_row][new_col]
                    if target_piece is not None and target_piece.color != self.color:
                        moves.append((new_row, new_col))
                    # Check for en passant capture
                    elif en_passant_target == (new_row, new_col):
                        moves.append((new_row, new_col))

            # Filter out moves that would put the king in check
            valid_moves = []
            for move in moves:
                if not would_cause_check(self, move, board):
                    valid_moves.append(move)
            return valid_moves

        def move(self, new_position):
            # Move the pawn to a new position, and handle promotion if reaching the opposite end.
            super().move(new_position)
            row, col = self.position
            # Check for promotion
            if (self.color == 'white' and row == 0) or (self.color == 'black' and row == 7):
                # Use 'global' to modify module-level variables
                global promotion_pending, promoting_pawn
                promotion_pending = True
                promoting_pawn = self

    def is_square_under_attack(row, col, color, board):
        # Check if a square is under attack by any of the opponent's pieces.
        opponent_color = 'black' if color == 'white' else 'white'
        for row_index in range(board_size):
            for col_index in range(board_size):
                piece = board[row_index][col_index]
                if piece is not None and piece.color == opponent_color:
                    if isinstance(piece, King):
                        # King's moves are limited to one square
                        if abs(piece.position[0] - row) <= 1 and abs(piece.position[1] - col) <= 1:
                            return True
                    else:
                        if (row, col) in piece.get_potential_moves(board):
                            return True
        return False

    def would_cause_check(piece, move, board):
        # Determine if moving a piece to a new position would leave its own king in check.
        original_position = piece.position
        target_piece = board[move[0]][move[1]]

        # Temporarily make the move
        board[original_position[0]][original_position[1]] = None
        board[move[0]][move[1]] = piece
        piece.position = move

        in_check = is_in_check(piece.color, board)

        # Undo the move
        piece.position = original_position
        board[original_position[0]][original_position[1]] = piece
        board[move[0]][move[1]] = target_piece
        return in_check

    def is_in_check(color, board):
        # Check if the king of the given color is in check.
        for row in range(board_size):
            for col in range(board_size):
                piece = board[row][col]
                if isinstance(piece, King) and piece.color == color:
                    return is_square_under_attack(row, col, color, board)
        return False

    def is_checkmate(color, board):
        # Check if the player of the given color is in checkmate.
        if not is_in_check(color, board):
            return False
        # For each piece of the current player, check if there are any valid moves
        for row in range(board_size):
            for col in range(board_size):
                piece = board[row][col]
                if piece is not None and piece.color == color:
                    if piece.get_valid_moves(board):
                        return False
        return True

    def add_potential_moves_method():
        # Adds a get_potential_moves method to each piece class
        for cls in [King, Queen, Bishop, Knight, Rook, Pawn]:
            if cls == King:
                def get_potential_moves(self, board):
                    row, col = self.position
                    directions = [(-1, -1), (-1, 0), (-1, 1),
                                  (0, -1),          (0, 1),
                                  (1, -1),  (1, 0),  (1, 1)]
                    moves = []
                    for delta_row, delta_col in directions:
                        new_row, new_col = row + delta_row, col + delta_col
                        if 0 <= new_row < board_size and 0 <= new_col < board_size:
                            moves.append((new_row, new_col))
                    return moves
                cls.get_potential_moves = get_potential_moves
            elif cls == Knight:
                def get_potential_moves(self, board):
                    row, col = self.position
                    moves = [(-2, -1), (-2, 1),
                             (-1, -2), (-1, 2),
                             (1, -2),  (1, 2),
                             (2, -1),  (2, 1)]
                    potential_moves = []
                    for delta_row, delta_col in moves:
                        new_row, new_col = row + delta_row, col + delta_col
                        if 0 <= new_row < board_size and 0 <= new_col < board_size:
                            potential_moves.append((new_row, new_col))
                    return potential_moves
                cls.get_potential_moves = get_potential_moves
            elif cls == Pawn:
                def get_potential_moves(self, board):
                    row, col = self.position
                    direction = -1 if self.color == 'white' else 1
                    moves = []
                    # Capture diagonally
                    for delta_col in [-1, 1]:
                        new_row, new_col = row + direction, col + delta_col
                        if 0 <= new_row < board_size and 0 <= new_col < board_size:
                            moves.append((new_row, new_col))
                    # En passant target
                    if en_passant_target:
                        en_row, en_col = en_passant_target
                        if abs(en_col - col) == 1 and en_row - row == direction:
                            moves.append(en_passant_target)
                    return moves
                cls.get_potential_moves = get_potential_moves
            else:
                def get_potential_moves(self, board):
                    global directions
                    row, col = self.position
                    if isinstance(self, Bishop):
                        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                    elif isinstance(self, Rook):
                        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    elif isinstance(self, Queen):
                        directions = [(-1, -1), (-1, 0), (-1, 1),
                                      (0, -1),          (0, 1),
                                      (1, -1),  (1, 0),  (1, 1)]
                    moves = []
                    for delta_row, delta_col in directions:
                        new_row, new_col = row, col
                        while True:
                            new_row += delta_row
                            new_col += delta_col
                            if 0 <= new_row < board_size and 0 <= new_col < board_size:
                                moves.append((new_row, new_col))
                                if board[new_row][new_col] is not None:
                                    break
                            else:
                                break
                    return moves
                cls.get_potential_moves = get_potential_moves

    # Initialize the pieces on the board
    # noinspection PyTypeChecker
    def initialize_pieces():
        # Black pieces
        for col in range(board_size):
            board[1][col] = Pawn('black', (1, col), Blackpieces[0])
        board[0][0] = Rook('black', (0, 0), Blackpieces[1])
        # noinspection PyTypeChecker
        board[0][1] = Knight('black', (0, 1), Blackpieces[2])
        board[0][2] = Bishop('black', (0, 2), Blackpieces[3])
        board[0][3] = Queen('black', (0, 3), Blackpieces[4])
        board[0][4] = King('black', (0, 4), Blackpieces[5])
        board[0][5] = Bishop('black', (0, 5), Blackpieces[3])
        board[0][6] = Knight('black', (0, 6), Blackpieces[2])
        board[0][7] = Rook('black', (0, 7), Blackpieces[1])

        # White pieces
        for col in range(board_size):
            board[6][col] = Pawn('white', (6, col), Whitepieces[0])
        board[7][0] = Rook('white', (7, 0), Whitepieces[1])
        board[7][1] = Knight('white', (7, 1), Whitepieces[2])
        board[7][2] = Bishop('white', (7, 2), Whitepieces[3])
        board[7][3] = Queen('white', (7, 3), Whitepieces[4])
        board[7][4] = King('white', (7, 4), Whitepieces[5])
        board[7][5] = Bishop('white', (7, 5), Whitepieces[3])
        board[7][6] = Knight('white', (7, 6), Whitepieces[2])
        board[7][7] = Rook('white', (7, 7), Whitepieces[1])

    add_potential_moves_method()
    initialize_pieces()

    def get_square_color(row, col):
        # Return the color of the square at the given position.
        return board_colors[(row + col) % 2]

    # Game loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # User clicked the close button
                running = False
                pygame.quit()
                sys.exit()
            elif promotion_pending:
                row, col = promoting_pawn.position
                if auto_promotes:
                    board[row][col] = Queen(promoting_pawn.color, promoting_pawn.position,
                                            Whitepieces[4] if promoting_pawn.color == 'white' else Blackpieces[4])
                    promoting_pawn = None
                    promotion_pending = False
                    current_player = 'black' if current_player == 'white' else 'white'
                #Handle promotion choice
                elif event.type == pygame.KEYDOWN:
                    key = event.unicode.upper()
                    if key in ['Q', 'R', 'B', 'N']:
                        if key == 'Q':
                            board[row][col] = Queen(promoting_pawn.color, promoting_pawn.position,
                                                    Whitepieces[4] if promoting_pawn.color == 'white' else Blackpieces[4])
                        elif key == 'R':
                            board[row][col] = Rook(promoting_pawn.color, promoting_pawn.position,
                                                   Whitepieces[1] if promoting_pawn.color == 'white' else Blackpieces[1])
                        elif key == 'B':
                            board[row][col] = Bishop(promoting_pawn.color, promoting_pawn.position,
                                                     Whitepieces[3] if promoting_pawn.color == 'white' else Blackpieces[3])
                        elif key == 'N':
                            board[row][col] = Knight(promoting_pawn.color, promoting_pawn.position,
                                                     Whitepieces[2] if promoting_pawn.color == 'white' else Blackpieces[2])

                        promoting_pawn = None
                        promotion_pending = False
                        # Switch turns after promotion
                        current_player = 'black' if current_player == 'white' else 'white'
                        opponent_player = 'black' if current_player == 'white' else 'white'
                        # Check for check or checkmate after promotion
                        if is_checkmate(current_player, board):
                            game_over = True
                            save_simple_result(opponent_player, current_player)
                            break
                        else:
                            check_status = is_in_check(current_player, board)
            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over and not promotion_pending:
                # Handle mouse click event
                mouse_pos = pygame.mouse.get_pos()
                clicked_row = mouse_pos[1] // square_size
                clicked_col = mouse_pos[0] // square_size

                if 0 <= clicked_row < board_size and 0 <= clicked_col < board_size:
                    clicked_piece = board[clicked_row][clicked_col]
                    if selected_piece is None:
                        # No piece selected yet
                        if clicked_piece is not None and clicked_piece.color == current_player:
                            # Select the piece
                            selected_piece = clicked_piece
                            valid_moves = selected_piece.get_valid_moves(board)
                            if not valid_moves:
                                selected_piece = None  # Deselect if no valid moves
                    else:
                        # A piece is already selected
                        if (clicked_row, clicked_col) in valid_moves:
                            # Special handling for castling
                            if isinstance(selected_piece, King) and abs(selected_piece.position[1] - clicked_col) == 2:
                                # Determine the direction of castling
                                if clicked_col > selected_piece.position[1]:
                                    # King-side castling
                                    rook_col = 7
                                    new_rook_col = clicked_col - 1
                                else:
                                    # Queen-side castling
                                    rook_col = 0
                                    new_rook_col = clicked_col + 1
                                # Move the rook
                                rook = board[selected_piece.position[0]][rook_col]
                                board[selected_piece.position[0]][rook_col] = None
                                rook.move((selected_piece.position[0], new_rook_col))
                                board[selected_piece.position[0]][new_rook_col] = rook

                            # Move the selected piece to the clicked square
                            old_row, old_col = selected_piece.position
                            board[old_row][old_col] = None  # Remove piece from old position

                            # Check for en passant capture
                            if isinstance(selected_piece, Pawn):
                                if (clicked_row, clicked_col) == en_passant_target:
                                    # En passant capture
                                    capture_row = clicked_row + (1 if selected_piece.color == 'white' else -1)
                                    board[capture_row][clicked_col] = None  # Remove the opponent's pawn

                            # Capture opponent's piece if present
                            if board[clicked_row][clicked_col] is not None:
                                board[clicked_row][clicked_col] = None

                            # Update piece position
                            selected_piece.move((clicked_row, clicked_col))
                            board[clicked_row][clicked_col] = selected_piece

                            # After moving, reset en passant target
                            en_passant_target = None

                            # If pawn moved two squares, set en passant target
                            if isinstance(selected_piece, Pawn) and abs(clicked_row - old_row) == 2:
                                en_passant_target = ((old_row + clicked_row) // 2, clicked_col)
                            else:
                                en_passant_target = None

                            # Reset selection
                            selected_piece = None
                            valid_moves = []

                            # If promotion is pending, don't switch turns yet
                            if not promotion_pending:
                                # Switch turns
                                current_player = 'black' if current_player == 'white' else 'white'
                                opponent_player = 'black' if current_player == 'white' else 'white'
                                # Check if the next player is in check or checkmate
                                if is_checkmate(current_player, board):
                                    game_over = True
                                    save_simple_result(opponent_player, current_player)
                                else:
                                    check_status = is_in_check(current_player, board)
                        elif clicked_piece is not None and clicked_piece.color == current_player:
                            # Select a different piece of the current player
                            selected_piece = clicked_piece
                            valid_moves = selected_piece.get_valid_moves(board)
                            if not valid_moves:
                                selected_piece = None  # Deselect if no valid moves
                        else:
                            # Deselect the piece
                            selected_piece = None
                            valid_moves = []

        # Clear the screen
        screen.fill(pygame.Color("white"))
    
        # Draw the board and pieces
        for row in range(board_size):
            for col in range(board_size):
                # Draw the square
                square_color = get_square_color(row, col)
                square_rect = pygame.Rect(col * square_size, row * square_size, square_size, square_size)
                pygame.draw.rect(screen, square_color, square_rect)

                # Highlight valid moves
                if selected_piece is not None and (row, col) in valid_moves:
                    # Draw a green circle on squares that are valid moves
                    pygame.draw.circle(screen, pygame.Color('green'),
                                       (col * square_size + square_size // 2, row * square_size + square_size // 2),
                                       square_size // 6)

                # Highlight selected piece
                if selected_piece is not None and selected_piece.position == (row, col):
                    # Draw a yellow border around the selected piece
                    pygame.draw.rect(screen, pygame.Color('yellow'), square_rect, 3)

                # Draw the piece if there is one
                piece = board[row][col]
                if piece is not None:
                    # Scale the piece image to fit in the square
                    scaled_image = pygame.transform.scale(piece.image, (square_size -1  , square_size ))
                    screen.blit(scaled_image, square_rect.topleft)

        # Display check or checkmate message
        if game_over:
            message = f"Checkmate! { 'Black' if current_player == 'white' else 'White' } wins!"
            text_surface = message_font.render(message, True, pygame.Color('red'))
            text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(text_surface, text_rect)
        elif check_status:
            message = "Check!"
            text_surface = message_font.render(message, True, pygame.Color('red'))
            screen.blit(text_surface, (10, 10))

        # Display promotion message
        if promotion_pending:
            message = f"Promote pawn to (Q)ueen, (R)ook, (B)ishop, or K(N)ight?"
            text_surface = message_font.render(message, True, pygame.Color('blue'))
            text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(text_surface, text_rect)

        # Update the display
        pygame.display.flip()
    # Quit the game
    pygame.quit()

def settings_menu():
    global auto_promote
    auto_promote = True

    button_width, button_height = 200, 50
    font = pygame.font.Font(None, 36)

    text = font.render("Settings Menu", True, (0, 0, 0))
    text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
    screen.blit(text, text_rect)

    auto_queen_rect = pygame.Rect(
        (screen.get_width() // 2 - button_width // 2, screen.get_height() // 2 - 10), (button_width, button_height)
    )

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if auto_queen_rect.collidepoint(mouse_pos):
                    auto_promote = not auto_promote
            elif event.type == pygame.KEYDOWN:
                return

        screen.fill((255, 255, 255))  # Clear screen.
        screen.blit(text, text_rect)  # Redraw the settings menu title.

        # Update and render the button text
        if auto_promote:
            auto_queen_button_text = font.render("Auto Queen", True, (0, 255, 0))
        else:
            auto_queen_button_text = font.render("Manual Queen", True, (255, 0, 0))

        pygame.draw.rect(screen, (200, 200, 200), auto_queen_rect)
        screen.blit(
            auto_queen_button_text,
            (auto_queen_rect.x + (button_width - auto_queen_button_text.get_width()) // 2,
             auto_queen_rect.y + (button_height - auto_queen_button_text.get_height()) // 2)
        )

        pygame.display.flip()


def game_history():
    # Fill the screen with white color
    screen.fill((255, 255, 255))
    # Set the font and render the "Previous games" text
    font = pygame.font.Font(None, 36)
    text = font.render("Previous games", True, (0, 0, 0))
    text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
    screen.blit(text, text_rect)

    # Fetch and display past game results
    c.execute('SELECT winner, loser, timestamp FROM game_results')
    game_results = c.fetchall()
    y_offset = 50
    for result in game_results:
        winner, loser, timestamp = result
        result_text = f"Winner: {winner}, Loser: {loser}, Time: {timestamp}"
        result_render = font.render(result_text, True, (0, 0, 0))
        screen.blit(result_render, (50, screen.get_height() // 2 - 50 + y_offset))
        y_offset += 40

    pygame.display.flip()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Quit the game if the user closes the window
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                # Return to the main menu if any key is pressed
                return

def main_menu():
    # Fill the screen with white color
    screen.fill((255, 255, 255))
    # Set the font and button dimensions
    font = pygame.font.Font(None, 36)
    button_width, button_height = 200, 50
    # Define the rectangles for the buttons
    start_button_rect = pygame.Rect((screen.get_width() // 2 - button_width // 2, screen.get_height() // 2 - 60), (button_width, button_height))
    settings_button_rect = pygame.Rect((screen.get_width() // 2 - button_width // 2, screen.get_height() // 2 + 10), (button_width, button_height))
    history_button_rect = pygame.Rect((screen.get_width() // 2 - button_width // 2, screen.get_height() // 2 + 80), (button_width, button_height))
    # Render the button texts
    start_text = font.render("Start Game", True, (0, 0, 0))
    settings_text = font.render("Settings", True, (0, 0, 0))
    history_text = font.render("History", True, (0, 0, 0))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Quit the game if the user closes the window
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Get the mouse position
                mouse_pos = event.pos
                # Check if the start button is clicked
                if start_button_rect.collidepoint(mouse_pos):
                    startgame(auto_promote)
                    return
                # Check if the settings button is clicked
                elif settings_button_rect.collidepoint(mouse_pos):
                    settings_menu()
                    screen.fill((255, 255, 255))
                    break
                elif history_button_rect.collidepoint(mouse_pos):
                    game_history()
                    screen.fill((255, 255, 255))
                    break
        # Draw the buttons
        pygame.draw.rect(screen, (200, 200, 200), start_button_rect)
        pygame.draw.rect(screen, (200, 200, 200), settings_button_rect)
        pygame.draw.rect(screen, (200, 200, 200), history_button_rect)
        # Draw the button texts
        screen.blit(start_text, (start_button_rect.x + (button_width - start_text.get_width()) // 2, start_button_rect.y + (button_height - start_text.get_height()) // 2))
        screen.blit(settings_text, (settings_button_rect.x + (button_width - settings_text.get_width()) // 2, settings_button_rect.y + (button_height - settings_text.get_height()) // 2))
        screen.blit(history_text, (history_button_rect.x + (button_width - history_text.get_width()) // 2, history_button_rect.y + (button_height - history_text.get_height()) // 2))
        pygame.display.flip()

# Start the main menu
main_menu()
#fin