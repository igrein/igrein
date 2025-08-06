#!/bin/bash

# Переменные
TEST_FILE="test.txt"
FLAGS=("-b" "-e" "-E" "-n" "-s" "-T" "-t")

# Проверки существования необходимых файлов и утилит
if [[ ! -f ./s21_cat ]]; then
    echo "Ошибка: s21_cat не найден. Соберите проект перед тестированием."
    exit 1
fi

if [[ ! -f $TEST_FILE ]]; then
    echo "Ошибка: тестовый файл $TEST_FILE не найден."
    exit 1
fi

if ! command -v cat &>/dev/null; then
    echo "Ошибка: оригинальная утилита cat не найдена."
    exit 1
fi

# Функция для тестирования
run_test() {
    local flag=$1
    echo "Тестирование с флагом: $flag"

    # Запускаем оригинальную утилиту cat
    if ! cat $flag $TEST_FILE > original_output.txt 2>&1; then
        echo "Ошибка при выполнении оригинальной команды cat."
        return 1
    fi

    # Запускаем нашу реализацию
    if ! ./s21_cat $flag $TEST_FILE > s21_output.txt 2>&1; then
        echo "Ошибка при выполнении s21_cat."
        return 1
    fi

    # Сравнение результатов
    if [[ -f original_output.txt && -f s21_output.txt ]]; then
        if [[ -s original_output.txt && -s s21_output.txt ]]; then
            if diff -q original_output.txt s21_output.txt >/dev/null; then
                echo -e "\033[32m✅ Совпадает с оригиналом\033[0m"
            else
                echo -e "\033[31m❌ Несоответствие. Разница:\033[0m"
                diff original_output.txt s21_output.txt
            fi
        else
            echo "Один или оба файла пусты."
        fi
    else
        echo "Файл(ы) отсутствуют."
    fi
}

# Запускаем тесты для каждого флага
for flag in "${FLAGS[@]}"; do
    run_test "$flag"
done

# Удаляем временные файлы
rm -f original_output.txt s21_output.txt

echo "Все тесты завершены."
