CC = gcc
CFLAGS = -std=c11 -Wall -Werror -Wextra
TEST_FLAGS = -lcheck -lm -lpthread -lsubunit
GCOV_FLAGS = -fprofile-arcs -ftest-coverage
LIB_NAME = s21_matrix.a

$(LIB_NAME): s21_matrix.o
	ar rcs $(LIB_NAME) s21_matrix.o
	ranlib $(LIB_NAME)

s21_matrix.o: s21_matrix.c s21_matrix.h
	$(CC) $(CFLAGS) $(GCOV_FLAGS) -c s21_matrix.c

test_build: $(LIB_NAME)
	$(CC) $(CFLAGS) test.c $(LIB_NAME) -o test $(TEST_FLAGS) $(GCOV_FLAGS)

test: test_build
	./test

gcov_report: test
	-lcov -t "s21_matrix" -o coverage.info -c -d .
	-genhtml -o report coverage.info
	-xdg-open report/index.html

clean:
	rm -rf *.o *.a *.gcno *.gcda *.info report test .vscode

all: $(LIB_NAME) test gcov_report
