#include "tetris_interface.h"

#include <ncurses.h>

void init_interface() {
  initscr();
  noecho();
  curs_set(FALSE);
  keypad(stdscr, TRUE);
  nodelay(stdscr, TRUE);
  start_color();
  init_pair(1, COLOR_WHITE, COLOR_BLACK);
  init_pair(2, COLOR_BLACK, COLOR_WHITE);
}

void close_interface() {
  clear();
  refresh();
  endwin();
}

void draw_field(TetrisState_t *state) {
  if (!state || !state->info.field) return;

  clear();

  draw_field_borders();

  draw_field_content(state);

  draw_sidebar(state);
  refresh();
}

void draw_field_borders() {
  for (int y = 0; y <= HEIGHT + 1; y++) {
    for (int x = 0; x <= WIDTH + 1; x++) {
      if (x == 0 || x == WIDTH + 1 || y == 0 || y == HEIGHT + 1) {
        attron(COLOR_PAIR(1));
        mvprintw(y, x * 2, "[]");
        attroff(COLOR_PAIR(1));
      }
    }
  }
}

void draw_field_content(TetrisState_t *state) {
  for (int y = 1; y <= HEIGHT; y++) {
    for (int x = 1; x <= WIDTH; x++) {
      int draw_x = x - 1;
      int draw_y = y - 1;
      bool filled = is_cell_filled(state, draw_x, draw_y);

      attron(COLOR_PAIR(filled ? 1 : 2));
      mvprintw(y, x * 2, "  ");
      attroff(COLOR_PAIR(filled ? 1 : 2));
    }
  }
}

bool is_cell_filled(TetrisState_t *state, int x, int y) {
  bool filled = state->info.field[y][x];

  for (int i = 0; !filled && i < state->current.height; i++) {
    for (int j = 0; !filled && j < state->current.width; j++) {
      filled = state->current.matrix[i][j] && (state->current.x + j == x) &&
               (state->current.y + i == y);
    }
  }

  return filled;
}

void draw_sidebar(TetrisState_t *state) {
  if (!state) return;

  int start_x = WIDTH * 2 + 4;

  mvprintw(1, start_x, "Next:");
  for (int i = 0; i < 6; i++) {
    for (int j = 0; j < 6; j++) {
      int y = 2 + i;
      int x = start_x + j * 2;
      if (i == 0 || i == 5 || j == 0 || j == 5) {
        attron(COLOR_PAIR(1));
        mvprintw(y, x, "[]");
        attroff(COLOR_PAIR(1));
      } else {
        attron(COLOR_PAIR(2));
        mvprintw(y, x, "  ");
        attroff(COLOR_PAIR(2));
      }
    }
  }

  int shiftY = 2 + (6 - state->next.height) / 2;
  int shiftX = start_x + ((6 - state->next.width) * 2) / 2;

  for (int i = 0; i < state->next.height; i++) {
    for (int j = 0; j < state->next.width; j++) {
      if (state->next.matrix[i][j]) {
        attron(COLOR_PAIR(1));
        mvprintw(shiftY + i, shiftX + j * 2, "  ");
        attroff(COLOR_PAIR(1));
      }
    }
  }

  // Статистика
  attron(A_BOLD);
  mvprintw(9, start_x, "SCORE: %d", state->info.score);
  attroff(A_BOLD);
  mvprintw(10, start_x, "High: %d", state->info.high_score);
  mvprintw(11, start_x, "Level: %d", state->info.level);

  // Управление
  mvprintw(13, start_x, "Controls:");
  mvprintw(14, start_x, "Right & Left arrows: Move");
  mvprintw(15, start_x, "Space: Rotate");
  mvprintw(16, start_x, "Down arrow: Hard drop");
  mvprintw(17, start_x, "Up arrow: ");
  mvprintw(18, start_x, "P: Pause");
  mvprintw(19, start_x, "Q: Quit");
}
