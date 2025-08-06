#include <check.h>
#include <limits.h>

#include "./s21_matrix.h"

START_TEST(test_create_matrix) {
  // Корректное создание
  matrix_t mat1 ={0};
  int res1 = s21_create_matrix(3, 4, &mat1);
  ck_assert_int_eq(res1, 0);
  ck_assert_int_eq(mat1.rows, 3);
  ck_assert_int_eq(mat1.columns, 4);
  ck_assert_ptr_nonnull(mat1.matrix);

  // Проверка инициализации нулями
  for (int i = 0; i < 3; i++) {
    for (int j = 0; j < 4; j++) {
      ck_assert_double_eq_tol(mat1.matrix[i][j], 0.0, 1e-6);
    }
  }
  s21_remove_matrix(&mat1);

//   Отрицательные строки
  matrix_t mat2 ={0};
  int res2 = s21_create_matrix(-2, 5, &mat2);
  ck_assert_int_eq(res2, 1);

//   Нулевые столбцы
  matrix_t mat3;
  int res3 = s21_create_matrix(3, 0, &mat3);
  ck_assert_int_eq(res3, 1);

//    NULL результат
  int res4 = s21_create_matrix(3, 3, NULL);
  ck_assert_int_eq(res4, 1);

  }
END_TEST

START_TEST(test_remove_matrix) {
  // Нормальное освобождение
  matrix_t m1;
  s21_create_matrix(3, 3, &m1);
  s21_remove_matrix(&m1);
  ck_assert_ptr_eq(m1.matrix, NULL);
  ck_assert_int_eq(m1.rows, 0);
  ck_assert_int_eq(m1.columns, 0);

  // Передача NULL
  s21_remove_matrix(NULL);

  // Очистка уже очищенной матрицы
  matrix_t m2 = {0};
  s21_remove_matrix(&m2);
  ck_assert_int_eq(m2.rows, 0);
  ck_assert_int_eq(m2.columns, 0);

  // Корректная очистка с невалидным указателем
  matrix_t m3 = {.matrix = NULL, .rows = 0, .columns = 0};
  s21_remove_matrix(&m3);
  ck_assert_int_eq(m3.rows, 0);
  ck_assert_int_eq(m3.columns, 0);
}
END_TEST

START_TEST(test_eq_matrix) {
  // Идентичные матрицы
  matrix_t A, B;
  s21_create_matrix(2, 2, &A);
  s21_create_matrix(2, 2, &B);
  A.matrix[0][0] = 1.0;
  A.matrix[0][1] = 2.0;
  A.matrix[1][0] = 3.0;
  A.matrix[1][1] = 4.0;
  B.matrix[0][0] = 1.0;
  B.matrix[0][1] = 2.0;
  B.matrix[1][0] = 3.0;
  B.matrix[1][1] = 4.0;
  ck_assert_int_eq(s21_eq_matrix(&A, &B), SUCCESS);
  s21_remove_matrix(&A);
  s21_remove_matrix(&B);

  // Разные размеры
  matrix_t C, D;
  s21_create_matrix(2, 2, &C);
  s21_create_matrix(3, 3, &D);
  ck_assert_int_eq(s21_eq_matrix(&C, &D), FAILURE);
  s21_remove_matrix(&C);
  s21_remove_matrix(&D);

  // Сравнение с погрешностью 1e-9
  matrix_t E, F;
  s21_create_matrix(1, 1, &E);
  s21_create_matrix(1, 1, &F);
  E.matrix[0][0] = 0.123456789;
  F.matrix[0][0] = 0.123456788;
  ck_assert_int_eq(s21_eq_matrix(&E, &F), SUCCESS);
  s21_remove_matrix(&E);
  s21_remove_matrix(&F);

  // NULL вход
  matrix_t G;
  s21_create_matrix(2, 2, &G);
  ck_assert_int_eq(s21_eq_matrix(NULL, &G), FAILURE);
  ck_assert_int_eq(s21_eq_matrix(&G, NULL), FAILURE);
  s21_remove_matrix(&G);

  // Неинициализированные матрицы
  matrix_t H = {0}, I = {0};
  ck_assert_int_eq(s21_eq_matrix(&H, &I), FAILURE);
}
END_TEST

START_TEST(test_sum_matrix) {
  // Корректное сложение
  matrix_t A, B, result;
  s21_create_matrix(2, 2, &A);
  s21_create_matrix(2, 2, &B);

  // Заполнение матриц
  A.matrix[0][0] = 1.5;
  A.matrix[0][1] = 2.5;
  A.matrix[1][0] = 3.5;
  A.matrix[1][1] = 4.5;

  B.matrix[0][0] = 0.5;
  B.matrix[0][1] = 1.5;
  B.matrix[1][0] = 2.5;
  B.matrix[1][1] = 3.5;

  int status = s21_sum_matrix(&A, &B, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 2.0, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], 8.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&B);
  s21_remove_matrix(&result);

  // Несовпадение размеров
  matrix_t C, D, result2;
  s21_create_matrix(2, 3, &C);
  s21_create_matrix(3, 2, &D);
  status = s21_sum_matrix(&C, &D, &result2);
  ck_assert_int_eq(status, 2);
  s21_remove_matrix(&C);
  s21_remove_matrix(&D);

  // NULL вход
  status = s21_sum_matrix(NULL, &D, &result2);
  ck_assert_int_eq(status, 1);
}
END_TEST

START_TEST(test_sub_matrix) {
  // Корректное вычитание
  matrix_t A, B, result;
  s21_create_matrix(2, 2, &A);
  s21_create_matrix(2, 2, &B);

  A.matrix[0][0] = 5.0;
  A.matrix[0][1] = 7.0;
  A.matrix[1][0] = 9.0;
  A.matrix[1][1] = 11.0;

  B.matrix[0][0] = 1.0;
  B.matrix[0][1] = 2.0;
  B.matrix[1][0] = 3.0;
  B.matrix[1][1] = 4.0;

  int status = s21_sub_matrix(&A, &B, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 4.0, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], 7.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&B);
  s21_remove_matrix(&result);

  // Вычитание с отрицательными числами
  matrix_t C, D, result2;
  s21_create_matrix(1, 1, &C);
  s21_create_matrix(1, 1, &D);
  C.matrix[0][0] = -5.0;
  D.matrix[0][0] = 3.0;

  status = s21_sub_matrix(&C, &D, &result2);
  ck_assert_double_eq_tol(result2.matrix[0][0], -8.0, 1e-7);
  s21_remove_matrix(&C);
  s21_remove_matrix(&D);
  s21_remove_matrix(&result2);

  // Невалидные аргументы
  status = s21_sub_matrix(NULL, &D, &result2);
  ck_assert_int_eq(status, 1);
}
END_TEST

START_TEST(test_mult_number) {
  // Умножение на положительное число
  matrix_t A, result;
  s21_create_matrix(2, 2, &A);
  A.matrix[0][0] = 1.5;
  A.matrix[0][1] = 2.5;
  A.matrix[1][0] = 3.5;
  A.matrix[1][1] = 4.5;

  int status = s21_mult_number(&A, 2.0, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 3.0, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], 9.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&result);

  // Умножение на ноль
  s21_create_matrix(2, 2, &A);
  status = s21_mult_number(&A, 0.0, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 0.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&result);

  // Некорректная матрица
  status = s21_mult_number(NULL, 2.0, &result);
  ck_assert_int_eq(status, 1);

  matrix_t C = {0};
  s21_create_matrix(1, 1, &C);
  C.matrix[0][0] = DBL_MAX;

  // Умножение на 2 - переполнение
  status = s21_mult_number(&C, 2.0, &result);
  ck_assert_int_eq(status, 2);
  s21_remove_matrix(&C);
}
END_TEST

START_TEST(test_mult_matrix) {
  // Корректное умножение
  matrix_t A, B, result;
  s21_create_matrix(2, 3, &A);
  s21_create_matrix(3, 2, &B);

  A.matrix[0][0] = 1;
  A.matrix[0][1] = 2;
  A.matrix[0][2] = 3;
  A.matrix[1][0] = 4;
  A.matrix[1][1] = 5;
  A.matrix[1][2] = 6;

  B.matrix[0][0] = 7;
  B.matrix[0][1] = 8;
  B.matrix[1][0] = 9;
  B.matrix[1][1] = 10;
  B.matrix[2][0] = 11;
  B.matrix[2][1] = 12;

  int status = s21_mult_matrix(&A, &B, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 58, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], 154, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&B);
  s21_remove_matrix(&result);

  // Несовместимые размеры
  matrix_t C, D, result2;
  s21_create_matrix(2, 2, &C);
  s21_create_matrix(3, 2, &D);
  status = s21_mult_matrix(&C, &D, &result2);
  ck_assert_int_eq(status, 2);
  s21_remove_matrix(&C);
  s21_remove_matrix(&D);

  // Умножение на NULL
  status = s21_mult_matrix(NULL, &D, &result2);
  ck_assert_int_eq(status, 1);
}
END_TEST

START_TEST(test_transpose) {
  // Транспонирование прямоугольной матрицы 2x3
  matrix_t A, result;
  s21_create_matrix(2, 3, &A);
  A.matrix[0][0] = 1;
  A.matrix[0][1] = 2;
  A.matrix[0][2] = 3;
  A.matrix[1][0] = 4;
  A.matrix[1][1] = 5;
  A.matrix[1][2] = 6;

  int status = s21_transpose(&A, &result);
  ck_assert_int_eq(status, 0);
  ck_assert_int_eq(result.rows, 3);
  ck_assert_int_eq(result.columns, 2);
  ck_assert_double_eq_tol(result.matrix[0][0], 1.0, 1e-7);
  ck_assert_double_eq_tol(result.matrix[2][1], 6.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&result);

  // Транспонирование матрицы 1x1
  matrix_t B, result2;
  s21_create_matrix(1, 1, &B);
  B.matrix[0][0] = 42.0;

  status = s21_transpose(&B, &result2);
  ck_assert_int_eq(status, 0);
  ck_assert_double_eq_tol(result2.matrix[0][0], 42.0, 1e-7);
  s21_remove_matrix(&B);
  s21_remove_matrix(&result2);

  // Некорректная матрица
  status = s21_transpose(NULL, &result);
  ck_assert_int_eq(status, 1);
}
END_TEST

START_TEST(test_determinant) {
  // Матрица 1x1
  matrix_t A1;
  s21_create_matrix(1, 1, &A1);
  A1.matrix[0][0] = -5.5;
  double det;
  ck_assert_int_eq(s21_determinant(&A1, &det), 0);
  ck_assert_double_eq_tol(det, -5.5, 1e-7);
  s21_remove_matrix(&A1);

  // Матрица 2x2
  matrix_t A2;
  s21_create_matrix(2, 2, &A2);
  double data2[2][2] = {{3.1, 1.2}, {2.5, 4.0}};
  for (int i = 0; i < 2; i++)
    memcpy(A2.matrix[i], data2[i], sizeof(double) * 2);
  ck_assert_int_eq(s21_determinant(&A2, &det), 0);
  ck_assert_double_eq_tol(det, (3.1 * 4.0 - 1.2 * 2.5), 1e-7);
  s21_remove_matrix(&A2);

  // Вырожденная матрица 3x3 (det = 0)
  matrix_t A3;
  s21_create_matrix(3, 3, &A3);
  double data3[3][3] = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};
  for (int i = 0; i < 3; i++)
    memcpy(A3.matrix[i], data3[i], sizeof(double) * 3);
  ck_assert_int_eq(s21_determinant(&A3, &det), 0);
  ck_assert_double_eq_tol(det, 0.0, 1e-7);
  s21_remove_matrix(&A3);

  // Некорректные данные
  matrix_t A4;
  s21_create_matrix(2, 3, &A4);
  ck_assert_int_eq(s21_determinant(&A4, &det), 2);
  s21_remove_matrix(&A4);
  ck_assert_int_eq(s21_determinant(NULL, &det), 1);
}
END_TEST

START_TEST(test_calc_complements) {
  // Матрица 2x2
  matrix_t A1 = {0};
  matrix_t result1 = {0};
  s21_create_matrix(2, 2, &A1);
  double data1[2][2] = {{1.0, 2.0}, {3.0, 4.0}};
  for (int i = 0; i < 2; i++)
    memcpy(A1.matrix[i], data1[i], sizeof(double) * 2);

  ck_assert_int_eq(s21_calc_complements(&A1, &result1), 0);
  ck_assert_double_eq_tol(result1.matrix[0][0], 4.0, 1e-7);
  ck_assert_double_eq_tol(result1.matrix[0][1], -3.0, 1e-7);
  ck_assert_double_eq_tol(result1.matrix[1][0], -2.0, 1e-7);
  ck_assert_double_eq_tol(result1.matrix[1][1], 1.0, 1e-7);
  s21_remove_matrix(&A1);
  s21_remove_matrix(&result1);

  // Матрица 1x1 (дополнение = 1)
  matrix_t A2 = {0};
  matrix_t result2 = {0};
  s21_create_matrix(1, 1, &A2);
  A2.matrix[0][0] = 5.0;
  ck_assert_int_eq(s21_calc_complements(&A2, &result2), 0);
  ck_assert_double_eq_tol(result2.matrix[0][0], 1.0, 1e-7);
  s21_remove_matrix(&A2);
  s21_remove_matrix(&result2);

  // Некорректные данные
  matrix_t A3 = {0};
  s21_create_matrix(2, 3, &A3);
  matrix_t result3 = {0};
  ck_assert_int_eq(s21_calc_complements(&A3, &result3), 2);
  s21_remove_matrix(&A3);
  ck_assert_int_eq(s21_calc_complements(NULL, &result3), 1);

  matrix_t A = {0};
  matrix_t result = {0};
  s21_create_matrix(3, 3, &A);
  double data[3][3] = {{2, 5, 7}, {6, 3, 4}, {5, -2, -3}};
  for (int i = 0; i < 3; i++) memcpy(A.matrix[i], data[i], sizeof(double) * 3);

  ck_assert_int_eq(s21_calc_complements(&A, &result), 0);
  ck_assert_double_eq_tol(result.matrix[0][0], -1.0, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], -41.0, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&result);
}
END_TEST

START_TEST(test_inverse_matrix) {
  // Матрица 2x2
  matrix_t A, result;
  s21_create_matrix(2, 2, &A);
  double data[2][2] = {{4, 7}, {2, 6}};
  for (int i = 0; i < 2; i++) memcpy(A.matrix[i], data[i], sizeof(double) * 2);

  ck_assert_int_eq(s21_inverse_matrix(&A, &result), 0);
  ck_assert_double_eq_tol(result.matrix[0][0], 0.6, 1e-7);
  ck_assert_double_eq_tol(result.matrix[0][1], -0.7, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][0], -0.2, 1e-7);
  ck_assert_double_eq_tol(result.matrix[1][1], 0.4, 1e-7);
  s21_remove_matrix(&A);
  s21_remove_matrix(&result);

  // Матрица 1x1
  matrix_t A1, result1;
  s21_create_matrix(1, 1, &A1);
  A1.matrix[0][0] = 5.0;
  ck_assert_int_eq(s21_inverse_matrix(&A1, &result1), 0);
  ck_assert_double_eq_tol(result1.matrix[0][0], 0.2, 1e-7);
  s21_remove_matrix(&A1);
  s21_remove_matrix(&result1);

  // Вырожденная матрица (det = 0)
  matrix_t A2;
  s21_create_matrix(2, 2, &A2);
  double data2[2][2] = {{1, 2}, {2, 4}};
  for (int i = 0; i < 2; i++)
    memcpy(A2.matrix[i], data2[i], sizeof(double) * 2);
  ck_assert_int_eq(s21_inverse_matrix(&A2, &result), 2);
  s21_remove_matrix(&A2);

  // Некорректные данные
  matrix_t A3;
  s21_create_matrix(2, 3, &A3);
  ck_assert_int_eq(s21_inverse_matrix(&A3, &result), 2);
  s21_remove_matrix(&A3);
  ck_assert_int_eq(s21_inverse_matrix(NULL, &result), 1);
}
END_TEST

Suite *matrix_suite(void) {
  Suite *s = suite_create("Matrix Create");
  TCase *tc = tcase_create("Core");

  tcase_add_test(tc, test_create_matrix);
  tcase_add_test(tc, test_remove_matrix);
  tcase_add_test(tc, test_eq_matrix);
  tcase_add_test(tc, test_sum_matrix);
  tcase_add_test(tc, test_sub_matrix);
  tcase_add_test(tc, test_mult_number);
  tcase_add_test(tc, test_mult_matrix);
  tcase_add_test(tc, test_transpose);
  tcase_add_test(tc, test_determinant);
  tcase_add_test(tc, test_calc_complements);
  tcase_add_test(tc, test_inverse_matrix);

  suite_add_tcase(s, tc);

  return s;
}

int main(void) {
  int failures;
  Suite *s = matrix_suite();
  SRunner *sr = srunner_create(s);

  srunner_run_all(sr, CK_VERBOSE);
  failures = srunner_ntests_failed(sr);
  srunner_free(sr);

  return (failures == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
