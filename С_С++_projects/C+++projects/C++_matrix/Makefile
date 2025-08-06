CXX = g++
CXXFLAGS = -std=c++20 -Wall -Wextra -Werror -Wpedantic -g
GTEST_FLAGS = -lgtest -lgtest_main -pthread

LIBRARY = s21_matrix_oop.a
TEST_EXECUTABLE = test
SOURCES = s21_matrix_oop.cpp
OBJECTS = s21_matrix_oop.o
TEST_SOURCE = tests.cpp

all: $(LIBRARY) test

$(LIBRARY): $(OBJECTS)
	ar rcs $(LIBRARY) $(OBJECTS)
	ranlib $(LIBRARY)


s21_matrix_oop.o: s21_matrix_oop.cpp s21_matrix_oop.h
	$(CXX) $(CXXFLAGS) -c s21_matrix_oop.cpp -o s21_matrix_oop.o

test: $(LIBRARY)
	$(CXX) $(CXXFLAGS) $(TEST_SOURCE) $(LIBRARY) $(GTEST_FLAGS) -o $(TEST_EXECUTABLE)
	./$(TEST_EXECUTABLE)

clean:
	rm -rf $(LIBRARY) $(TEST_EXECUTABLE) $(OBJECTS) *.gcda *.gcno report test.info tests.o *.out *.gcov

gcov_report: clean
	$(CXX) $(CXXFLAGS) --coverage -c s21_matrix_oop.cpp -o s21_matrix_oop.o
	$(CXX) $(CXXFLAGS) --coverage -c $(TEST_SOURCE) -o tests.o
	$(CXX) s21_matrix_oop.o tests.o --coverage $(GTEST_FLAGS) -o $(TEST_EXECUTABLE)
	./$(TEST_EXECUTABLE)
	lcov -c -d . -o test.info --include '*/s21_matrix_oop.cpp'
	genhtml -o report test.info

check: test
	cppcheck --language=c++ --enable=all --suppress=missingIncludeSystem .
	valgrind --leak-check=full --track-origins=yes ./$(TEST_EXECUTABLE)

.PHONY: all test clean gcov_report check style
