#ifndef TETRIS_INTERFACE_H
#define TETRIS_INTERFACE_H

#include <ncurses.h>

#include "../../brick_game/tetris/tetris_game.h"

void init_interface();
void close_interface();

void draw_field(TetrisState_t *state);
void draw_field_borders();
void draw_field_content(TetrisState_t *state);
bool is_cell_filled(TetrisState_t *state, int x, int y);
void draw_sidebar(TetrisState_t *state);

#endif
