#include "s21_cat.h"

int main(int argc, char* argv[]) {
  Flags flags = {false};
  int success = EXIT_SUCCESS;

  if (argc == 1 && !isatty(STDIN_FILENO)) {
    cat_file(&flags, stdin);
  } else {
    parse_args(&flags, argc, argv);

    for (int i = optind; i < argc; ++i) {
      FILE* fp = fopen(argv[i], "r");
      if (fp != NULL) {
        cat_file(&flags, fp);
        if (fclose(fp) != 0) {
          perror("Error closing file");
          success = EXIT_FAILURE;
        }
      } else {
        fprintf(stderr, "Error opening file %s: %s\n", argv[i],
                strerror(errno));
        success = EXIT_FAILURE;
      }
    }

    if (argc == 1) {
      PrintUsage(argv[0]);
      success = EXIT_FAILURE;
    }
  }

  return success;
}

static void parse_args(Flags* flags, int argc, char* argv[]) {
  int opt;
  while ((opt = getopt(argc, argv, "benstvTE")) != -1) {
    switch (opt) {
      case 'b':
        flags->b_flag = true;
        break;
      case 'e':
        flags->e_flag = true;
        flags->v_flag = true;
        break;
      case 'E':
        flags->E_flag = true;
        break;
      case 'n':
        flags->n_flag = true;
        break;
      case 's':
        flags->s_flag = true;
        break;
      case 't':
        flags->t_flag = true;
        flags->v_flag = true;
        break;
      case 'T':
        flags->T_flag = true;
        break;
      case 'v':
        flags->v_flag = true;
        break;
      default:
        PrintUsage(argv[0]);
        exit(EXIT_FAILURE);
    }
  }
}

static void cat_file(const Flags* flags, FILE* fp) {
  char* line = NULL;
  size_t len = 0;
  int previous_line_was_empty = 0;
  int line_number = 1;

  while (getline(&line, &len, fp) != -1) {
    int is_empty = (strcmp(line, "\n") == 0);

    print_with_flag(line, flags, &line_number, &previous_line_was_empty,
                    is_empty);

    free(line);
    line = NULL;
    len = 0;
  }

  if (line != NULL) {
    free(line);
  }
}

static void print_with_flag(char* line, const Flags* flags, int* line_number,
                            int* previous_line_was_empty, int is_empty) {
  if (is_empty) {
    if (!(*previous_line_was_empty) || !flags->s_flag) {
      if (flags->n_flag && !flags->b_flag) {
        printf("%6d\t", (*line_number)++);
      }
      if (flags->e_flag || flags->E_flag) {
        printf("$");
      }
      fputs(line, stdout);
    }
    *previous_line_was_empty = 1;
  } else {
    if (flags->b_flag) {
      printf("%6d\t", (*line_number)++);
    } else if (flags->n_flag) {
      printf("%6d\t", (*line_number)++);
    }

    if (flags->e_flag || flags->E_flag) {
      size_t line_len = strlen(line);
      if (line[line_len - 1] == '\n') {
        line[line_len - 1] = '\0';
        printf("%s$", line);
        printf("\n");
      } else {
        printf("%s$", line);
      }
    } else if (flags->t_flag || flags->T_flag) {
      for (size_t i = 0; line[i] != '\0'; ++i) {
        if (line[i] == '\t') {
          printf("^I");
        } else {
          putchar(line[i]);
        }
      }
    } else {
      fputs(line, stdout);
    }
    *previous_line_was_empty = 0;
  }
}
