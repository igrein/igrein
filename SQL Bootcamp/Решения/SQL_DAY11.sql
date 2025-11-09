--ДЕНЬ 11

--Направлен создание функций (SQL/PLpgSQL) и триггеров для реализации бизнес-логики 
--на уровне СУБД, разрабатку систему аудита изменений данных и оптимизацию запросов

-- ex00
-- Создать систему аудита для отслеживания операций INSERT в таблице person.
-- Требуется создать таблицу person_audit с дополнительными колонками для аудита,
-- триггерную функцию fnc_trg_person_insert_audit и триггер trg_person_insert_audit,
-- которые будут автоматически сохранять информацию о каждой новой вставленной записи.
-- После создания объектов выполнить тестовый INSERT для проверки работы.

-- Создание таблицы для аудита с дополнительными колонками для отслеживания изменений
CREATE TABLE person_audit (
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type_event CHAR(1) NOT NULL DEFAULT 'I',
    row_id BIGINT NOT NULL,
    name VARCHAR,
    age INTEGER,
    gender VARCHAR,
    address VARCHAR,
    CONSTRAINT ch_type_event CHECK (type_event IN ('I', 'U', 'D'))
);

-- Создание триггерной функции для обработки операций INSERT
CREATE OR REPLACE FUNCTION fnc_trg_person_insert_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Сохранение информации о новой вставленной записи в таблицу аудита
    INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
    VALUES (NOW(), 'I', NEW.id, NEW.name, NEW.age, NEW.gender, NEW.address);
    RETURN NEW;
END;
$$ LANGUAGE PLPGSQL;

-- Создание триггера, который срабатывает после каждой операции INSERT
CREATE TRIGGER trg_person_insert_audit
    AFTER INSERT ON person
    FOR EACH ROW
    EXECUTE FUNCTION fnc_trg_person_insert_audit();

-- Проверка работы триггера: вставка тестовой записи
INSERT INTO person(id, name, age, gender, address) 
VALUES (10, 'Damir', 22, 'male', 'Irkutsk');

-- Проверка результатов
SELECT * FROM person WHERE id = 10;
SELECT * FROM person_audit;


-- ex01
-- Расширить систему аудита для отслеживания операций UPDATE в таблице person.
-- Создать триггерную функцию fnc_trg_person_update_audit и триггер trg_person_update_audit,
-- которые будут сохранять предыдущие состояния записей (OLD значения) при обновлении.
-- После создания выполнить тестовые UPDATE запросы для проверки работы.

-- Создание триггерной функции для обработки операций UPDATE
CREATE OR REPLACE FUNCTION fnc_trg_person_update_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Сохранение предыдущего состояния записи (OLD значения) при обновлении
    INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
    VALUES (NOW(), 'U', OLD.id, OLD.name, OLD.age, OLD.gender, OLD.address);
    RETURN NEW;
END;
$$ LANGUAGE PLPGSQL;

-- Создание триггера, который срабатывает перед каждой операцией UPDATE
CREATE TRIGGER trg_person_update_audit
    BEFORE UPDATE ON person
    FOR EACH ROW
    EXECUTE FUNCTION fnc_trg_person_update_audit();

-- Проверка работы триггера: последовательные обновления записи
UPDATE person SET name = 'Bulat' WHERE id = 10; 
UPDATE person SET name = 'Damir' WHERE id = 10;

-- Проверка результатов в таблице аудита
SELECT * FROM person_audit;


-- ex02
-- Дополнить систему аудита для отслеживания операций DELETE в таблице person.
-- Создать триггерную функцию fnc_trg_person_delete_audit и триггер trg_person_delete_audit,
-- которые будут сохранять удаляемые записи в таблице аудита.
-- После создания выполнить тестовый DELETE запрос для проверки работы.

-- Создание триггерной функции для обработки операций DELETE
CREATE OR REPLACE FUNCTION fnc_trg_person_delete_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Сохранение удаляемой записи (OLD значения) в таблице аудита
    INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
    VALUES (NOW(), 'D', OLD.id, OLD.name, OLD.age, OLD.gender, OLD.address);
    RETURN OLD;
END;
$$ LANGUAGE PLPGSQL;

-- Создание триггера, который срабатывает перед каждой операцией DELETE
CREATE TRIGGER trg_person_delete_audit
    BEFORE DELETE ON person
    FOR EACH ROW
    EXECUTE FUNCTION fnc_trg_person_delete_audit();

-- Проверка работы триггера: удаление тестовой записи
DELETE FROM person WHERE id = 10;

-- Проверка результатов в таблице аудита
SELECT * FROM person_audit;

-- ex03
-- Объединить всю логику аудита в один универсальный триггер для всех операций DML (INSERT, UPDATE, DELETE).
-- Создать универсальную триггерную функцию fnc_trg_person_audit и триггер trg_person_audit,
-- которые будут обрабатывать все три типа операций с явным разделением логики через IF-ELSE.
-- Удалить старые триггеры и функции, очистить таблицу аудита и выполнить полный тестовый сценарий.

-- Создание универсальной триггерной функции для обработки INSERT, UPDATE и DELETE
CREATE OR REPLACE FUNCTION fnc_trg_person_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Обработка операции INSERT - сохранение новой записи
    IF TG_OP = 'INSERT' THEN 
        INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
        VALUES (NOW(), 'I', NEW.id, NEW.name, NEW.age, NEW.gender, NEW.address);
        RETURN NEW;
    
    -- Обработка операции UPDATE - сохранение предыдущего состояния
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
        VALUES (NOW(), 'U', OLD.id, OLD.name, OLD.age, OLD.gender, OLD.address);
        RETURN NEW;
    
    -- Обработка операции DELETE - сохранение удаляемой записи
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO person_audit(created, type_event, row_id, name, age, gender, address)
        VALUES (NOW(), 'D', OLD.id, OLD.name, OLD.age, OLD.gender, OLD.address);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE PLPGSQL;

-- Создание универсального триггера для всех операций DML
CREATE TRIGGER trg_person_audit
    AFTER INSERT OR UPDATE OR DELETE ON person
    FOR EACH ROW
    EXECUTE FUNCTION fnc_trg_person_audit();

-- Удаление старых специализированных триггеров
DROP TRIGGER IF EXISTS trg_person_insert_audit ON person;
DROP TRIGGER IF EXISTS trg_person_update_audit ON person;
DROP TRIGGER IF EXISTS trg_person_delete_audit ON person;

-- Удаление старых триггерных функций
DROP FUNCTION IF EXISTS fnc_trg_person_insert_audit();
DROP FUNCTION IF EXISTS fnc_trg_person_update_audit();
DROP FUNCTION IF EXISTS fnc_trg_person_delete_audit();

-- Очистка таблицы аудита для тестирования нового универсального решения
DELETE FROM person_audit WHERE row_id > 0;

-- Комплексная проверка работы универсального триггера
INSERT INTO person(id, name, age, gender, address) VALUES (10, 'Damir', 22, 'male', 'Irkutsk'); 
UPDATE person SET name = 'Bulat' WHERE id = 10; 
UPDATE person SET name = 'Damir' WHERE id = 10; 
DELETE FROM person WHERE id = 10;

-- Проверка результатов в таблице аудита
SELECT * FROM person_audit;

-- ex04
-- Создать две SQL-функции для фильтрации данных из таблицы person по признаку пола.
-- Функция fnc_persons_female должна возвращать всех женщин, 
-- функция fnc_persons_male должна возвращать всех мужчин.
-- Функции должны возвращать таблицы с такой же структурой, как исходная таблица person.

-- Создание функции для выборки женщин
CREATE OR REPLACE FUNCTION fnc_persons_female()
RETURNS TABLE (
    id BIGINT, 
    name VARCHAR,
    age INTEGER, 
    gender VARCHAR, 
    address VARCHAR
) AS $$
    SELECT * FROM person 
    WHERE gender = 'female';
$$ LANGUAGE SQL;

-- Создание функции для выборки мужчин
CREATE OR REPLACE FUNCTION fnc_persons_male()
RETURNS TABLE (
    id BIGINT, 
    name VARCHAR,
    age INTEGER, 
    gender VARCHAR, 
    address VARCHAR
) AS $$
    SELECT * FROM person 
    WHERE gender = 'male';
$$ LANGUAGE SQL;

-- Проверка работы функций
SELECT * FROM fnc_persons_male();
SELECT * FROM fnc_persons_female();

-- ex05
-- Создать универсальную параметризованную SQL-функцию для фильтрации данных по полу.
-- Функция fnc_persons должна принимать параметр pgender со значением по умолчанию 'female'
-- и возвращать соответствующие записи из таблицы person.
-- Удалить предыдущие функции и обеспечить гибкость фильтрации через параметры.

-- Удаление предыдущих функций
DROP FUNCTION IF EXISTS fnc_persons_female();
DROP FUNCTION IF EXISTS fnc_persons_male();

-- Создание универсальной функции с параметром для фильтрации по полу
CREATE OR REPLACE FUNCTION fnc_persons(pgender VARCHAR DEFAULT 'female')
RETURNS TABLE (
    id BIGINT, 
    name VARCHAR,
    age INTEGER, 
    gender VARCHAR, 
    address VARCHAR
) AS $$	
    SELECT * FROM person 
    WHERE gender = pgender;
$$ LANGUAGE SQL;

-- Проверка работы параметризованной функции
SELECT * FROM fnc_persons(pgender := 'male');
SELECT * FROM fnc_persons();

-- ex06
-- Создать PL/pgSQL функцию fnc_person_visits_and_eats_on_date для сложного запроса 
-- с поиском пиццерий, которые посетил указанный человек и где он мог купить пиццу 
-- дешевле указанной цены на заданную дату.
-- Функция должна принимать три параметра со значениями по умолчанию и возвращать названия пиццерий.

-- Создание функции для поиска пиццерий, которые посетил человек с возможностью покупки пиццы по цене
CREATE OR REPLACE FUNCTION fnc_person_visits_and_eats_on_date(
    pperson VARCHAR DEFAULT 'Dmitriy', 
    pprice NUMERIC DEFAULT 500, 
    pdate DATE DEFAULT '2022-01-08'
)
RETURNS TABLE (name VARCHAR) AS $$
BEGIN 
    RETURN QUERY	
        SELECT DISTINCT pizzeria.name  
        FROM person p
        JOIN person_visits pv ON p.id = pv.person_id
        JOIN menu ON pv.pizzeria_id = menu.pizzeria_id
        JOIN pizzeria ON pizzeria.id = menu.pizzeria_id
        WHERE p.name = pperson 
          AND visit_date = pdate 
          AND price < pprice;
END;
$$ LANGUAGE PLPGSQL;

-- Проверка работы функции с различными параметрами
SELECT * FROM fnc_person_visits_and_eats_on_date(pprice := 800);
SELECT * FROM fnc_person_visits_and_eats_on_date(pperson := 'Anna', pprice := 1300, pdate := '2022-01-01');

-- ex07
-- Создать функцию func_minimum для нахождения минимального значения в массиве чисел.
-- Функция должна принимать входной параметр в виде массива чисел (VARIADIC arr)
-- и возвращать минимальное значение из этого массива.

-- Создание функции для поиска минимального значения в массиве
CREATE OR REPLACE FUNCTION func_minimum(VARIADIC arr NUMERIC[])
RETURNS NUMERIC AS $$
BEGIN 
    RETURN (SELECT MIN(unnest) FROM UNNEST(arr) AS unnest);
END;
$$ LANGUAGE PLPGSQL;

-- Проверка работы функции с массивом чисел
SELECT func_minimum(VARIADIC arr => ARRAY[10.0, -1.0, 5.0, 4.4]);

-- ex08
-- Создать функцию fnc_fibonacci для генерации последовательности чисел Фибоначчи 
-- до указанного предела. Функция должна принимать параметр pstop со значением по умолчанию 10
-- и возвращать таблицу всех чисел Фибоначчи, меньших заданного предела.

-- Создание функции для генерации чисел Фибоначчи меньше заданного предела
CREATE OR REPLACE FUNCTION fnc_fibonacci(pstop INTEGER DEFAULT 10)
RETURNS TABLE(fib INTEGER) AS $$
DECLARE
    a INTEGER := 0;
    b INTEGER := 1;
    temp INTEGER;
BEGIN
    -- Генерация последовательности Фибоначчи до достижения предела
    WHILE a < pstop LOOP
        fib := a;       
        RETURN NEXT; 

        temp := a + b;
        a := b;
        b := temp;
    END LOOP;
END;
$$ LANGUAGE PLPGSQL;

-- Проверка работы функции генерации чисел Фибоначчи
SELECT * FROM fnc_fibonacci(100);
SELECT * FROM fnc_fibonacci();
