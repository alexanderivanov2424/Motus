import numpy as np
import os

import threading
import queue
import time
from msvcrt import getch
"""
2-player
1-vs AI

ring can be places in first or last 2 rows
powerup only in first 2? or 3 rows
piece can only be bought into first row

piece costs 1, ring costs 4, powerup is 4 for 1, 6 for 2 and 8 for 3

**cannot buy after moving**
"""
class Motus:
    def __init__(self):
        self.board = np.zeros((8,8))
        self.board_rings = np.zeros((8,8))

        self.piece_dict = {0:" ", -1:"o", -2:"U", 1:"x", 2:"H"}
        self.ring_dict = {0:(" "," "), -1:("(",")"), 1:("[","]")}

        self.rings = 4

        self.p1_score = 0
        self.p2_score = 0

        self.p1_power = 0
        self.p1_peices = 0
        self.p1_powerups = 0
        self.p1_rings = 0
        self.p1_peices_to_buy = 3
        self.p1_powerups_to_buy = 4

        self.p2_power = 1 #start with 1 extra power because second
        self.p2_peices = 0
        self.p2_rings = 0
        self.p2_powerups = 0
        self.p2_peices_to_buy = 3
        self.p2_powerups_to_buy = 4

        self.board[0,:] = -1
        self.board[-1,:] = 1

        # (area, arg1, arg2)   board needs x,y but owned and to buy only need 1
        #0 - board 1 - owned  2 - to buy 3 - score
        self.cursor = [0, 0, 0]
        self.selection = None
        self.mode = None #move, place,

        #turn related data
        self.player = 1
        self.has_bought_powerup = False # need this to adjust cost
        self.moved_piece = None #None or board loc | once moved ends buy phase
        self.moves_done = False # need this if normal piece moves while other poweredup piece attacks
        self.turn_done = False
        self.placed_in_turn_list = [] #can't move pieces powered up same turn

        self.error = ""

    def next_turn(self):
        Done = self.turn_done
        if self.player == 1:
            Done = Done or np.sum(self.board == 2) == 0 and self.moves_done
        else:
            Done = Done or np.sum(self.board == -2) == 0 and self.moves_done
        if Done:
            for c in range(8):
                if self.player == 1 and self.board[0][c] > 0:
                    if self.board[0][c] == 2:
                        self.p1_powerups_to_buy += 1
                    self.board[0][c] = 0
                    self.p1_power += 2
                    self.p1_score += 1
                elif self.board[7][c] < 0:
                    if self.board[7][c] == -2:
                        self.p2_powerups_to_buy += 1
                    self.board[7][c] = 0
                    self.p2_power += 2
                    self.p2_score += 1
            if self.player == 1:
                self.p1_power += 1
            else:
                self.p2_power += 1
            self.reset_turn()
            self.player = 2 if self.player == 1 else 1


    def reset_turn(self):
        self.has_bought_powerup = False
        self.moved_piece = None #None or board loc
        self.moves_done = False
        self.turn_done = False
        self.placed_in_turn_list = []

    def make_move(self, start, end):
        if self.board[start[0]][start[1]] == 0:
            self.error = "not a piece"
            return #invalid not a piece
        if self.player == 1 and self.board[start[0]][start[1]] < 0:
            self.error = "mv opp"
            return #invalid can't move opponent piece
        if not self.player == 1 and self.board[start[0]][start[1]] > 0:
            self.error = "mv opp"
            return #invalid can't move opponent piece
        if self.player == 1 and self.board[end[0]][end[1]] > 0:
            self.error = "land on own"
            return #invalid cant move onto own piece
        if not self.player == 1 and self.board[end[0]][end[1]] < 0:
            self.error = "land on own"
            return #invalid cant move onto own piece
        if start[0] == end[0] and start[1] == end[1]:
            self.error = "didn't move"
            return #invalid
        for loc in self.placed_in_turn_list:
            if loc[0] == start[0] and loc[1] == start[1]:
                self.error = "mv p-up same turn"
                return
        shift_r = abs(end[0] - start[0])
        shift_c = abs(end[1] - start[1])
        if shift_r > 2:
            self.error = "too far"
            return #invalid
        if shift_c > 2:
            self.error = "too far"
            return #invalid
        if not shift_r == shift_c and shift_r != 0 and shift_c != 0:
            self.error = "knight mv"
            return #invalid can't make knights move
        if self.moved_piece != None and (start[0] != self.moved_piece[0] or start[1] != self.moved_piece[1]):
            if abs(self.board[start[0]][start[1]]) == 2:
                self.make_hit(start, end)
                return
            else:
                self.error = "mv 1 piece/turn"
                return #invalid can only move one piece per turn
        if (shift_r == 1 or shift_c == 1) and self.moved_piece != None:
            if abs(self.board[start[0]][start[1]]) == 2:
                self.make_hit(start, end)
                return
            else:
                self.error = "can't slide"
                return #invalid can't slide after jumps or slides
        if self.moves_done:
            self.error = "mv's done"
            return #invalid can no longer move, attacking with poweredup piece already checked
        if self.player == 1 and self.board_rings[end[0]][end[1]] < 0:
            self.error = "ring in way"
            return #can't move onto opponent ring
        if not self.player == 1 and self.board_rings[end[0]][end[1]] > 0:
            self.error = "ring in way"
            return #can't move onto opponent ring
        if shift_r == 2 or shift_c == 2:
            r = (end[0]-start[0])//2 + start[0]
            c = (end[1]-start[1])//2 + start[1]
            if self.board[r][c] == 0:
                self.error = "jump over nill"
                return #invalid can't jump over nothing
        target_piece = self.board[end[0]][end[1]]
        if target_piece != 0:
            self.moves_done = True
            self.turn_done = self.board[start[0]][start[1]] == 1 #poweredup piece can attack after landing on top
            if self.player == 1:
                self.p1_power += 1
                self.p2_peices_to_buy += 1
                if abs(target_piece) == 2:
                    self.p2_powerups_to_buy
            else:
                self.p2_power += 1
                self.p1_peices_to_buy += 1
                if abs(target_piece) == 2:
                    self.p1_powerups_to_buy
        self.board[end[0]][end[1]] = self.board[start[0]][start[1]]
        self.board[start[0]][start[1]] = 0
        self.moved_piece = list(end)

    def make_hit(self, start, end):
        shift_r = abs(end[0] - start[0])
        shift_c = abs(end[1] - start[1])
        if shift_r > 1:
            return #invalid can only hit adjacent
        if shift_c > 1:
            return #invalid can only hit adjacent
        if self.board_rings[end[0]][end[1]] != 0:
            if self.player == 1 and self.board_rings[end[0]][end[1]] > 0:
                self.error = "hit own ring"
                return
            if not self.player == 1 and self.board_rings[end[0]][end[1]] < 0:
                self.error = "hit own ring"
                return
            self.moves_done = True
            self.turn_done = True
            self.board_rings[end[0]][end[1]] = 0
            if self.player == 1:
                self.p1_power += 1
            else:
                self.p2_power += 1
            self.rings += 1
        elif self.board[end[0]][end[1]] != 0:
            self.moves_done = True
            self.turn_done = True
            if self.player == 1:
                self.p1_power += 1
                self.p2_peices_to_buy += 1
                if abs(self.board[end[0]][end[1]]) == 2:
                    self.p2_powerups_to_buy
            else:
                self.p2_power += 1
                self.p1_peices_to_buy += 1
                if abs(self.board[end[0]][end[1]]) == 2:
                    self.p1_powerups_to_buy
            self.board[end[0]][end[1]] = 0
        else:
            return #invalid can't attack empty

    def make_score(self, start):
        if self.board[start[0]][start[1]] == 0:
            self.error = "not a piece"
            return #invalid not a piece
        if self.player == 1 and self.board[start[0]][start[1]] < 0:
            self.error = "mv opp"
            return #invalid can't move opponent piece
        if not self.player == 1 and self.board[start[0]][start[1]] > 0:
            self.error = "mv opp"
            return #invalid can't move opponent piece
        row = 1 if self.player == 1 else 6
        jump_over_row = 0 if self.player == 1 else 7
        if start[0] != row:
            self.error = "can't score"
            return #can only jump to score from 2nd row
        can_jump = False
        if start[1] > 0 and self.board[jump_over_row][start[1]-1] != 0:
            can_jump = True
        if self.board[jump_over_row][start[1]] != 0:
            can_jump = True
        if start[1] < 7 and self.board[jump_over_row][start[1]+1] != 0:
            can_jump = True
        if not can_jump:
            self.error = "no jump to score"
            return
        self.board[start[0]][start[1]] = 0
        if self.player == 1:
            self.p1_score += 1
            self.p1_power += 2
        else:
            self.p2_score += 1
            self.p2_power += 2

    def make_place(self, loc, type):
        if type == 'piece':
            piece_row = 7 if self.player == 1 else 0
            if loc[0] != piece_row:
                self.error = "invalid loc"
                return
            if self.board[loc[0]][loc[1]] != 0:
                self.error = "occupied"
                return
            if self.player == 1:
                self.board[loc[0]][loc[1]] = 1
                self.p1_peices -= 1
            else:
                self.board[loc[0]][loc[1]] = -1
                self.p2_peices -= 1
            self.placed_in_turn_list.append(list(loc))
        elif type == 'powerup':
            if self.player == 1 and loc[0] not in [6,7]:
                self.error = "only 1st/2nd row"
                return
            if not self.player == 1 and loc[0] not in [0,1]:
                self.error = "only 1st/2nd row"
                return
            if self.player == 1 and self.board[loc[0]][loc[1]] != 1:
                self.error = "only powerup own"
                return
            if not self.player == 1 and self.board[loc[0]][loc[1]] != -1:
                self.error = "only powerup own"
                return
            if self.player == 1:
                self.board[loc[0]][loc[1]] = 2
                self.p1_powerups -= 1
            else:
                self.board[loc[0]][loc[1]] = -2
                self.p2_powerups -= 1
            self.placed_in_turn_list.append(list(loc))
        elif type == 'ring':
            if loc[0] in [0,7]:
                self.error = "not 1st/last row"
                return
            if self.board[loc[0]][loc[1]] != 0:
                self.error = "occupied"
                return
        else:
            self.error = "!! invalid piece !!"
            return

    def make_buy(self, type):
        if self.moved_piece != None:
            self.error="buy phase over"
            return
        if type == 'piece':
            if self.player == 1:
                if self.p1_power < 1:
                    self.error = "not enough"
                    return
                self.p1_peices += 1
                self.p1_power -= 1
            else:
                if self.p2_power < 1:
                    self.error = "not enough"
                    return
                self.p2_peices += 1
                self.p2_power -= 1
        elif type == 'powerup':
            if self.player == 1:
                if self.p1_power < (2 if self.has_bought_powerup else 4):
                    self.error = "not enough"
                    return
                self.p1_powerups += 1
                self.p1_power -= (2 if self.has_bought_powerup else 4)
                self.has_bought_powerup = True
            else:
                if self.p2_power < (2 if self.has_bought_powerup else 4):
                    self.error = "not enough"
                    return
                self.p2_powerups += 1
                self.p2_power -= (2 if self.has_bought_powerup else 4)
                self.has_bought_powerup = True
        elif type == 'ring':
            if self.player == 1:
                if self.p1_power < 4:
                    self.error = "not enough"
                    return
                self.p1_rings += 1
                self.p1_power -= 4
            else:
                if self.p2_power < 4:
                    self.error = "not enough"
                    return
                self.p2_rings += 1
                self.p2_power -= 4
        else:
            self.error = "!! invalid piece !!"
            return

    def input(self, key_code):
        if key_code == 100: #d
            self.selection = None
            self.mode = None
        elif key_code == 13: #ENTER
            if self.moved_piece != None:
                self.turn_done = True
            else:
                self.error = "haven't moved"
        elif key_code == 115: #s
            if self.cursor[0] == 0:
                if self.selection == None:
                    self.selection = list(self.cursor)
                    self.mode = 'move'
                elif self.selection[0] == 0:
                    self.make_move(self.selection[1:], self.cursor[1:])
                    self.selection = None
                    self.mode = None
                elif self.selection[0] == 1:
                    type = "none"
                    if self.player == 1:
                        if self.selection[2] < self.p1_peices:
                            type = "piece"
                        elif self.selection[2] < self.p1_peices + self.p1_powerups:
                            type = "powerup"
                        else:
                            type = "ring"
                    else:
                        if self.selection[2] < self.p2_peices:
                            type = "piece"
                        elif self.selection[2] < self.p2_peices + self.p2_powerups:
                            type = "powerup"
                        else:
                            type = "ring"
                    self.make_place(self.cursor[1:], type)
                    self.selection = None
                    self.mode = None
            if self.cursor[0] == 1:
                if self.selection == None:
                    self.selection = list(self.cursor)
                    self.mode = 'place'

            if self.cursor[0] == 2:
                type = "none"
                if self.cursor[1] == 0:
                    type = "ring"
                elif self.cursor[2] == 0:
                    type = "piece"
                else:
                    type = "powerup"
                self.make_buy(type)
            if self.selection != None and self.selection[0] == 0 and self.cursor[0] == 3:
                self.make_score(self.selection[1:])
                self.mode = None

    def shift_cursor(self, key_code):
        if not key_code in [105,106,107,108]:
            return
        if self.player == 1:
            UP = 105
            LEFT = 106
            DOWN = 107
            RIGHT = 108
        else:
            UP = 107
            LEFT = 108
            DOWN = 105
            RIGHT = 106

        if self.cursor[0] == 0: #board
            if key_code == UP:
                if self.cursor[1] > 0:
                    self.cursor[1] -= 1
                elif self.cursor[1] == 0 and not self.player == 1 and self.p2_peices + self.p2_powerups > 0:
                    self.cursor[0] = 1
                    self.cursor[2] = min((7 - self.cursor[2]), self.p2_peices + self.p2_powerups - 1)
                elif self.cursor[1] == 0 and self.player == 1:
                    self.cursor[0] = 3
            elif key_code == LEFT:
                if self.cursor[2] > 0:
                    self.cursor[2] -= 1
                elif self.cursor[2] == 0 and not self.player == 1:
                    self.cursor[0] = 2
                    self.cursor[1] = 1 if self.cursor[1] < 4 else 0
                    self.cursor[2] = 0
            elif key_code == DOWN:
                if self.cursor[1] < 7:
                    self.cursor[1] += 1
                elif self.cursor[1] == 7 and self.player == 1 and self.p1_peices + self.p1_powerups > 0:
                    self.cursor[0] = 1
                    self.cursor[2] = min(self.cursor[2], self.p1_peices + self.p1_powerups - 1)
                elif self.cursor[1] == 7 and not self.player == 1:
                    self.cursor[0] = 3
            elif key_code == RIGHT:
                if self.cursor[2] < 7:
                    self.cursor[2] += 1
                elif self.cursor[2] == 7 and self.player == 1:
                    self.cursor[0] = 2
                    self.cursor[1] = 1 if self.cursor[1] > 4 else 0
                    self.cursor[2] = 0
        elif self.cursor[0] == 1: #owned pieces
            if key_code == 105:
                self.cursor[0] = 0
                if self.player == 1:
                    self.cursor[1] = 7
                    self.cursor[2] = min(self.cursor[2], 7)
                else:
                    self.cursor[1] = 0
                    self.cursor[2] = max(7-self.cursor[2], 0)
            elif key_code == 106:
                if self.cursor[2] > 0:
                    self.cursor[2] -= 1
            elif key_code == 108:
                if self.player == 1:
                    num_owned = self.p1_peices + self.p1_powerups + self.p1_rings
                else:
                    num_owned = self.p2_peices + self.p2_powerups + self.p2_rings

                if self.cursor[2] < num_owned - 1:
                    self.cursor[2] += 1
                elif self.cursor[2] == num_owned - 1:
                    self.cursor[0] = 2
                    self.cursor[1] = 1
                    self.cursor[2] = 0

        elif self.cursor[0] == 2: #pieces to buy
            if key_code == 105:
                self.cursor[1] = 0
            elif key_code == 106:
                if self.cursor[1] == 1 and self.cursor[2] > 0:
                    self.cursor[2] -= 1
                elif self.cursor[2] == 0 or self.cursor[1] == 0:
                    self.cursor[0] = 0
                    if self.player == 1:
                        self.cursor[1] = 3 if self.cursor[1] == 0 else 7
                        self.cursor[2] = 7
                    else:
                        self.cursor[1] = 4 if self.cursor[1] == 0 else 0
                        self.cursor[2] = 0
            elif key_code == 107:
                self.cursor[1] = 1
            elif key_code == 108:
                if self.cursor[2] < 1:
                    self.cursor[2] += 1

        elif self.cursor[0] == 3: #scoring
            if key_code == 107:
                self.cursor[0] = 0

    def place_cursor(self, arr, animation):
        if not animation:
            return
        if self.cursor[0] == 0: #board
            if self.player == 1:
                arr[3 + self.cursor[1]*2][3 + 4*self.cursor[2]] = '<'
                arr[3 + self.cursor[1]*2][5 + 4*self.cursor[2]] = '>'
            else:
                arr[17 - self.cursor[1]*2][36 - 5 - 4*self.cursor[2]] = '<'
                arr[17 - self.cursor[1]*2][36 - 3 - 4*self.cursor[2]] = '>'
        if self.cursor[0] == 1: #owned
            if self.player == 1:
                split_num = self.p1_peices + self.p1_powerups
            else:
                split_num = self.p2_peices + self.p2_powerups
            extra_shift = max(self.cursor[2] - split_num + 1, 0)
            arr[20][3 + self.cursor[2]*2 + extra_shift] = '^'
        if self.cursor[0] == 2: #to buy
            if self.cursor[1] == 0:
                arr[10][38] = '^'
                arr[10][39] = '^'
                arr[10][40] = '^'
            elif self.cursor[1] == 1:
                arr[18][38 + self.cursor[2]] = '^'
        if self.cursor[0] == 3: #score
            score = "** S C O R E **"
            for i in range(len(score)):
                arr[0][10 + i] = score[i]

    def place_selection(self, arr):
        if self.mode == 'move':
            if self.player == 1:
                arr[3 + self.selection[1]*2][3 + 4*self.selection[2]] = '«'
                arr[3 + self.selection[1]*2][5 + 4*self.selection[2]] = '»'
            else:
                arr[17 - self.selection[1]*2][36 - 5 - 4*self.selection[2]] = '«'
                arr[17 - self.selection[1]*2][36 - 3 - 4*self.selection[2]] = '»'
        if self.mode == 'place':
            if self.player == 1:
                split_num = self.p1_peices + self.p1_powerups
            else:
                split_num = self.p2_peices + self.p2_powerups
            extra_shift = max(self.selection[2] - split_num + 1, 0)
            arr[20][3 + self.selection[2]*2 + extra_shift] = '^'

    def place_grid(self, arr, shift_r=2, shift_c=2):
        for i in range(15):
            for j in range(31):
                if i % 2 == 1:
                    arr[shift_r + 1 + i][shift_c + 1 + j] = '┼' if j%4 == 3 else '─'
                else:
                    arr[shift_r + 1 + i][shift_c + 1 + j] = '│' if j%4 == 3 else ' '

        for j in range(33):
            if j == 0:
                arr[shift_r][shift_c + j] = '╔'
                arr[shift_r + 16][shift_c + j] = '╚'
            elif j == 32:
                arr[shift_r][shift_c + j] = '╗'
                arr[shift_r + 16][shift_c + j] = '╝'
            else:
                arr[shift_r][shift_c + j] = '═'
                arr[shift_r+16][shift_c + j] = '═'
        for i in range(15):
            arr[shift_r + i+1][shift_c] = '║'
            arr[shift_r + i+1][shift_c + 32] = '║'

    def place_pieces(self, arr, shift_r=2, shift_c=2):
        for i in range(self.board.shape[0]):
            for j in range(self.board.shape[1]):
                p = self.piece_dict[self.board[i][j]]
                if self.player == 1:
                    arr[shift_r + 1 + i*2][shift_c + 2 + 4*j] = p
                else:
                    arr[shift_r + 16 - 1 - i*2][shift_c + 32 - 2 - 4*j] = p

        for i in range(self.board_rings.shape[0]):
            for j in range(self.board_rings.shape[1]):
                p = self.ring_dict[self.board_rings[i][j]]
                if self.player == 1:
                    arr[shift_r + 1 + i*2][shift_c + 1 + 4*j] = p[0]
                    arr[shift_r + 1 + i*2][shift_c + 3 + 4*j] = p[1]
                else:
                    arr[shift_r + 16 - 1 - i*2][shift_c + 32 - 3 - 4*j] = p[0]
                    arr[shift_r + 16 - 1 - i*2][shift_c + 32 - 1 - 4*j] = p[1]


    def place_power_bar_down(self, arr, row=3, col=0, animation=True):
        P = self.p2_power if self.player == 1 else self.p1_power
        for i in range(P):
            arr[row + i][col] = '█' if animation else '▒'
        arr[row + P][col] = str(P)

    def place_power_bar_up(self, arr, row=18, col=35, animation=True):
        P = self.p1_power if self.player == 1 else self.p2_power
        for i in range(P):
            arr[row - i][col] = '█' if animation else '▒'
        arr[row - P][col] = str(P)

    def place_owned_pieces(self, arr):
        if self.player == 1:
            for i in range(self.p1_peices):
                arr[19][3 + 2*i] = self.piece_dict[1]
            for i in range(self.p1_powerups):
                arr[19][3 + 2*self.p1_peices + 2*i] = self.piece_dict[2]
            for i in range(self.p1_rings):
                arr[19][3 + 2*self.p1_peices + 2*self.p1_powerups + 3*i] = self.ring_dict[1][0]
                arr[19][3 + 2*self.p1_peices + 2*self.p1_powerups + 3*i + 1] = self.ring_dict[1][1]

            for i in range(self.p2_peices):
                arr[1][33 - 2*i] = self.piece_dict[-1]
            for i in range(self.p2_powerups):
                arr[1][33 - 2*self.p2_peices - 2*i] = self.piece_dict[-2]
            for i in range(self.p2_rings):
                arr[1][33 - 2*self.p2_peices - 2*self.p2_powerups - 3*i - 1] = self.ring_dict[-1][0]
                arr[1][33 - 2*self.p2_peices - 2*self.p2_powerups - 3*i] = self.ring_dict[-1][1]
        else:
            for i in range(self.p2_peices):
                arr[19][3 + 2*i] = self.piece_dict[-1]
            for i in range(self.p2_powerups):
                arr[19][3 + 2*self.p2_peices + 2*i] = self.piece_dict[-2]
            for i in range(self.p2_rings):
                arr[19][3 + 2*self.p2_peices + 2*self.p2_powerups + 3*i] = self.ring_dict[-1][0]
                arr[19][3 + 2*self.p2_peices + 2*self.p2_powerups + 3*i + 1] = self.ring_dict[-1][1]

            for i in range(self.p1_peices):
                arr[1][33 - 2*i] = self.piece_dict[1]
            for i in range(self.p1_powerups):
                arr[1][33 - 2*self.p1_peices - 2*i] = self.piece_dict[2]
            for i in range(self.p1_rings):
                arr[1][33 - 2*self.p1_peices - 2*self.p1_powerups - 3*i - 1] = self.ring_dict[1][0]
                arr[1][33 - 2*self.p1_peices - 2*self.p1_powerups - 3*i] = self.ring_dict[1][1]

    def place_pieces_to_buy(self, arr):
        for i in range(2,19):
            arr[i][37] = '│'

        if self.player == 1:
            for i in range(self.p1_powerups_to_buy):
                arr[17-i][39] = self.piece_dict[2]
            for i in range(self.p2_powerups_to_buy):
                arr[3+i][39] = self.piece_dict[-2]
            for i in range(self.p1_peices_to_buy):
                arr[17-i][38] = self.piece_dict[1]
            for i in range(self.p2_peices_to_buy):
                arr[3+i][38] = self.piece_dict[-1]
        else:
            for i in range(self.p2_powerups_to_buy):
                arr[17-i][39] = self.piece_dict[-2]
            for i in range(self.p1_powerups_to_buy):
                arr[3+i][39] = self.piece_dict[2]
            for i in range(self.p2_peices_to_buy):
                arr[17-i][38] = self.piece_dict[-1]
            for i in range(self.p1_peices_to_buy):
                arr[3+i][38] = self.piece_dict[1]

        for i in range(self.rings):
            arr[9][38+3*i] = "{"
            arr[9][38+3*i+1] = "}"

    def place_error(self, arr):
        for i in range(len(self.error)):
            arr[21][3+i] = self.error[i]

    def place_score(self, arr):
        score = "S C O R E"
        for i in range(len(score)):
            arr[11][39+i] = score[i]
        score = self.piece_dict[1] + ": " + str(self.p1_score) + "-" + str(self.p2_score) + " :" + self.piece_dict[-1]
        for i in range(len(score)):
            arr[12][39+i] = score[i]


    def render(self, animation):
        arr = [[' ' for _ in range(49)] for _ in range (22)]

        self.place_power_bar_down(arr, animation=animation)
        self.place_power_bar_up(arr, animation=animation)
        self.place_grid(arr)

        self.place_pieces(arr)
        self.place_owned_pieces(arr)
        self.place_pieces_to_buy(arr)

        self.place_selection(arr)
        self.place_cursor(arr, animation)
        self.place_score(arr)
        self.place_error(arr)

        self.next_turn()

        os.system('cls' if os.name == 'nt' else 'clear')
        s = ""
        for i in range(len(arr)):
            for j in range(len(arr[0])):
                s += arr[i][j]
            s += "\n"
        print(s)



def read_kbd_input(inputQueue):
    while (True):
        inputQueue.put(ord(getch()))

def main():
    EXIT_COMMAND = 113
    inputQueue = queue.Queue()

    inputThread = threading.Thread(target=read_kbd_input, args=(inputQueue,), daemon=True)
    inputThread.start()

    animation_length = .5
    last_animation = time.time()
    animation = False
    need_render = True

    game = Motus()
    game.render(False)

    while (True):
        if (inputQueue.qsize() > 0):
            key_code = inputQueue.get()
            if (key_code == EXIT_COMMAND):
                print("Exiting Game")
                break

            game.shift_cursor(key_code)
            game.input(key_code)
            animation = True
            last_animation = time.time()
            need_render = True

        if time.time() - last_animation > animation_length:
            animation = not animation
            last_animation = time.time()
            need_render = True

        if need_render:
            game.render(animation)
            need_render = False
    print("Exit")

main()
