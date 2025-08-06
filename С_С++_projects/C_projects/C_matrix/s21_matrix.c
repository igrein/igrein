#include "./s21_matrix.h"

// Создание матриц (create_matrix)
int s21_create_matrix(int rows, int columns, matrix_t *result) {
  if (rows <= 0 || columns <= 0 || !result) {
    return 1;
  }

  int error = 0;
  int i = 0;

  result->matrix = (double **)malloc(rows * sizeof(double *));
  error = !result->matrix;

  if (!error) {
    result->rows = rows;
    result->columns = columns;

    for (i = 0; i < rows && !error; i++) {
      result->matrix[i] = (double *)malloc(columns * sizeof(double));
      error = !result->matrix[i];
      if (!error) {
        memset(result->matrix[i], 0, columns * sizeof(double));
      }
    }
  }

  if (error && result->matrix) {
    for (int j = 0; j < i; j++) free(result->matrix[j]);
    free(result->matrix);
    result->matrix = NULL;
  }

  if (error) {
    result->rows = 0;
    result->columns = 0;
  }

  return error;
}

// Очистка матриц (remove_matrix)
void s21_remove_matrix(matrix_t *A) {
  if (A) {
    if (A->matrix && A->rows > 0) {
      for (int i = 0; i < A->rows; i++) {
        free(A->matrix[i]);
      }
      free(A->matrix);
      A->matrix = NULL;
    }
    A->rows = 0;
    A->columns = 0;
  }
}

// Сравнение матриц (eq_matrix)
int s21_eq_matrix(matrix_t *A, matrix_t *B) {
  if (A == NULL || B == NULL || A->matrix == NULL || B->matrix == NULL ||
      A->rows <= 0 || A->columns <= 0 || B->rows <= 0 || B->columns <= 0 ||
      A->columns != B->columns || A->rows != B->rows) {
    return FAILURE;
  }

  int error = 1;

  for (int i = 0; i < A->rows; i++) {
    for (int j = 0; j < A->columns; j++) {
      if (fabs(A->matrix[i][j] - B->matrix[i][j]) > 1e-7) {
        error = 0;
      }
    }
  }

  return (error == 1) ? SUCCESS : FAILURE;
}

// Складывание (sum_matrix) и вычитание матриц (sub_matrix)

int s21_sum_matrix(matrix_t *A, matrix_t *B, matrix_t *result) {
  if (A == NULL || B == NULL || result == NULL || A->matrix == NULL ||
      B->matrix == NULL || A->rows <= 0 || A->columns <= 0 || B->rows <= 0 ||
      B->columns <= 0) {
    return 1;
  }

  int error = 0;

  if (A->rows != B->rows || A->columns != B->columns) {
    error = 2;
  } else {
    error = s21_create_matrix(A->rows, A->columns, result);
  }

  if (!error) {
    for (int i = 0; i < A->rows; i++) {
      for (int j = 0; j < A->columns; j++) {
        result->matrix[i][j] = A->matrix[i][j] + B->matrix[i][j];
      }
    }
  }

  return error;
}

int s21_sub_matrix(matrix_t *A, matrix_t *B, matrix_t *result) {
  if (A == NULL || B == NULL || result == NULL || A->matrix == NULL ||
      B->matrix == NULL || A->rows <= 0 || A->columns <= 0 || B->rows <= 0 ||
      B->columns <= 0) {
    return 1;
  }

  int error = 0;

  if (A->rows != B->rows || A->columns != B->columns) {
    error = 2;
  } else {
    error = s21_create_matrix(A->rows, A->columns, result);
  }

  if (!error) {
    for (int i = 0; i < A->rows; i++) {
      for (int j = 0; j < A->columns; j++) {
        result->matrix[i][j] = A->matrix[i][j] - B->matrix[i][j];
      }
    }
  }

  return error;
}

// Умножение матрицы на скаляр (mult_number).
// Умножение двух матриц (mult_matrix)

int s21_mult_number(matrix_t *A, double number, matrix_t *result) {
  if (A == NULL || A->matrix == NULL || result == NULL || A->rows <= 0 ||
      A->columns <= 0) {
    return 1;
  }

  int error = 0;

  error = s21_create_matrix(A->rows, A->columns, result);

  if (!error) {
    for (int i = 0; i < result->rows; i++) {
      for (int j = 0; j < result->columns; j++) {
        result->matrix[i][j] = A->matrix[i][j] * number;
        error = isinf(result->matrix[i][j]) ? 2 : 0;
      }
    }
  }

  if (error == 2) {
    s21_remove_matrix(result);
  }

  return error;
}

int s21_mult_matrix(matrix_t *A, matrix_t *B, matrix_t *result) {
  if (A == NULL || B == NULL || A->matrix == NULL || B->matrix == NULL ||
      result == NULL || A->rows <= 0 || A->columns <= 0 || B->rows <= 0 ||
      B->columns <= 0) {
    return 1;
  }

  int error = 0;

  if (A->columns != B->rows) {
    error = 2;
  }

  if (!error) {
    error = s21_create_matrix(A->rows, B->columns, result);
  }

  if (!error) {
    for (int i = 0; i < A->rows; i++) {
      for (int j = 0; j < B->columns; j++) {
        result->matrix[i][j] = 0;

        for (int k = 0; k < A->columns; k++) {
          result->matrix[i][j] += A->matrix[i][k] * B->matrix[k][j];
        }
      }
    }
  }

  return error;
}

// Транспонирование матрицы (transpose)
int s21_transpose(matrix_t *A, matrix_t *result) {
  if (A == NULL || A->matrix == NULL || result == NULL || A->rows <= 0 ||
      A->columns <= 0) {
    return 1;
  }

  int error = 0;

  error = s21_create_matrix(A->columns, A->rows, result);

  if (!error) {
    for (int i = 0; i < A->rows; i++) {
      for (int j = 0; j < A->columns; j++) {
        result->matrix[j][i] = A->matrix[i][j];
      }
    }
  }

  return error;
}

// Минор матрицы и матрица алгебраических дополнений (calc_complements)
int s21_calc_complements(matrix_t *A, matrix_t *result) {
  int error = 0;

  if (A == NULL || A->matrix == NULL || result == NULL) {
    return 1;
  }

  if (!error && A->columns != A->rows) {
    error = 2;
  }

  if (!error) {
    int create_status = s21_create_matrix(A->rows, A->columns, result);
    if (create_status != 0) {
      error = create_status;
    }
  }

  if (!error && A->rows == 1) {
    result->matrix[0][0] = 1.0;
  }

  for (int i = 0; !error && i < A->rows && A->rows > 1; i++) {
    for (int j = 0; j < A->rows; j++) {
      matrix_t minor;
      int minor_status = s21_create_matrix(A->rows - 1, A->rows - 1, &minor);
      if (minor_status != 0) {
        s21_remove_matrix(result);
        error = minor_status;
        break;
      }

      for (int y = 0, mi = 0; y < A->rows; y++) {
        if (y == i) continue;
        for (int x = 0, mj = 0; x < A->rows; x++) {
          if (x == j) continue;
          minor.matrix[mi][mj++] = A->matrix[y][x];
        }
        mi++;
      }

      if (!error) {
        double det = 0;
        s21_determinant(&minor, &det);
        int sign = ((i + j) % 2 == 0) ? 1 : -1;
        result->matrix[i][j] = sign * det;
      }

      s21_remove_matrix(&minor);
    }
  }

  return error;
}

// Матричный определитель
int s21_determinant(matrix_t *A, double *result) {
  int error = 0;
  double det = 1.0;

  if (A == NULL || A->matrix == NULL || result == NULL) {
    return 1;
  }

  if (!error && A->columns != A->rows) {
    error = 2;
  }

  matrix_t temp;
  if (!error) {
    error = s21_create_matrix(A->rows, A->columns, &temp);
  }

  if (!error) {
    for (int i = 0; i < A->rows; i++) {
      for (int j = 0; j < A->rows; j++) {
        temp.matrix[i][j] = A->matrix[i][j];
      }
    }

    for (int i = 0; i < A->rows && det != 0; i++) {
      int max_row = i;
      for (int k = i + 1; k < A->rows; k++) {
        if (fabs(temp.matrix[k][i]) > fabs(temp.matrix[max_row][i])) {
          max_row = k;
        }
      }

      if (fabs(temp.matrix[max_row][i]) < 1e-12) {
        det = 0;
        break;
      }

      if (max_row != i) {
        double *swap = temp.matrix[i];
        temp.matrix[i] = temp.matrix[max_row];
        temp.matrix[max_row] = swap;
        det *= -1;
      }

      for (int k = i + 1; k < A->rows; k++) {
        double factor = temp.matrix[k][i] / temp.matrix[i][i];
        for (int j = i; j < A->rows; j++) {
          temp.matrix[k][j] -= factor * temp.matrix[i][j];
        }
      }

      det *= temp.matrix[i][i];
    }

    *result = det;
  }

  if (!error) {
    s21_remove_matrix(&temp);
  }

  return error;
}

// Обратная матрица (inverse_matrix)
int s21_inverse_matrix(matrix_t *A, matrix_t *result) {
  int error = 0;
  double det = 0.0;

  if (A == NULL || A->matrix == NULL || result == NULL) {
    return 1;
  }

  if (!error && A->columns != A->rows) {
    error = 2;
  }

  if (!error) {
    error = s21_determinant(A, &det);
  }

  if (!error && fabs(det) < 1e-7) {
    error = 2;
  }

  matrix_t complements;
  if (!error) {
    error = s21_calc_complements(A, &complements);
  }

  matrix_t adjugate;
  if (!error) {
    error = s21_transpose(&complements, &adjugate);
    s21_remove_matrix(&complements);
  }

  if (!error) {
    double inv_det = 1.0 / det;
    error = s21_mult_number(&adjugate, inv_det, result);
    s21_remove_matrix(&adjugate);
  }

  return error;
}
