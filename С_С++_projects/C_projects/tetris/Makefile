CC = gcc
CFLAGS = -g -Wall -Werror -Wextra -std=c11 -fsanitize=address -fsanitize=leak
LDFLAGS = -lncursesw
GCOV_FLAGS = -fprofile-arcs -ftest-coverage

OS = Linux

ifeq ($(OS), Linux)
	CHECK_FLAG = -lcheck -lm -lpthread -lsubunit
else
	CHECK_FLAG = -lcheck -lm -lpthread
endif

GAME_SRC = ./brick_game/tetris/tetris_game.c
INT_SRC = ./gui/cli/tetris_interface.c
TEST_SRC = ./tests/test_tetris.c
MAIN_SRC = ./main.c

GAME_OBJ = $(GAME_SRC:.c=.o)
INT_OBJ = $(INT_SRC:.c=.o)
TEST_OBJ = $(TEST_SRC:.c=.o)
MAIN_OBJ = $(MAIN_SRC:.c=.o)

# Объектные файлы для тестов (с gcov)
GAME_OBJ_GCOV = $(GAME_SRC:.c=.gcov.o)
INT_OBJ_GCOV = $(INT_SRC:.c=.gcov.o)
TEST_OBJ_GCOV = $(TEST_SRC:.c=.gcov.o)

DIST_DIRECT = ./dist_tmp
INSTALL_DIR = ../tetris_game_start

DOC_DIR = documentation
DOC_FILE = Documentation.html
DOC_FILES = $(DOC_DIR)/$(DOC_FILE) $(DOC_DIR)/tetris.png

.PHONY: all clean install uninstall test dist dvi gcov_report

# Правило для обычной компиляции
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Правило для компиляции с gcov
%.gcov.o: %.c
	$(CC) $(CFLAGS) $(GCOV_FLAGS) -c $< -o $@

all: install

TETRIS_LIB = tetris_game.a
$(TETRIS_LIB): $(GAME_OBJ) $(INT_OBJ)
	ar rcs $@ $^
	ranlib $@

TETRIS_LIB_GCOV = tetris_game_gcov.a
$(TETRIS_LIB_GCOV): $(GAME_OBJ_GCOV) $(INT_OBJ_GCOV)
	ar rcs $@ $^
	ranlib $@

install: $(MAIN_OBJ) $(TETRIS_LIB)
	mkdir -p $(INSTALL_DIR)
	$(CC) $(CFLAGS) $^ -o tetris $(LDFLAGS)
	mv tetris $(INSTALL_DIR)/

uninstall: clean
	rm -f $(INSTALL_DIR)/tetris
	rm -rf $(INSTALL_DIR)/high_score.txt
	rm -rf $(INSTALL_DIR)

clean:
	rm -f $(GAME_OBJ) $(INT_OBJ) $(TEST_OBJ) $(MAIN_OBJ) $(TETRIS_LIB)
	rm -f $(GAME_OBJ_GCOV) $(INT_OBJ_GCOV) $(TEST_OBJ_GCOV) $(TETRIS_LIB_GCOV)
	rm -f ./tests/test_tetris
	rm -f ./*.gcda ./*.gcno coverage.info coverage_filtered.info
	rm -rf ./out
	rm -f ../../brick_game.tar.gz
	rm -f ./*.gcov ./tests/*.gcda ./tests/*.gcno 
	rm -f ./gui/cli/*.gcda ./gui/cli/*.gcno 
	rm -f ./brick_game/tetris/*.gcda ./brick_game/tetris/*.gcno
	rm -rf high_score.txt

dvi:
	@xdg-open "$(DOC_DIR)/$(DOC_FILE)" 2>/dev/null || open "$(DOC_DIR)/$(DOC_FILE)" 2>/dev/null || echo "Откройте документ вручную"

dist: clean
	mkdir -p $(DIST_DIRECT)
	cp -r brick_game gui *.c documentation/ ./dist_tmp
	tar -czf ../../brick_game.tar.gz -C $(DIST_DIRECT)/.. $(notdir $(DIST_DIRECT))
	rm -rf $(DIST_DIRECT)

test: $(GAME_OBJ_GCOV) $(INT_OBJ_GCOV) $(TEST_OBJ_GCOV)
	$(CC) $(CFLAGS) $(GCOV_FLAGS) $^ -o ./tests/test_tetris $(CHECK_FLAG) $(LDFLAGS) -lgcov
	./tests/test_tetris

gcov_report: test
	lcov --capture --directory . --output-file coverage.info
	lcov --remove coverage.info '*test_tetris.c' '*interface.c' --output-file coverage_filtered.info
	genhtml coverage_filtered.info --output-directory out
	xdg-open out/index.html || open out/index.html
