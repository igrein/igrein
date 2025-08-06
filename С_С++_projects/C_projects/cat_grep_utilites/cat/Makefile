CC = gcc 
GFLAGS = -Wall -Werror -Wextra - std =c11

s21_cat: s21_cat.o common.o 
	$(CC) $(CFLAGS) s21_cat.o common.o -o s21_cat

s21_cat.o: s21_cat.c s21_cat.h 
	$(CC) $(CFLAGS) -c s21_cat.c

common.o: ../common/common.c ../common/common.h 
	$(CC) $(CFLAGS) -c ../common/common.c 
    
clean:
	rm -rf *.o s21_cat
