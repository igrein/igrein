#ifndef S21_CAT_H
#define S21_CAT_H

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <unistd.h>

#include "../common/common.h"

typedef struct {
  bool b_flag;
  bool e_flag;
  bool E_flag;
  bool n_flag;
  bool s_flag;
  bool t_flag;
  bool T_flag;
  bool v_flag;
} Flags;

static void parse_args(Flags* flags, int argc, char* argv[]);
static void cat_file(const Flags* flags, FILE* fp);
static void print_with_flag(char* line, const Flags* flags, int* line_number,
                            int* previous_line_was_empty, int is_empty);

#endif
