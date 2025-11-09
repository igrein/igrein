--ДЕНЬ 10

-- День направлен на изучение транзакций и проблем параллельного доступа в базах данных:
-- изоляция транзакций, аномалии параллельного доступа (Lost Update, Non-Repeatable Reads, 
-- Phantom Reads), взаимоблокировки (Deadlock) и различные уровни изоляции транзакций.

-- ex00: Simple transaction
-- Изучение базового поведения транзакций и видимости изменений между сессиями

-- Session #1
-- Обновляем рейтинг для "Pizza Hut" до 5 баллов в режиме транзакции
BEGIN TRANSACTION;
UPDATE pizzeria SET rating = 5 WHERE name = 'Pizza Hut';

-- Проверяем изменения в сеансе №1 - видим рейтинг 5
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем изменения в session #2 - не видим изменений (рейтинг остался прежним)
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #1
-- Публикуем изменения для всех параллельных сеансов
COMMIT;

-- Session #2
-- Проверяем изменения в Session #2 после COMMIT - теперь видим рейтинг 5
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';


-- ex01: Lost Update Anomaly
-- Изучение аномалии потери обновления на уровне изоляции READ COMMITTED

-- Session #1
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Обновляем рейтинг до 4
UPDATE pizzeria SET rating = 4 WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Пытаемся обновить рейтинг до 3.6 (блокируется до коммита в Session #1)
UPDATE pizzeria SET rating = 3.6 WHERE name = 'Pizza Hut';

-- Session #1
-- Фиксируем изменения
COMMIT;

-- Session #2
-- UPDATE теперь выполняется после снятия блокировки
-- Фиксируем изменения
COMMIT;

-- Session #1
-- Проверяем конечный результат - видим рейтинг 3.6
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем конечный результат - видим рейтинг 3.6
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';


-- ex02: Lost Update for Repeatable Read
-- Изучение аномалии потери обновления на уровне изоляции REPEATABLE READ

-- Session #1
-- Устанавливаем уровень изоляции REPEATABLE READ
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Обновляем рейтинг до 4
UPDATE pizzeria SET rating = 4 WHERE name = 'Pizza Hut';

-- Session #2
-- Устанавливаем уровень изоляции REPEATABLE READ
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Пытаемся обновить рейтинг до 3.6
UPDATE pizzeria SET rating = 3.6 WHERE name = 'Pizza Hut';

-- Session #1
-- Фиксируем изменения
COMMIT;

-- Session #2
-- Получаем ошибку из-за конфликта параллельных изменений
-- Фиксируем транзакцию
COMMIT;

-- Session #1
-- Проверяем конечный результат - видим рейтинг 4
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем конечный результат - видим рейтинг 4
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';


-- ex03: Non-Repeatable Reads Anomaly
-- Изучение аномалии неповторяющегося чтения на уровне изоляции READ COMMITTED

-- Session #1
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Обновляем рейтинг до 3.6 и фиксируем изменения
UPDATE pizzeria SET rating = 3.6 WHERE name = 'Pizza Hut';
COMMIT;

-- Session #1
-- Проверяем рейтинг снова в той же транзакции - видим измененные данные
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Фиксируем транзакцию
COMMIT;

-- Session #1
-- Проверяем рейтинг после коммита
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем рейтинг
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';


-- ex04: Non-Repeatable Reads for Serialization
-- Изучение аномалии неповторяющегося чтения на уровне изоляции SERIALIZABLE

-- Session #1
-- Устанавливаем уровень изоляции SERIALIZABLE
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и проверяем рейтинг
BEGIN TRANSACTION;
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Устанавливаем уровень изоляции SERIALIZABLE
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SHOW TRANSACTION ISOLATION LEVEL;

-- Обновляем рейтинг до 3.0 и фиксируем изменения
UPDATE pizzeria SET rating = 3.0 WHERE name = 'Pizza Hut';
COMMIT;

-- Session #1
-- Проверяем рейтинг снова в той же транзакции - не видим изменений
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Фиксируем транзакцию
COMMIT;

-- Session #1
-- Проверяем рейтинг после коммита - теперь видим изменения
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';

-- Session #2
-- Проверяем рейтинг
SELECT * FROM pizzeria WHERE name = 'Pizza Hut';


-- ex05: Phantom Reads Anomaly
-- Изучение аномалии фантомного чтения на уровне изоляции READ COMMITTED

-- Session #1
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и выполняем агрегацию рейтингов
BEGIN TRANSACTION;
SELECT SUM(rating) FROM pizzeria;

-- Session #2
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Добавляем новую пиццерию и фиксируем изменения
INSERT INTO pizzeria VALUES (10, 'Kazan Pizza', 5);
COMMIT;

-- Session #1
-- Выполняем агрегацию рейтингов снова - видим фантомную запись
SELECT SUM(rating) FROM pizzeria;

-- Фиксируем транзакцию
COMMIT;

-- Session #1
-- Проверяем агрегацию после коммита
SELECT SUM(rating) FROM pizzeria;

-- Session #2
-- Проверяем агрегацию
SELECT SUM(rating) FROM pizzeria;


-- ex06: Phantom Reads for Repeatable Read
-- Изучение аномалии фантомного чтения на уровне изоляции REPEATABLE READ

-- Session #1
-- Устанавливаем уровень изоляции REPEATABLE READ
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и выполняем агрегацию рейтингов
BEGIN TRANSACTION;
SELECT SUM(rating) FROM pizzeria;

-- Session #2
-- Устанавливаем уровень изоляции REPEATABLE READ
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SHOW TRANSACTION ISOLATION LEVEL;

-- Добавляем новую пиццерию и фиксируем изменения
INSERT INTO pizzeria VALUES (11, 'Kazan Pizza 2', 4);
COMMIT;

-- Session #1
-- Выполняем агрегацию рейтингов снова - не видим фантомную запись
SELECT SUM(rating) FROM pizzeria;

-- Фиксируем транзакцию
COMMIT;

-- Session #1
-- Проверяем агрегацию после коммита - теперь видим новую запись
SELECT SUM(rating) FROM pizzeria;

-- Session #2
-- Проверяем агрегацию
SELECT SUM(rating) FROM pizzeria;


-- ex07: Deadlock
-- Воспроизведение ситуации взаимоблокировки (deadlock)

-- Session #1
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и обновляем рейтинг для пиццерии с id = 1
BEGIN TRANSACTION;
UPDATE pizzeria SET rating = 1.0 WHERE id = 1;

-- Session #2
-- Проверяем текущий уровень изоляции
SHOW TRANSACTION ISOLATION LEVEL;

-- Начинаем транзакцию и обновляем рейтинг для пиццерии с id = 2
BEGIN TRANSACTION;
UPDATE pizzeria SET rating = 2.0 WHERE id = 2;

-- Session #1
-- Пытаемся обновить рейтинг для пиццерии с id = 2 (блокируется)
UPDATE pizzeria SET rating = 1.5 WHERE id = 2;

-- Session #2
-- Пытаемся обновить рейтинг для пиццерии с id = 1 (возникает взаимоблокировка)
UPDATE pizzeria SET rating = 3 WHERE id = 1;

-- Session #1
-- Одна из транзакций завершается успешно, фиксируем изменения
COMMIT;

-- Session #2
-- Вторая транзакция получает ошибку deadlock, фиксируем изменения
COMMIT;
