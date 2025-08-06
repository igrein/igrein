#include <gtest/gtest.h>

#include "s21_matrix_oop.h"

TEST(MatrixTest, DefaultConstructor) {
  S21Matrix matrix;
  EXPECT_EQ(matrix.GetRows(), 0);
  EXPECT_EQ(matrix.GetCols(), 0);
}

TEST(MatrixTest, ParamConstructor) {
  S21Matrix matrix(3, 4);
  EXPECT_EQ(matrix.GetRows(), 3);
  EXPECT_EQ(matrix.GetCols(), 4);

  for (int i = 0; i < 3; i++) {
    for (int j = 0; j < 4; j++) {
      EXPECT_DOUBLE_EQ(matrix.GetElement(i, j), 0.0);
    }
  }

  EXPECT_THROW(S21Matrix(-1, 5), std::invalid_argument);
}

TEST(MatrixTest, CopyConstructor) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(0, 1, 2.0);
  matrix1.SetElement(1, 0, 3.0);
  matrix1.SetElement(1, 1, 4.0);

  S21Matrix matrix2(matrix1);
  EXPECT_TRUE(matrix1 == matrix2);
}

TEST(MatrixTest, MoveConstructor) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);

  S21Matrix matrix2(std::move(matrix1));
  EXPECT_EQ(matrix1.GetRows(), 0);
  EXPECT_EQ(matrix1.GetCols(), 0);
  EXPECT_EQ(matrix2.GetRows(), 2);
  EXPECT_EQ(matrix2.GetCols(), 2);
  EXPECT_DOUBLE_EQ(matrix2.GetElement(0, 0), 1.0);
}

TEST(MatrixTest, SetRows) {
  S21Matrix matrix(2, 2);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(1, 1, 1.0);

  matrix.SetRows(3);
  EXPECT_EQ(matrix.GetRows(), 3);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 1.0);
  EXPECT_DOUBLE_EQ(matrix.GetElement(1, 1), 1.0);
  EXPECT_DOUBLE_EQ(matrix.GetElement(2, 0), 0.0);

  matrix.SetRows(1);
  EXPECT_EQ(matrix.GetRows(), 1);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 1.0);

  S21Matrix m(2, 2);
  EXPECT_THROW(m.SetRows(-1), std::invalid_argument);
}

TEST(MatrixTest, SetCols) {
  S21Matrix matrix(2, 2);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(1, 1, 1.0);

  matrix.SetCols(3);
  EXPECT_EQ(matrix.GetCols(), 3);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 1.0);
  EXPECT_DOUBLE_EQ(matrix.GetElement(1, 1), 1.0);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 2), 0.0);

  matrix.SetCols(1);
  EXPECT_EQ(matrix.GetCols(), 1);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 1.0);

  S21Matrix m(2, 2);
  EXPECT_THROW(m.SetCols(-1), std::invalid_argument);
}

TEST(MatrixTest, EqMatrix) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);

  EXPECT_TRUE(matrix1.EqMatrix(matrix2));

  matrix2.SetElement(0, 0, 1.0000001);
  EXPECT_TRUE(matrix1.EqMatrix(matrix2));

  matrix2.SetElement(0, 0, 1.1);
  EXPECT_FALSE(matrix1.EqMatrix(matrix2));
}

TEST(MatrixTest, SumMatrix) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(1, 1, 1.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 2.0);
  matrix2.SetElement(1, 1, 2.0);

  matrix1.SumMatrix(matrix2);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 3.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 3.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1.SumMatrix(matrix3), std::invalid_argument);
}

TEST(MatrixTest, SubMatrix) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 3.0);
  matrix1.SetElement(1, 1, 3.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);
  matrix2.SetElement(1, 1, 1.0);

  matrix1.SubMatrix(matrix2);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 2.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 2.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1.SubMatrix(matrix3), std::invalid_argument);
}

TEST(MatrixTest, MulNumber) {
  S21Matrix matrix(2, 2);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(1, 1, 2.0);

  matrix.MulNumber(2.5);
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 2.5);
  EXPECT_DOUBLE_EQ(matrix.GetElement(1, 1), 5.0);
}

TEST(MatrixTest, MulMatrix) {
  S21Matrix matrix1(2, 3);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(0, 1, 2.0);
  matrix1.SetElement(0, 2, 3.0);
  matrix1.SetElement(1, 0, 4.0);
  matrix1.SetElement(1, 1, 5.0);
  matrix1.SetElement(1, 2, 6.0);

  S21Matrix matrix2(3, 2);
  matrix2.SetElement(0, 0, 7.0);
  matrix2.SetElement(0, 1, 8.0);
  matrix2.SetElement(1, 0, 9.0);
  matrix2.SetElement(1, 1, 10.0);
  matrix2.SetElement(2, 0, 11.0);
  matrix2.SetElement(2, 1, 12.0);

  matrix1.MulMatrix(matrix2);
  EXPECT_EQ(matrix1.GetRows(), 2);
  EXPECT_EQ(matrix1.GetCols(), 2);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 58.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 1), 64.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 0), 139.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 154.0);

  S21Matrix matrix3(2, 2);
  EXPECT_NO_THROW(matrix1.MulMatrix(matrix3));

  S21Matrix matrix4(4, 4);
  EXPECT_THROW(matrix1.MulMatrix(matrix4), std::invalid_argument);
}

TEST(MatrixTest, Transpose) {
  S21Matrix matrix(2, 3);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(0, 1, 2.0);
  matrix.SetElement(0, 2, 3.0);
  matrix.SetElement(1, 0, 4.0);
  matrix.SetElement(1, 1, 5.0);
  matrix.SetElement(1, 2, 6.0);

  S21Matrix result = matrix.Transpose();
  EXPECT_EQ(result.GetRows(), 3);
  EXPECT_EQ(result.GetCols(), 2);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 0), 1.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 0), 2.0);
  EXPECT_DOUBLE_EQ(result.GetElement(2, 0), 3.0);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 1), 4.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 1), 5.0);
  EXPECT_DOUBLE_EQ(result.GetElement(2, 1), 6.0);
}

TEST(MatrixTest, Determinant) {
  S21Matrix matrix1(1, 1);
  matrix1.SetElement(0, 0, 5.0);
  EXPECT_DOUBLE_EQ(matrix1.Determinant(), 5.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);
  matrix2.SetElement(0, 1, 2.0);
  matrix2.SetElement(1, 0, 3.0);
  matrix2.SetElement(1, 1, 4.0);
  EXPECT_DOUBLE_EQ(matrix2.Determinant(), -2.0);

  S21Matrix matrix3(3, 3);
  matrix3.SetElement(0, 0, 1.0);
  matrix3.SetElement(0, 1, 2.0);
  matrix3.SetElement(0, 2, 3.0);
  matrix3.SetElement(1, 0, 4.0);
  matrix3.SetElement(1, 1, 5.0);
  matrix3.SetElement(1, 2, 6.0);
  matrix3.SetElement(2, 0, 7.0);
  matrix3.SetElement(2, 1, 8.0);
  matrix3.SetElement(2, 2, 9.0);
  EXPECT_DOUBLE_EQ(matrix3.Determinant(), 0.0);

  S21Matrix matrix4(2, 3);
  EXPECT_THROW(matrix4.Determinant(), std::logic_error);
}

TEST(MatrixTest, CalcComplements) {
  S21Matrix matrix(3, 3);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(0, 1, 2.0);
  matrix.SetElement(0, 2, 3.0);
  matrix.SetElement(1, 0, 0.0);
  matrix.SetElement(1, 1, 4.0);
  matrix.SetElement(1, 2, 2.0);
  matrix.SetElement(2, 0, 5.0);
  matrix.SetElement(2, 1, 2.0);
  matrix.SetElement(2, 2, 1.0);

  S21Matrix result = matrix.CalcComplements();
  EXPECT_DOUBLE_EQ(result.GetElement(0, 0), 0.0);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 1), 10.0);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 2), -20.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 0), 4.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 1), -14.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 2), 8.0);
  EXPECT_DOUBLE_EQ(result.GetElement(2, 0), -8.0);
  EXPECT_DOUBLE_EQ(result.GetElement(2, 1), -2.0);
  EXPECT_DOUBLE_EQ(result.GetElement(2, 2), 4.0);

  S21Matrix matrix2(2, 3);
  EXPECT_THROW(matrix2.CalcComplements(), std::logic_error);

  S21Matrix m1(1, 1);
  m1(0, 0) = 5.0;
  S21Matrix res1 = m1.CalcComplements();
  EXPECT_EQ(res1(0, 0), 1.0);

  // Вырожденная матрица
  S21Matrix m2(2, 2);
  m2(0, 0) = m2(0, 1) = m2(1, 0) = m2(1, 1) = 1.0;
  EXPECT_NO_THROW(m2.CalcComplements());
}

TEST(MatrixTest, InverseMatrix) {
  S21Matrix matrix(3, 3);
  matrix.SetElement(0, 0, 2.0);
  matrix.SetElement(0, 1, 5.0);
  matrix.SetElement(0, 2, 7.0);
  matrix.SetElement(1, 0, 6.0);
  matrix.SetElement(1, 1, 3.0);
  matrix.SetElement(1, 2, 4.0);
  matrix.SetElement(2, 0, 5.0);
  matrix.SetElement(2, 1, -2.0);
  matrix.SetElement(2, 2, -3.0);

  S21Matrix result = matrix.InverseMatrix();
  const double epsilon = 1e-10;

  EXPECT_NEAR(result.GetElement(0, 0), 1.0, epsilon);
  EXPECT_NEAR(result.GetElement(0, 1), -1.0, epsilon);
  EXPECT_NEAR(result.GetElement(0, 2), 1.0, epsilon);
  EXPECT_NEAR(result.GetElement(1, 0), -38.0, epsilon);
  EXPECT_NEAR(result.GetElement(1, 1), 41.0, epsilon);
  EXPECT_NEAR(result.GetElement(1, 2), -34.0, epsilon);
  EXPECT_NEAR(result.GetElement(2, 0), 27.0, epsilon);
  EXPECT_NEAR(result.GetElement(2, 1), -29.0, epsilon);
  EXPECT_NEAR(result.GetElement(2, 2), 24.0, epsilon);

  S21Matrix matrix2(2, 3);
  EXPECT_THROW(matrix2.InverseMatrix(), std::logic_error);

  // Проверка на вырожденную матрицу
  S21Matrix matrix3(3, 3);
  matrix3.SetElement(0, 0, 1.0);
  matrix3.SetElement(0, 1, 2.0);
  matrix3.SetElement(0, 2, 3.0);
  matrix3.SetElement(1, 0, 4.0);
  matrix3.SetElement(1, 1, 5.0);
  matrix3.SetElement(1, 2, 6.0);
  matrix3.SetElement(2, 0, 7.0);
  matrix3.SetElement(2, 1, 8.0);
  matrix3.SetElement(2, 2, 9.0);
  EXPECT_THROW(matrix3.InverseMatrix(), std::logic_error);
}

TEST(MatrixTest, OperatorPlus) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(1, 1, 1.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 2.0);
  matrix2.SetElement(1, 1, 2.0);

  S21Matrix result = matrix1 + matrix2;
  EXPECT_DOUBLE_EQ(result.GetElement(0, 0), 3.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 1), 3.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1 + matrix3, std::invalid_argument);
}

TEST(MatrixTest, OperatorMinus) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 3.0);
  matrix1.SetElement(1, 1, 3.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);
  matrix2.SetElement(1, 1, 1.0);

  S21Matrix result = matrix1 - matrix2;
  EXPECT_DOUBLE_EQ(result.GetElement(0, 0), 2.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 1), 2.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1 - matrix3, std::invalid_argument);
}

TEST(MatrixTest, OperatorMultiplyMatrix) {
  S21Matrix matrix1(2, 3);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(0, 1, 2.0);
  matrix1.SetElement(0, 2, 3.0);
  matrix1.SetElement(1, 0, 4.0);
  matrix1.SetElement(1, 1, 5.0);
  matrix1.SetElement(1, 2, 6.0);

  S21Matrix matrix2(3, 2);
  matrix2.SetElement(0, 0, 7.0);
  matrix2.SetElement(0, 1, 8.0);
  matrix2.SetElement(1, 0, 9.0);
  matrix2.SetElement(1, 1, 10.0);
  matrix2.SetElement(2, 0, 11.0);
  matrix2.SetElement(2, 1, 12.0);

  S21Matrix result = matrix1 * matrix2;
  EXPECT_EQ(result.GetRows(), 2);
  EXPECT_EQ(result.GetCols(), 2);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 0), 58.0);
  EXPECT_DOUBLE_EQ(result.GetElement(0, 1), 64.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 0), 139.0);
  EXPECT_DOUBLE_EQ(result.GetElement(1, 1), 154.0);

  S21Matrix matrix3(2, 2);
  EXPECT_THROW(matrix1 * matrix3, std::invalid_argument);
}

TEST(MatrixTest, OperatorMultiplyNumber) {
  S21Matrix matrix(2, 2);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(1, 1, 2.0);

  S21Matrix result1 = matrix * 2.5;
  EXPECT_DOUBLE_EQ(result1.GetElement(0, 0), 2.5);
  EXPECT_DOUBLE_EQ(result1.GetElement(1, 1), 5.0);

  S21Matrix result2 = 2.5 * matrix;
  EXPECT_DOUBLE_EQ(result2.GetElement(0, 0), 2.5);
  EXPECT_DOUBLE_EQ(result2.GetElement(1, 1), 5.0);
}

TEST(MatrixTest, OperatorEq) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);

  EXPECT_TRUE(matrix1 == matrix2);

  matrix2.SetElement(0, 0, 1.1);
  EXPECT_FALSE(matrix1 == matrix2);
}

TEST(MatrixTest, OperatorAssignment) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);

  S21Matrix matrix2;
  matrix2 = matrix1;
  EXPECT_TRUE(matrix1 == matrix2);
}

TEST(MatrixTest, OperatorPlusEq) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(1, 1, 1.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 2.0);
  matrix2.SetElement(1, 1, 2.0);

  matrix1 += matrix2;
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 3.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 3.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1 += matrix3, std::invalid_argument);
}

TEST(MatrixTest, OperatorMinusEq) {
  S21Matrix matrix1(2, 2);
  matrix1.SetElement(0, 0, 3.0);
  matrix1.SetElement(1, 1, 3.0);

  S21Matrix matrix2(2, 2);
  matrix2.SetElement(0, 0, 1.0);
  matrix2.SetElement(1, 1, 1.0);

  matrix1 -= matrix2;
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 2.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 2.0);

  S21Matrix matrix3(3, 3);
  EXPECT_THROW(matrix1 -= matrix3, std::invalid_argument);
}

TEST(MatrixTest, OperatorMultiplyEqMatrix) {
  S21Matrix matrix1(2, 3);
  matrix1.SetElement(0, 0, 1.0);
  matrix1.SetElement(0, 1, 2.0);
  matrix1.SetElement(0, 2, 3.0);
  matrix1.SetElement(1, 0, 4.0);
  matrix1.SetElement(1, 1, 5.0);
  matrix1.SetElement(1, 2, 6.0);

  S21Matrix matrix2(3, 2);
  matrix2.SetElement(0, 0, 7.0);
  matrix2.SetElement(0, 1, 8.0);
  matrix2.SetElement(1, 0, 9.0);
  matrix2.SetElement(1, 1, 10.0);
  matrix2.SetElement(2, 0, 11.0);
  matrix2.SetElement(2, 1, 12.0);

  matrix1 *= matrix2;
  EXPECT_EQ(matrix1.GetRows(), 2);
  EXPECT_EQ(matrix1.GetCols(), 2);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 0), 58.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(0, 1), 64.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 0), 139.0);
  EXPECT_DOUBLE_EQ(matrix1.GetElement(1, 1), 154.0);

  S21Matrix matrix3(2, 2);
  EXPECT_NO_THROW(matrix1 *= matrix3);

  S21Matrix matrix4(3, 2);
  EXPECT_THROW(matrix1 *= matrix4, std::invalid_argument);
}

TEST(MatrixTest, OperatorMultiplyEqNumber) {
  S21Matrix matrix(2, 2);
  matrix.SetElement(0, 0, 1.0);
  matrix.SetElement(1, 1, 2.0);

  matrix *= 2.5;
  EXPECT_DOUBLE_EQ(matrix.GetElement(0, 0), 2.5);
  EXPECT_DOUBLE_EQ(matrix.GetElement(1, 1), 5.0);
}

TEST(MatrixTest, OperatorParentheses) {
  S21Matrix matrix(2, 2);
  matrix(0, 0) = 1.0;
  matrix(1, 1) = 2.0;

  EXPECT_DOUBLE_EQ(matrix(0, 0), 1.0);
  EXPECT_DOUBLE_EQ(matrix(1, 1), 2.0);

  const S21Matrix const_matrix(matrix);
  EXPECT_DOUBLE_EQ(const_matrix(0, 0), 1.0);

  EXPECT_THROW(matrix(2, 0), std::out_of_range);
  EXPECT_THROW(matrix(0, 2), std::out_of_range);
  EXPECT_THROW(matrix(-1, 0), std::out_of_range);
  EXPECT_THROW(matrix(0, -1), std::out_of_range);
}

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}