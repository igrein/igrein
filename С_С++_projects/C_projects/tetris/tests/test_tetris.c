#include <check.h>
#include <curses.h>
#include <sys/time.h>
#include <time.h>

#include "../brick_game/tetris/tetris_game.h"

START_TEST(test_init_terminate) {
  TetrisState_t state;
  game_init(&state);
  ck_assert_ptr_nonnull(state.info.field);
  ck_assert_ptr_nonnull(state.info.next);
  ck_assert_int_eq(state.info.level, 1);
  ck_assert_int_eq(state.info.score, 0);

  game_terminate(&state);
}
END_TEST

START_TEST(test_user_input_status) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = StartState;

  fsm_handle_state(&state);
  ck_assert(state.current_state == SpawnState);

  state.current_state = MovingState;
  userInput(&state, Pause, false);
  ck_assert(state.info.pause == true);

  userInput(&state, Terminate, false);
  ck_assert(state.game_active == false);
  ck_assert(state.current_state == GameOverState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_user_input_move) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = MovingState;
  state.current = (TetrisFigure_t){
      .x = 5,
      .y = 5,
      .matrix = {{0, 0, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0}, {0, 0, 0, 0}},
      .width = FIGURE_SIZE,
      .height = FIGURE_SIZE};

  userInput(&state, Left, false);
  ck_assert_int_eq(state.current.x, 4);

  state.current.x = 5;

  userInput(&state, Right, false);
  ck_assert_int_eq(state.current.x, 6);

  state.current.x = 5;

  int original_matrix[FIGURE_SIZE][FIGURE_SIZE];
  memcpy(original_matrix, state.current.matrix, sizeof(original_matrix));

  userInput(&state, Action, false);
  ck_assert_mem_ne(&state.current.matrix, &original_matrix,
                   sizeof(original_matrix));

  int old_y = state.current.y;

  userInput(&state, Down, false);
  ck_assert_int_gt(state.current.y, old_y);

  game_terminate(&state);
}
END_TEST

START_TEST(test_moving_operate) {
  TetrisState_t state;
  game_init(&state);
  reset_fall_timer(&state);
  state.current_state = MovingState;
  state.info.speed = 2000;
  state.current = (TetrisFigure_t){.x = 5,
                                   .y = 5,
                                   .matrix = {{1, 0}, {1, 0}, {1, 1}},
                                   .width = 2,
                                   .height = 3,
                                   .is_locked = false};

  state.last_action = Left;
  moving_operate(&state);
  ck_assert_int_eq(state.current.x, 4);
  ck_assert_int_eq(state.current.y, 5);

  state.last_action = Right;
  moving_operate(&state);
  ck_assert_int_eq(state.current.x, 5);
  ck_assert_int_eq(state.current.y, 5);

  state.last_action = Down;
  moving_operate(&state);
  ck_assert_int_eq(state.current.y, 6);

  int original_matrix[3][2];
  memcpy(original_matrix, state.current.matrix, sizeof(original_matrix));
  state.last_action = Action;
  moving_operate(&state);
  ck_assert_mem_ne(&state.current.matrix, original_matrix,
                   sizeof(original_matrix));

  state.last_action = Pause;
  moving_operate(&state);
  ck_assert(state.info.pause);

  state.last_action = Left;
  int old_x = state.current.x;
  moving_operate(&state);
  ck_assert_int_eq(state.current.x, old_x);

  state.last_action = Pause;
  moving_operate(&state);
  ck_assert(!state.info.pause);

  game_terminate(&state);
}
END_TEST

START_TEST(test_shifting_operate) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = ShiftingState;

  state.current = (TetrisFigure_t){.x = 5,
                                   .y = 15,
                                   .matrix = {{1, 1}, {1, 1}},
                                   .width = 2,
                                   .height = 2,
                                   .is_locked = false};

  shifting_operate(&state);
  ck_assert_int_eq(state.current.y, 16);
  ck_assert(state.current_state == MovingState ||
            state.current_state == AttachingState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_attaching_operate) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = AttachingState;

  state.current = (TetrisFigure_t){.x = 5,
                                   .y = HEIGHT - 2,
                                   .matrix = {{1, 1}, {1, 1}},
                                   .width = 2,
                                   .height = 2,
                                   .is_locked = true};

  attaching_operate(&state);
  ck_assert(state.info.field[HEIGHT - 1][5] == 1);
  ck_assert(state.info.field[HEIGHT - 1][6] == 1);
  ck_assert(state.current_state == SpawnState ||
            state.current_state == GameOverState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_spawn_operate) {
  TetrisState_t state;
  game_init(&state);

  state.next =
      (TetrisFigure_t){.matrix = {{1, 1}, {1, 1}}, .width = 2, .height = 2};

  state.current_state = SpawnState;
  spawn_operate(&state);
  ck_assert_int_eq(state.current_state, MovingState);

  for (int i = 0; i < 2; i++) {
    for (int j = WIDTH / 2 - 1; j < WIDTH / 2 + 1; j++) {
      state.info.field[i][j] = 1;
    }
  }

  state.current_state = SpawnState;
  spawn_operate(&state);
  ck_assert_int_eq(state.current_state, GameOverState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_gameover_operate) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = GameOverState;
  state.game_active = true;

  gameover_operate(&state);
  ck_assert(!state.game_active);

  state.last_action = Start;
  gameover_operate(&state);
  ck_assert_int_eq(state.current_state, StartState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_attach_to_field) {
  TetrisState_t state;
  game_init(&state);

  state.current = (TetrisFigure_t){
      .x = 0,
      .y = 0,
      .matrix = {{1, 0, 0, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},
      .width = 3,
      .height = 2};

  attach_to_field(&state);
  ck_assert_int_eq(state.info.field[0][0], 1);
  ck_assert_int_eq(state.info.field[1][0], 1);
  ck_assert_int_eq(state.info.field[1][1], 1);

  game_terminate(&state);
}
END_TEST

START_TEST(test_is_game_over) {
  TetrisState_t state;
  game_init(&state);

  ck_assert(!is_game_over(&state));

  for (int x = 0; x < WIDTH; x++) {
    state.info.field[0][x] = 1;
  }

  ck_assert(is_game_over(&state));

  game_terminate(&state);
}
END_TEST

START_TEST(test_clear_lines) {
  TetrisState_t state;
  game_init(&state);

  for (int x = 0; x < WIDTH; x++) {
    state.info.field[HEIGHT - 1][x] = 1;
  }

  int cleared = clear_completed_lines(&state);
  ck_assert_int_eq(cleared, 1);

  for (int x = 0; x < WIDTH; x++) {
    ck_assert_int_eq(state.info.field[HEIGHT - 1][x], 0);
  }

  game_terminate(&state);
}
END_TEST

START_TEST(test_score_calculation) {
  TetrisState_t state;
  game_init(&state);

  ck_assert_int_eq(state.info.level, 1);

  state.info.score = 600;
  update_score_level(&state, 1);
  ck_assert_int_eq(state.info.level, 2);

  state.info.score += 600;
  update_score_level(&state, 1);
  ck_assert_int_eq(state.info.level, 3);

  game_terminate(&state);
}
END_TEST

START_TEST(test_level_speed_increase) {
  TetrisState_t state;
  game_init(&state);

  int initial_speed = state.info.speed;

  state.info.score = POINTS_FOR_LEVEL;
  update_score_level(&state, 1);

  ck_assert_int_eq(state.info.speed, initial_speed - LEVEL_SPEED_STEP);

  state.info.score = POINTS_FOR_LEVEL * 2;
  update_score_level(&state, 1);
  ck_assert_int_eq(state.info.speed, initial_speed - 2 * LEVEL_SPEED_STEP);

  game_terminate(&state);
}
END_TEST

START_TEST(test_high_score) {
  GameInfo_t info = {0};
  info.high_score = 1000;

  save_high_score(&info);
  load_high_score(&info);
  ck_assert_int_eq(info.high_score, 1000);
}
END_TEST

START_TEST(test_hard_drop) {
  TetrisState_t state;
  game_init(&state);

  state.current = (TetrisFigure_t){
      .x = 0,
      .y = 0,
      .matrix = {{1, 0, 0, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},
      .width = 3,
      .height = 2};

  hard_drop(&state);
  ck_assert_int_gt(state.current.y, 0);

  game_terminate(&state);
}
END_TEST

START_TEST(test_can_place_figure) {
  TetrisState_t state;
  game_init(&state);

  state.current = (TetrisFigure_t){
      .x = 0,
      .y = 0,
      .matrix = {{1, 1, 0, 0}, {1, 1, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},
      .width = 2,
      .height = 2};
  ck_assert(can_place_figure(&state, 0, 0));

  ck_assert(!can_place_figure(&state, -1, 0));
  ck_assert(!can_place_figure(&state, WIDTH - 1, 0));

  game_terminate(&state);
}
END_TEST

START_TEST(test_try_move) {
  TetrisState_t state;
  game_init(&state);

  state.current = (TetrisFigure_t){
      .x = 5, .y = 5, .matrix = {{1, 0}, {1, 1}}, .width = 2, .height = 2};

  ck_assert(try_move(&state, 1, 0));
  ck_assert_int_eq(state.current.x, 6);

  ck_assert(try_move(&state, -1, 0));
  ck_assert_int_eq(state.current.x, 5);

  ck_assert(try_move(&state, 0, 1));
  ck_assert_int_eq(state.current.y, 6);

  state.current.x = 0;
  ck_assert(!try_move(&state, -1, 0));

  game_terminate(&state);
}
END_TEST

START_TEST(test_rotation) {
  TetrisState_t state;
  game_init(&state);

  state.current = (TetrisFigure_t){
      .x = 5,
      .y = 5,
      .matrix = {{1, 0, 0, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},
      .width = 3,
      .height = 2};

  int original_matrix[FIGURE_SIZE][FIGURE_SIZE];
  memcpy(original_matrix, state.current.matrix, sizeof(original_matrix));
  try_rotate(&state);
  ck_assert_int_eq(state.current.matrix[0][0], 1);
  ck_assert_int_eq(state.current.matrix[0][1], 1);
  ck_assert_int_eq(state.current.matrix[1][0], 1);
  ck_assert_int_eq(state.current.matrix[2][0], 1);
  ck_assert_mem_ne(&state.current.matrix, original_matrix,
                   sizeof(original_matrix));

  state.current = (TetrisFigure_t){
      .x = 5,
      .y = 5,
      .matrix = {{1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},
      .width = 3,
      .height = 1};

  for (int x = 3; x <= 7; x++) {
    state.info.field[6][x] = 1;
  }

  memcpy(original_matrix, state.current.matrix, sizeof(original_matrix));
  try_rotate(&state);
  for (int i = 0; i < FIGURE_SIZE; i++) {
    for (int j = 0; j < FIGURE_SIZE; j++) {
      ck_assert_int_eq(state.current.matrix[i][j], original_matrix[i][j]);
    }
  }

  game_terminate(&state);
}
END_TEST

START_TEST(test_fsm_comprehensive) {
  TetrisState_t state;
  game_init(&state);

  state.last_action = Start;
  fsm_handle_state(&state);
  ck_assert_int_eq(state.current_state, SpawnState);

  fsm_handle_state(&state);
  ck_assert_int_eq(state.current_state, MovingState);

  state.current_state = ShiftingState;
  state.current = (TetrisFigure_t){.x = 5,
                                   .y = 5,
                                   .matrix = {{1, 1}},
                                   .width = 2,
                                   .height = 1,
                                   .is_locked = false};
  fsm_handle_state(&state);
  ck_assert(state.current_state == MovingState ||
            state.current_state == AttachingState);

  state.current_state = AttachingState;
  state.current = (TetrisFigure_t){
      .x = 5, .y = HEIGHT - 2, .matrix = {{1, 1}}, .width = 2, .height = 1};
  fsm_handle_state(&state);
  ck_assert(state.current_state == SpawnState ||
            state.current_state == GameOverState);

  state.current_state = GameOverState;
  fsm_handle_state(&state);
  ck_assert(state.game_active == false);

  game_terminate(&state);
}
END_TEST

START_TEST(test_generate_next_figure) {
  TetrisState_t state;
  game_init(&state);

  generate_next_figure(&state);

  int has_blocks = 0;
  for (int i = 0; i < FIGURE_SIZE; i++) {
    for (int j = 0; j < FIGURE_SIZE; j++) {
      if (state.next.matrix[i][j]) has_blocks = 1;
    }
  }
  ck_assert(has_blocks);

  game_terminate(&state);
}
END_TEST

START_TEST(test_update_next_preview) {
  TetrisState_t state;
  game_init(&state);

  state.next =
      (TetrisFigure_t){.matrix = {{1, 0}, {1, 1}}, .width = 2, .height = 2};

  update_next_preview(&state);

  ck_assert_int_eq(state.info.next[0][0], 1);
  ck_assert_int_eq(state.info.next[1][0], 1);
  ck_assert_int_eq(state.info.next[1][1], 1);

  game_terminate(&state);
}
END_TEST

START_TEST(test_update_current_state) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = MovingState;
  state.current = (TetrisFigure_t){
      .x = 5, .y = 5, .matrix = {{1, 0}, {1, 1}}, .width = 2, .height = 2};

  GameInfo_t info = updateCurrentState(Left, &state);
  ck_assert_int_eq(state.current.x, 4);
  ck_assert_ptr_nonnull(info.field);

  game_terminate(&state);
}
END_TEST

START_TEST(test_update_lock_timer) {
  TetrisState_t state;
  game_init(&state);

  state.current_state = MovingState;

  state.current.is_locked = true;
  gettimeofday(&state.lock_timer, NULL);

  state.lock_timer.tv_sec -= 1;

  update_lock_timer(&state);
  ck_assert(state.current_state == AttachingState);

  game_terminate(&state);
}
END_TEST

START_TEST(test_time_to_fall) {
  TetrisState_t state;
  game_init(&state);

  reset_fall_timer(&state);
  ck_assert_int_eq(is_time_to_fall(&state), 0);

  state.last_fall.tv_sec -= 2;
  ck_assert_int_eq(is_time_to_fall(&state), 1);

  game_terminate(&state);
}
END_TEST

START_TEST(test_convert_key) {
  ck_assert_int_eq(convert_key(KEY_LEFT), Left);
  ck_assert_int_eq(convert_key(KEY_RIGHT), Right);
  ck_assert_int_eq(convert_key(KEY_UP), Up);
  ck_assert_int_eq(convert_key(KEY_DOWN), Down);
  ck_assert_int_eq(convert_key(' '), Action);
  ck_assert_int_eq(convert_key('p'), Pause);
  ck_assert_int_eq(convert_key('P'), Pause);
  ck_assert_int_eq(convert_key('q'), Terminate);
  ck_assert_int_eq(convert_key('Q'), Terminate);
  ck_assert_int_eq(convert_key('x'), (UserAction_t)-1);
  ck_assert_int_eq(convert_key(27), (UserAction_t)-1);  // esc
}
END_TEST

Suite *tetris_suite(void) {
  Suite *s;
  TCase *tc_core;

  s = suite_create("Tetris");

  // Базовые тесты
  tc_core = tcase_create("Core");
  tcase_add_test(tc_core, test_init_terminate);
  tcase_add_test(tc_core, test_user_input_status);
  tcase_add_test(tc_core, test_user_input_move);
  tcase_add_test(tc_core, test_moving_operate);
  tcase_add_test(tc_core, test_shifting_operate);
  tcase_add_test(tc_core, test_attaching_operate);
  tcase_add_test(tc_core, test_spawn_operate);
  tcase_add_test(tc_core, test_gameover_operate);
  tcase_add_test(tc_core, test_attach_to_field);
  tcase_add_test(tc_core, test_is_game_over);
  tcase_add_test(tc_core, test_clear_lines);
  tcase_add_test(tc_core, test_score_calculation);
  tcase_add_test(tc_core, test_level_speed_increase);
  tcase_add_test(tc_core, test_high_score);
  tcase_add_test(tc_core, test_hard_drop);
  tcase_add_test(tc_core, test_can_place_figure);
  tcase_add_test(tc_core, test_try_move);
  tcase_add_test(tc_core, test_rotation);
  tcase_add_test(tc_core, test_fsm_comprehensive);
  tcase_add_test(tc_core, test_generate_next_figure);
  tcase_add_test(tc_core, test_update_next_preview);
  tcase_add_test(tc_core, test_update_current_state);
  tcase_add_test(tc_core, test_update_lock_timer);
  tcase_add_test(tc_core, test_time_to_fall);
  tcase_add_test(tc_core, test_convert_key);

  suite_add_tcase(s, tc_core);

  return s;
}

int main(void) {
  int number_failed;
  Suite *s;
  SRunner *sr;

  s = tetris_suite();
  sr = srunner_create(s);

  srunner_run_all(sr, CK_NORMAL);
  number_failed = srunner_ntests_failed(sr);
  srunner_free(sr);

  return (number_failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
