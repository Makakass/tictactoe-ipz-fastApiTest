def init_board():
    # create empty board
    return [
        None, None, None,
        None, None, None,
        None, None, None,
    ]


def is_draw(board):
    # checks if a draw
    for cell in board:
        if not cell:
            return False
    return True


def if_won(board):
    # check if some player has just won the game
    if board[0] == board[1] == board[2] is not None or \
            board[3] == board[4] == board[5] is not None or \
            board[6] == board[7] == board[8] is not None or \
            board[0] == board[3] == board[6] is not None or \
            board[1] == board[4] == board[7] is not None or \
            board[2] == board[5] == board[8] is not None or \
            board[0] == board[4] == board[8] is not None or \
            board[6] == board[4] == board[2] is not None:
        return True
    return False
