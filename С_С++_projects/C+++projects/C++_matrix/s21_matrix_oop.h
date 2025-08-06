#ifndef S21_MATRIX_OOP_H
#define S21_MATRIX_OOP_H

#include <cmath>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>

using namespace std;

class S21Matrix {
 private:
  int rows_, cols_;
  double** matrix_;

 public:
  // Базовый конструктор
  S21Matrix() : rows_(0), cols_(0), matrix_(nullptr) {}

  // Параметризированный конструктор
  S21Matrix(int rows, int cols);

  // Конструктор копирования
  S21Matrix(const S21Matrix& other);

  // Конструктор переноса
  S21Matrix(S21Matrix&& other);

  // Деструктор
  ~S21Matrix() {
    for (int i = 0; i < rows_; i++) {
      delete[] matrix_[i];
    }
    delete[] matrix_;
  }

  // Аксессоры (геттеры)
  int GetRows() const { return rows_; }

  int GetCols() const { return cols_; }

  double GetElement(int i, int j) const {
    return (*this)(i, j);
    ;
  }

  // Мутаторы (сеттеры)
  void SetRows(int new_rows);
  void SetCols(int new_cols);
  void SetElement(int i, int j, double value);

  // Методы
  bool EqMatrix(const S21Matrix& other) const;
  void SumMatrix(const S21Matrix& other);
  void SubMatrix(const S21Matrix& other);
  void MulNumber(const double num);
  void MulMatrix(const S21Matrix& other);
  S21Matrix Transpose();
  S21Matrix CalcComplements();
  double Determinant();
  S21Matrix InverseMatrix();

  // Перегрузка операторов
  S21Matrix& operator=(const S21Matrix& other);
  S21Matrix operator+(const S21Matrix& other);
  bool operator==(const S21Matrix& other) const;
  S21Matrix operator-(const S21Matrix& other);
  S21Matrix operator*(const S21Matrix& other);
  friend S21Matrix operator*(S21Matrix matrix, double i);
  friend S21Matrix operator*(double i, S21Matrix matrix);
  S21Matrix& operator+=(const S21Matrix& other);
  S21Matrix& operator-=(const S21Matrix& other);
  S21Matrix& operator*=(const S21Matrix& other);
  S21Matrix& operator*=(double num);
  const double& operator()(int i, int j) const;
  double& operator()(int i, int j);
};

#endif
