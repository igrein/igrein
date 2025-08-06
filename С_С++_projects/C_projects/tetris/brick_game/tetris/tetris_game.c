#include "tetris_game.h"

#include "../../gui/cli/tetris_interface.h"

// Работа с состояниями игры
void start_operate(TetrisState_t *state) {
  if (state->last_action == Start) {
    for (int i = 0; i < HEIGHT; i++) {
      memset(state->info.field[i], 0, WIDTH * sizeof(int));
    }

    state->info.score = 0;
    state->info.level = 1;
    state->info.pause = false;
    state->game_active = true;

    generate_next_figure(state);
    state->current_state = SpawnState;
  }
}

void spawn_operate(TetrisState_t *state) {
  memcpy(&state->current, &state->next, sizeof(TetrisFigure_t));
  state->current.x = WIDTH / 2 - state->current.width / 2;
  state->current.y = 0;
  state->current.is_locked = false;

  if (!can_place_figure(state, 0, 0)) {
    state->current_state = GameOverState;
    return;
  }

  generate_next_figure(state);
  update_next_preview(state);
  state->current_state = MovingState;
  reset_fall_timer(state);
}

void moving_operate(TetrisState_t *state) {
  bool should_process = true;

  if (state->last_action == Pause) {
    state->info.pause = !state->info.pause;
    should_process = false;
  }

  if (should_process && !state->info.pause) {
    switch (state->last_action) {
      case Left:
        try_move(state, -1, 0);
        break;
      case Right:
        try_move(state, 1, 0);
        break;
      case Down:
        if (!try_move(state, 0, 1)) {
          state->current_state = AttachingState;
        }
        reset_fall_timer(state);
        break;
      case Action:
        try_rotate(state);
        break;
      // case Up: break;
      default:
        break;
    }

    if (is_time_to_fall(state)) {
      if (!try_move(state, 0, 1)) {
        state->current_state = AttachingState;
      }
      reset_fall_timer(state);
    }
  }
}

void shifting_operate(TetrisState_t *state) {
  if (try_move(state, 0, 1)) {
    state->current_state = MovingState;
  } else {
    state->current_state = AttachingState;
  }

  reset_fall_timer(state);
}

void attaching_operate(TetrisState_t *state) {
  attach_to_field(state);

  int lines = clear_completed_lines(state);
  if (lines > 0) {
    update_score_level(state, lines);
  }

  if (is_game_over(state)) {
    state->current_state = GameOverState;
  } else {
    state->current_state = SpawnState;
  }
}

void gameover_operate(TetrisState_t *state) {
  state->game_active = false;

  if (state->last_action == Start) {
    state->current_state = StartState;
  }
}

//  Работа с фигурами
void generate_next_figure(TetrisState_t *state) {
  int next_type = rand() % 7;
  state->next.type = next_type;

  memcpy(state->next.matrix, tetris_figure[next_type],
         FIGURE_SIZE * FIGURE_SIZE * sizeof(int));
  state->next.width = figure_sizes[next_type].width;
  state->next.height = figure_sizes[next_type].height;

  for (int i = 0; i < FIGURE_SIZE; i++) {
    for (int j = 0; j < FIGURE_SIZE; j++) {
      state->info.next[i][j] = state->next.matrix[i][j];
    }
  }
}

bool can_place_figure(const TetrisState_t *state, int shiftX, int shiftY) {
  const TetrisFigure_t *fig = &state->current;
  bool is_valid = true;

  for (int i = 0; is_valid && i < fig->height; i++) {
    for (int j = 0; is_valid && j < fig->width; j++) {
      if (!fig->matrix[i][j]) continue;

      const int global_x = fig->x + j + shiftX;
      const int global_y = fig->y + i + shiftY;

      if (global_x < 0 || global_x >= WIDTH || global_y >= HEIGHT) {
        is_valid = false;
        continue;
      }
      is_valid = (global_y < 0) || !state->info.field[global_y][global_x];
    }
  }
  return is_valid;
}

bool try_move(TetrisState_t *state, int shiftX, int shiftY) {
  bool move_successful = false;

  if (!state->current.is_locked) {
    if (can_place_figure(state, shiftX, shiftY)) {
      state->current.x += shiftX;
      state->current.y += shiftY;
      move_successful = true;

      if (!can_place_figure(state, 0, 1)) {
        state->current.is_locked = true;
        gettimeofday(&state->lock_timer, NULL);
      }
    }
  }

  return move_successful;
}

void try_rotate(TetrisState_t *state) {
  if (state->current.is_locked) return;

  TetrisFigure_t *fig = &state->current;
  bool rotation_success = false;

  const int old_width = fig->width;
  const int old_height = fig->height;
  const int old_x = fig->x;
  int old_matrix[FIGURE_SIZE][FIGURE_SIZE];
  memcpy(old_matrix, fig->matrix, sizeof(old_matrix));

  int temp[FIGURE_SIZE][FIGURE_SIZE] = {0};
  for (int y = 0; y < fig->height; y++) {
    for (int x = 0; x < fig->width; x++) {
      temp[x][fig->height - 1 - y] = fig->matrix[y][x];
    }
  }

  const int kicks[] = {0, -1, 1, -2, 2};
  for (int i = 0; !rotation_success && i < 5; i++) {
    fig->x = old_x + kicks[i];
    fig->width = old_height;
    fig->height = old_width;
    memcpy(fig->matrix, temp, sizeof(temp));

    if (can_place_figure(state, 0, 0)) {
      rotation_success = true;
      if (!can_place_figure(state, 0, 1)) {
        state->current_state = AttachingState;
      }
    }
  }

  if (!rotation_success) {
    fig->x = old_x;
    fig->width = old_width;
    fig->height = old_height;
    memcpy(fig->matrix, old_matrix, sizeof(old_matrix));
  }
}

void update_lock_timer(TetrisState_t *state) {
  if (state->current.is_locked) {
    struct timeval now;
    gettimeofday(&now, NULL);
    long elapsed = (now.tv_sec - state->lock_timer.tv_sec) * 1000 +
                   (now.tv_usec - state->lock_timer.tv_usec) / 1000;

    if (elapsed > LOCK_DELAY_MS) {
      state->current_state = AttachingState;
    }
  }
}

void hard_drop(TetrisState_t *state) {
  while (try_move(state, 0, 1)) {
  }
}

// Логика игры
void attach_to_field(TetrisState_t *state) {
  for (int i = 0; i < state->current.height; i++) {
    for (int j = 0; j < state->current.width; j++) {
      if (state->current.matrix[i][j]) {
        int global_i = state->current.y + i;
        int global_j = state->current.x + j;

        if (global_i >= 0 && global_i < HEIGHT && global_j >= 0 &&
            global_j < WIDTH) {
          state->info.field[global_i][global_j] = 1;
        }
      }
    }
  }
}

int clear_completed_lines(TetrisState_t *state) {
  int lines_cleared = 0;
  int y = HEIGHT - 1;

  while (y >= 0) {
    int line_full = 1;

    for (int x = 0; x < WIDTH; x++) {
      if (!state->info.field[y][x]) {
        line_full = 0;
        break;
      }
    }

    if (line_full) {
      lines_cleared++;

      for (int ny = y; ny > 0; ny--) {
        memcpy(state->info.field[ny], state->info.field[ny - 1],
               WIDTH * sizeof(int));
      }

      memset(state->info.field[0], 0, WIDTH * sizeof(int));

    } else {
      y--;
    }
  }

  return lines_cleared;
}

void update_score_level(TetrisState_t *state, int lines) {
  const int line_bonuses[] = LINE_SCORES;

  if (lines > 0 && lines <= 4) {
    state->info.score += line_bonuses[lines];

    if (state->info.score > state->info.high_score) {
      state->info.high_score = state->info.score;
      save_high_score(&state->info);
    }

    int new_level = state->info.score / POINTS_FOR_LEVEL + 1;

    if (new_level > state->info.level) {
      if (new_level <= MAX_LEVEL) {
        state->info.level = new_level;

        state->info.speed = MAX_SPEED - ((new_level - 1) * LEVEL_SPEED_STEP);

        if (state->info.speed < MIN_SPEED) {
          state->info.speed = MIN_SPEED;
        }
      } else {
        state->info.level = MAX_LEVEL;
      }
    }
  }
}

void reset_fall_timer(TetrisState_t *state) {
  gettimeofday(&state->last_fall, NULL);
}

int is_time_to_fall(const TetrisState_t *state) {
  struct timeval now;
  gettimeofday(&now, NULL);

  long elapsed = (now.tv_sec - state->last_fall.tv_sec) * 1000 +
                 (now.tv_usec - state->last_fall.tv_usec) / 1000;

  return elapsed >= state->info.speed;
}

void update_next_preview(TetrisState_t *state) {
  for (int i = 0; i < FIGURE_SIZE; i++) {
    for (int j = 0; j < FIGURE_SIZE; j++) {
      state->info.next[i][j] = state->next.matrix[i][j];
    }
  }
}

void save_high_score(const GameInfo_t *info) {
  FILE *f = fopen("high_score.txt", "w");
  if (f) {
    fprintf(f, "%d", info->high_score);
    fclose(f);
  }
}

void load_high_score(GameInfo_t *info) {
  FILE *f = fopen("high_score.txt", "r");
  if (f) {
    fscanf(f, "%d", &info->high_score);
    fclose(f);
  } else {
    info->high_score = 0;
  }
}

int is_game_over(const TetrisState_t *state) {
  int game_over = 0;

  if (state != NULL) {
    for (int x = 0; !game_over && x < WIDTH; x++) {
      game_over = state->info.field[0][x];
    }
  }

  return game_over;
}

// начало и пользовательский ввод
void game_init(TetrisState_t *state) {
  srand(time(NULL));

  state->info.field = create_matrix(HEIGHT, WIDTH);
  state->info.next = create_matrix(FIGURE_SIZE, FIGURE_SIZE);

  memset(&state->current, 0, sizeof(TetrisFigure_t));
  memset(&state->next, 0, sizeof(TetrisFigure_t));

  state->info.score = 0;
  state->info.level = 1;
  state->info.speed = MAX_SPEED;
  state->info.pause = false;

  load_high_score(&state->info);
  state->current_state = StartState;
  state->lines_cleared = 0;
}

void game_terminate(TetrisState_t *state) {
  free_matrix(state->info.field, HEIGHT);
  free_matrix(state->info.next, FIGURE_SIZE);
}

int **create_matrix(int rows, int cols) {
  int **matrix = NULL;
  bool allocation_failed = false;
  int allocated_rows = 0;  // Счетчик успешно выделенных строк

  if (rows > 0 && cols > 0) {
    // Выделение памяти под указатели на строки
    matrix = malloc(rows * sizeof(int *));
    allocation_failed = (matrix == NULL);

    // Выделение памяти под сами строки
    for (allocated_rows = 0; !allocation_failed && allocated_rows < rows;
         allocated_rows++) {
      matrix[allocated_rows] = calloc(cols, sizeof(int));
      allocation_failed = (matrix[allocated_rows] == NULL);
    }

    // Обработка ошибок выделения
    if (allocation_failed) {
      if (matrix) {
        // Освобождаем только то, что успели выделить
        for (int j = 0; j < allocated_rows; j++) {
          free(matrix[j]);
        }
        free(matrix);
      }
      matrix = NULL;
    }
  }

  return matrix;
}

void free_matrix(int **matrix, int rows) {
  for (int i = 0; i < rows; i++) {
    free(matrix[i]);
  }
  free(matrix);
}

void userInput(TetrisState_t *state, UserAction_t action, bool hold) {
  bool input_processed = false;

  if (state->info.pause) {
    if (action == Pause) {
      state->info.pause = false;
      input_processed = true;
    } else if (action == Terminate) {
      state->game_active = false;
      state->current_state = GameOverState;
      input_processed = true;
    }
  } else if (!state->current.is_locked && !hold) {
    switch (action) {
      case Left:
        try_move(state, -1, 0);
        break;
      case Right:
        try_move(state, 1, 0);
        break;
      case Down:
        hard_drop(state);
        break;
      case Action:
        try_rotate(state);
        break;
      case Start:
        if (state->current_state == StartState ||
            state->current_state == GameOverState) {
          game_init(state);
        }
        break;
      case Pause:
        if (state->current_state != StartState &&
            state->current_state != GameOverState) {
          state->info.pause = true;
        }
        break;
      case Terminate:
        state->game_active = false;
        state->current_state = GameOverState;
        break;
      default:
        break;
    }
    input_processed = true;
  }

  (void)input_processed;
}

// Получение текущего состояния игры
void fsm_handle_state(TetrisState_t *state) {
  switch (state->current_state) {
    case StartState:
      start_operate(state);
      break;
    case SpawnState:
      spawn_operate(state);
      break;
    case MovingState:
      moving_operate(state);
      break;
    case ShiftingState:
      shifting_operate(state);
      break;
    case AttachingState:
      attaching_operate(state);
      break;
    case GameOverState:
      gameover_operate(state);
      break;
    default:
      break;
  }
}

UserAction_t convert_key(int ch) {
  UserAction_t action = (UserAction_t)-1;

  switch (ch) {
    case KEY_LEFT:
      action = Left;
      break;
    case KEY_RIGHT:
      action = Right;
      break;
    case KEY_UP:
      action = Up;
      break;
    case KEY_DOWN:
      action = Down;
      break;
    case ' ':
      action = Action;
      break;
    case 'p':
    case 'P':
      action = Pause;
      break;
    case 'q':
    case 'Q':
      action = Terminate;
      break;
    default:
      action = (UserAction_t)-1;
  }

  return action;
}

GameInfo_t updateCurrentState(UserAction_t action, TetrisState_t *state) {
  userInput(state, action, false);

  fsm_handle_state(state);

  GameInfo_t info_copy = state->info;

  info_copy.field = state->info.field;
  info_copy.next = state->info.next;

  return info_copy;
}
