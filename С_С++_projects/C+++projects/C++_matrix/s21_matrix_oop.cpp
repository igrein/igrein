#include "s21_matrix_oop.h"

// Параметризированный конструктор
S21Matrix::S21Matrix(int rows, int cols) {
  if (rows <= 0 || cols <= 0) {
    throw invalid_argument("Строки и столбцы не могут быть меньше 0");
  }

  double** new_matrix = nullptr;

  try {
    new_matrix = new double*[rows];
    for (int i = 0; i < rows; i++) {
      new_matrix[i] = new double[cols]();
    }
  } catch (const bad_alloc&) {
    if (new_matrix) {
      for (int j = 0; j < rows; j++) {
        delete[] new_matrix[j];
      }
      delete[] new_matrix;
    }
    throw;
  }

  rows_ = rows;
  cols_ = cols;
  matrix_ = new_matrix;
}

// Конструктор копирования
S21Matrix::S21Matrix(const S21Matrix& other)
    : rows_(0), cols_(0), matrix_(nullptr) {
  if (this == &other) return;

  if (other.matrix_ == nullptr) return;

  try {
    rows_ = other.rows_;
    cols_ = other.cols_;
    matrix_ = new double*[rows_];

    for (int i = 0; i < rows_; i++) {
      matrix_[i] = new double[cols_];
      copy(other.matrix_[i], other.matrix_[i] + cols_, matrix_[i]);
    }
  } catch (const bad_alloc&) {
    if (matrix_) {
      for (int j = 0; j < rows_; j++) {
        delete[] matrix_[j];
      }
      delete[] matrix_;
    }
    throw;
  }
}

// Конструктор переноса
S21Matrix::S21Matrix(S21Matrix&& other) {
  if (other.matrix_ == nullptr) return;

  if (this == &other) return;

  rows_ = other.rows_;
  cols_ = other.cols_;
  matrix_ = other.matrix_;

  other.rows_ = 0;
  other.cols_ = 0;
  other.matrix_ = nullptr;
}

// Сеттеры
void S21Matrix::SetRows(int new_rows) {
  if (new_rows < 0) {
    throw invalid_argument("Строки не могут быть меньше 0");
  }

  if (new_rows == rows_) {
    return;
  }

  double** new_matrix = nullptr;

  try {
    new_matrix = new double*[new_rows];

    int rows_to_copy = min(rows_, new_rows);

    for (int i = 0; i < rows_to_copy; ++i) {
      new_matrix[i] = new double[cols_];
      copy(matrix_[i], matrix_[i] + cols_, new_matrix[i]);
    }

    for (int i = rows_; i < new_rows; ++i) {
      new_matrix[i] = new double[cols_]();
    }

    for (int i = 0; i < rows_; ++i) {
      delete[] matrix_[i];
    }
    delete[] matrix_;

    matrix_ = new_matrix;
    rows_ = new_rows;
  } catch (const bad_alloc&) {
    if (new_matrix) {
      for (int j = 0; j < rows_; j++) {
        delete[] new_matrix[j];
      }
      delete[] new_matrix;
    }
    throw;
  }
}

void S21Matrix::SetCols(int new_cols) {
  if (new_cols < 0) {
    throw invalid_argument("Столбцы не могут быть меньше 0");
  }

  if (new_cols == cols_) {
    return;
  }

  double** new_matrix = nullptr;

  try {
    new_matrix = new double*[rows_];
    for (int i = 0; i < rows_; i++) {
      new_matrix[i] = new double[new_cols]();
    }

    int cols_to_copy = min(cols_, new_cols);

    for (int i = 0; i < rows_; ++i) {
      copy(matrix_[i], matrix_[i] + cols_to_copy, new_matrix[i]);
    }

    for (int i = 0; i < rows_; ++i) {
      delete[] matrix_[i];
    }
    delete[] matrix_;

    matrix_ = new_matrix;
    cols_ = new_cols;

  } catch (const bad_alloc&) {
    if (new_matrix) {
      for (int j = 0; j < rows_; j++) {
        delete[] new_matrix[j];
      }
      delete[] new_matrix;
    }
    throw;
  }
}

void S21Matrix::SetElement(int i, int j, double value) {
  (*this)(i, j) = value;
}

// Методы
bool S21Matrix::EqMatrix(const S21Matrix& other) const {
  int flag = 1;

  const double eps = 1e-6;

  if (rows_ != other.rows_ || cols_ != other.cols_) {
    flag = 0;
  }

  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < cols_; j++) {
      if (fabs(matrix_[i][j] - other.matrix_[i][j]) >= eps) {
        flag = 0;
        break;
      }
    }
  }

  return flag;
}

void S21Matrix::SumMatrix(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < cols_; j++) {
      matrix_[i][j] += other.matrix_[i][j];
    }
  }
}

void S21Matrix::SubMatrix(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < cols_; j++) {
      matrix_[i][j] -= other.matrix_[i][j];
    }
  }
}

void S21Matrix::MulNumber(const double num) {
  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < cols_; j++) {
      matrix_[i][j] *= num;
    }
  }
}

void S21Matrix::MulMatrix(const S21Matrix& other) {
  if (cols_ != other.rows_) {
    throw invalid_argument(
        "Столбцы в первой матрице не должны быть равными строкам во второй");
  }

  S21Matrix temp(rows_, other.cols_);

  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < other.cols_; j++) {
      temp.matrix_[i][j] = 0;
      for (int k = 0; k < cols_; k++)
        temp.matrix_[i][j] += matrix_[i][k] * other.matrix_[k][j];
    }
  }

  *this = temp;
}

S21Matrix S21Matrix::Transpose() {
  S21Matrix temp(cols_, rows_);
  for (int i = 0; i < rows_; i++) {
    for (int j = 0; j < cols_; j++) {
      temp.matrix_[j][i] = matrix_[i][j];
    }
  }
  return temp;
}

S21Matrix S21Matrix::CalcComplements() {
  if (rows_ != cols_) {
    throw logic_error("Матрица не квадратная");
  }

  S21Matrix temp(rows_, cols_);

  if (rows_ == 1) {
    temp(0, 0) = 1.0;
    return temp;
  }

  for (int i = 0; i < rows_ && rows_ > 1; i++) {
    for (int j = 0; j < rows_; j++) {
      S21Matrix minor(rows_ - 1, cols_ - 1);

      for (int y = 0, mi = 0; y < rows_; y++) {
        if (y == i) continue;
        for (int x = 0, mj = 0; x < rows_; x++) {
          if (x == j) continue;
          minor(mi, mj++) = (*this)(y, x);
          ;
        }
        mi++;
      }

      double det = minor.Determinant();
      int sign = ((i + j) % 2 == 0) ? 1 : -1;
      temp(i, j) = sign * det;
      ;
    }
  }
  return temp;
}

double S21Matrix::Determinant() {
  if (rows_ != cols_) {
    throw logic_error("Матрица не квадратная");
  }

  if (rows_ == 0) {
    return 0.0;
  }

  const double eps = 1e-10;

  if (rows_ == 1) {
    return matrix_[0][0];
  }

  double determinant = 1.0;

  S21Matrix temp(*this);

  for (int i = 0; i < rows_ && determinant != 0.0; i++) {
    int max_row = i;
    for (int k = i + 1; k < rows_; k++) {
      if (fabs(temp.matrix_[k][i]) > fabs(temp.matrix_[max_row][i])) {
        max_row = k;
      }
    }

    if (fabs(temp.matrix_[max_row][i]) < eps) {
      determinant = 0.0;
      break;
    }

    if (max_row != i) {
      swap(temp.matrix_[i], temp.matrix_[max_row]);
      determinant *= -1;
    }

    for (int k = i + 1; k < rows_; k++) {
      double factor = temp.matrix_[k][i] / temp.matrix_[i][i];
      for (int j = i; j < rows_; j++) {
        temp.matrix_[k][j] -= factor * temp.matrix_[i][j];
      }
    }

    determinant *= temp.matrix_[i][i];
  }
  return determinant;
}

S21Matrix S21Matrix::InverseMatrix() {
  if (rows_ != cols_) {
    throw logic_error("Матрица не квадратная");
  }

  double det = Determinant();
  const double eps = 1e-10;

  if (fabs(det) < eps) {
    throw logic_error("Матрица вырожденная, обратной не сущестсвует");
  }

  S21Matrix complements = this->CalcComplements();
  S21Matrix adjoint = complements.Transpose();

  double inv_det = 1.0 / det;
  adjoint.MulNumber(inv_det);

  return adjoint;
}

// Перегрузка операторов

S21Matrix& S21Matrix::operator=(const S21Matrix& other) {
  if (this != &other) {
    for (int i = 0; i < rows_; i++) {
      delete[] matrix_[i];
    }
    delete[] matrix_;

    try {
      rows_ = other.rows_;
      cols_ = other.cols_;
      matrix_ = new double*[rows_];
      for (int i = 0; i < rows_; i++) {
        matrix_[i] = new double[cols_];
        copy(other.matrix_[i], other.matrix_[i] + cols_, matrix_[i]);
      }
    } catch (const bad_alloc&) {
      if (matrix_) {
        for (int j = 0; j < rows_; j++) {
          delete[] matrix_[j];
        }
        delete[] matrix_;
      }
      throw;
    }
  }
  return *this;
}

S21Matrix S21Matrix::operator+(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  S21Matrix temp(*this);
  temp.SumMatrix(other);
  return temp;
}

bool S21Matrix::operator==(const S21Matrix& other) const {
  return EqMatrix(other);
}

S21Matrix S21Matrix::operator-(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  S21Matrix temp(*this);
  temp.SubMatrix(other);
  return temp;
}

S21Matrix S21Matrix::operator*(const S21Matrix& other) {
  if (cols_ != other.rows_) {
    throw invalid_argument(
        "Столбцы в первой матрице не должны быть равными строкам во второй");
  }

  S21Matrix temp(*this);
  temp.MulMatrix(other);
  return temp;
}

S21Matrix operator*(S21Matrix matrix, double i) {
  S21Matrix temp = matrix;
  temp.MulNumber(i);
  return temp;
}

S21Matrix operator*(double i, S21Matrix matrix) { return matrix * i; }

S21Matrix& S21Matrix::operator-=(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  SubMatrix(other);
  return *this;
}

S21Matrix& S21Matrix::operator+=(const S21Matrix& other) {
  if (rows_ != other.rows_ || cols_ != other.cols_) {
    throw invalid_argument("Матрицы разного размера");
  }

  SumMatrix(other);
  return *this;
}

S21Matrix& S21Matrix::operator*=(const S21Matrix& other) {
  if (cols_ != other.rows_) {
    throw invalid_argument(
        "Столбцы в первой матрице не должны быть равными строкам во второй");
  }

  *this = *this * other;
  return *this;
}

S21Matrix& S21Matrix::operator*=(double num) {
  this->MulNumber(num);
  return *this;
}

double& S21Matrix::operator()(int i, int j) {
  if (i < 0 || i >= rows_ || j < 0 || j >= cols_) {
    throw out_of_range("Аргументы не соответствуют матрице");
  }

  if (matrix_ == nullptr) {
    throw logic_error("Матрица неинициализирована");
  }

  return matrix_[i][j];
}

const double& S21Matrix::operator()(int i, int j) const {
  if (i < 0 || i >= rows_ || j < 0 || j >= cols_) {
    throw out_of_range("Аргументы не соответствуют матрице");
  }

  if (matrix_ == nullptr) {
    throw logic_error("Матрица неинициализирована");
  }

  return matrix_[i][j];
}
