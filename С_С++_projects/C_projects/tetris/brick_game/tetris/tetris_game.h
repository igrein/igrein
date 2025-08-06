#ifndef TETRIS_GAME_H
#define TETRIS_GAME_H

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

#define HEIGHT 20
#define WIDTH 10
#define FIGURE_SIZE 4

#define MAX_SPEED 1000
#define LEVEL_SPEED_STEP 100
#define MIN_SPEED 100

#define POINTS_FOR_LEVEL 600
#define MAX_LEVEL 10
#define LINE_SCORES \
  { 0, 100, 300, 700, 1500 }

#define LOCK_DELAY_MS 500

typedef enum UserAction_t {
  Start,
  Pause,
  Terminate,
  Left,
  Right,
  Up,
  Down,
  Action
} UserAction_t;

typedef struct GameInfo_t {
  int **field;
  int **next;
  int score;
  int high_score;
  int level;
  int speed;
  bool pause;
} GameInfo_t;

typedef enum GameState_t {
  StartState,
  SpawnState,
  MovingState,
  ShiftingState,
  AttachingState,
  GameOverState
} GameState_t;

typedef struct TetrisFigure_t {
  int x, y;
  int matrix[FIGURE_SIZE][FIGURE_SIZE];
  int width, height;
  int type;
  bool is_locked;  // new
} TetrisFigure_t;

typedef struct TetrisState_t {
  GameState_t current_state;
  TetrisFigure_t current;
  TetrisFigure_t next;
  UserAction_t last_action;
  bool game_active;
  GameInfo_t info;
  int lines_cleared;
  struct timeval last_fall;
  struct timeval lock_timer;
} TetrisState_t;

static const int tetris_figure[7][FIGURE_SIZE][FIGURE_SIZE] = {
    {{1, 1, 0, 0}, {1, 1, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // O
    {{1, 0, 0, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // J
    {{0, 0, 1, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // L
    {{1, 1, 1, 1}, {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // I
    {{0, 1, 1, 0}, {1, 1, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // S
    {{1, 1, 0, 0}, {0, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // Z
    {{0, 1, 0, 0}, {1, 1, 1, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}},  // T
};

static const struct {
  int width;
  int height;
} figure_sizes[7] = {
    {2, 2},  // O
    {3, 2},  // J
    {3, 2},  // L
    {4, 1},  // I
    {3, 2},  // S
    {3, 2},  // Z
    {3, 2}   // T
};

// Работа с состояниями игры
void start_operate(TetrisState_t *state);
void spawn_operate(TetrisState_t *state);
void moving_operate(TetrisState_t *state);
void shifting_operate(TetrisState_t *state);
void attaching_operate(TetrisState_t *state);
void gameover_operate(TetrisState_t *state);

//  Работа с фигурами
void generate_next_figure(TetrisState_t *state);
bool can_place_figure(const TetrisState_t *state, int shiftX, int shiftY);
bool try_move(TetrisState_t *state, int shiftX, int shiftY);
void try_rotate(TetrisState_t *state);
void hard_drop(TetrisState_t *state);

// Логика игры
void attach_to_field(TetrisState_t *state);
int clear_completed_lines(TetrisState_t *state);
void update_score_level(TetrisState_t *state, int lines);
void reset_fall_timer(TetrisState_t *state);
int is_time_to_fall(const TetrisState_t *state);
void update_next_preview(TetrisState_t *state);
void save_high_score(const GameInfo_t *info);
void load_high_score(GameInfo_t *info);
int is_game_over(const TetrisState_t *state);
void update_lock_timer(TetrisState_t *state);

// Начало и пользовательский ввод
void game_init(TetrisState_t *state);
void game_terminate(TetrisState_t *state);
int **create_matrix(int rows, int cols);
void free_matrix(int **matrix, int rows);
void userInput(TetrisState_t *state, UserAction_t action, bool hold);

// Получение текущего состояния игры
GameInfo_t updateCurrentState(UserAction_t action, TetrisState_t *state);
void fsm_handle_state(TetrisState_t *state);
UserAction_t convert_key(int ch);

#endif
