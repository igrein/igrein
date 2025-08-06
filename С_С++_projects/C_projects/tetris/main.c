#define _POSIX_C_SOURCE 200809L
#include "brick_game/tetris/tetris_game.h"
#include "gui/cli/tetris_interface.h"

int main(void) {
  TetrisState_t state = {0};
  game_init(&state);
  init_interface();

  state.game_active = true;
  struct timespec ts = {0, 10000000};  // 10 мс

  while (state.game_active) {
    int ch = getch();
    if (ch != ERR) {
      UserAction_t action = convert_key(ch);
      if (action != (UserAction_t)-1) {
        userInput(&state, action, false);
      }
    }

    if (!state.info.pause) {
      fsm_handle_state(&state);
      ts.tv_nsec = (100 - state.info.level * 5) * 1000000L;
    }

    draw_field(&state);
    nanosleep(&ts, NULL);
  }

  close_interface();
  game_terminate(&state);
  return 0;
}


