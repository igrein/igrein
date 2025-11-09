--ДЕНЬ 7
--Направлен наметоды работы с индексами PostgreSQL: 
--создание различных типов индексов, анализ запросов и их оптимизацию

--ex00
--Создать простой индекс BTree для каждого внешнего ключа в нашей базе данных. 
--Шаблон имени должен соответствовать следующему правилу:
-- "idx_{имя_таблицы}_{имя_столбца}". 
--Например, имя индекса BTree для столбца pizzeria_id в таблице menu — idx_menu_pizzeria_id

CREATE INDEX idx_person_visits_person_id ON person_visits(person_id);
CREATE INDEX idx_person_visits_pizzeria_id ON person_visits(pizzeria_id);
CREATE INDEX idx_menu_pizzeria_id ON menu(pizzeria_id);
CREATE INDEX idx_person_order_person_id ON person_order(person_id);
CREATE INDEX idx_person_order_menu_id ON person_order(menu_id);

--ex01
--Написать SQL-запрос, который возвращает информацию о пицце и названиях пиццерий
--Доказать, что  индексы работают с SQL. 
--В качестве доказательства служит команда EXPLAIN ANALYZE 

SELECT m.pizza_name, pi.name AS pizzeria_name FROM menu m
JOIN pizzeria pi ON m.pizzeria_id = pi.id
ORDER BY 1,2 DESC;

SET enable_seqscan = OFF;

EXPLAIN ANALYZE SELECT m.pizza_name, pi.name AS pizzeria_name FROM menu m
JOIN pizzeria pi ON m.pizzeria_id = pi.id
ORDER BY 1,2 DESC;

SET enable_seqscan = ON;

--ex02
--Создать функциональный индекс B-дерева с именем idx_person_name в названии столбца person таблицы. Индекс должен содержать имена пользователей, набранные заглавными буквами.
--Написать любой SQL-запрос с подтверждением (EXPLAIN ANALYZE), 
--что индекс idx_person_name работает.

CREATE INDEX idx_person_name ON person(upper(name));

SET enable_seqscan = OFF;

EXPLAIN ANALYZE 
SELECT * FROM person
WHERE upper(name) = 'KATE';

SET enable_seqscan = ON;

--ex03
--Создать более эффективный многоколоночный индекс B-Tree с именем idx_person_order_multi 
--для приведённого ниже SQL-запроса.

SELECT person_id, menu_id,order_date
FROM person_order
WHERE person_id = 8 AND menu_id = 19;

--Привести любой SQL-запрос с подтверждением (EXPLAIN ANALYZE), 
--что индекс idx_person_order_multi работает.

CREATE INDEX idx_person_order_multi ON person_order(person_id, menu_id, order_date);

SET enable_seqscan = OFF;

EXPLAIN ANALYZE
SELECT person_id, menu_id,order_date
FROM person_order
WHERE person_id = 8 AND menu_id = 19;

SET enable_seqscan = ON;

--ex04
--Создать уникальный индекс BTree с именем idx_menu_unique в таблице menu
--для столбцов pizzeria_id и pizza_name
--Написать любой SQL-запрос с подтверждением (EXPLAIN ANALYZE), 
--что индекс idx_menu_unique работает.

CREATE UNIQUE INDEX idx_menu_unique ON menu(pizzeria_id, pizza_name);

SET enable_seqscan = OFF;

EXPLAIN ANALYZE
INSERT INTO menu (id, pizzeria_id, pizza_name, price)
VALUES (100, 1, 'cheese pizza', 900);

SET enable_seqscan = ON;

--ex05
--Создать частично уникальный индекс BTree с именем idx_person_order_order_date
--в таблице person_order для атрибутов person_id и menu_id 
--с частичной уникальностью для столбца order_date с датой «2022-01-01».
--Команда EXPLAIN ANALYZE должна возвращать следующий шаблон.
--Index Only Scan using idx_person_order_order_date on person_order …

CREATE UNIQUE INDEX idx_person_order_order_date
ON person_order(person_id, menu_id)
WHERE order_date = '2022-01-01';

SET enable_seqscan = OFF;

EXPLAIN ANALYZE
SELECT person_id, menu_id
FROM person_order
WHERE order_date = '2022-01-01';

SET enable_seqscan = ON;

--ex06
--Проанализировать приведённый ниже SQL-запрос с технической точки зрения

SELECT
    m.pizza_name AS pizza_name,
    max(rating) OVER (PARTITION BY rating ORDER BY rating ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS k
FROM  menu m
INNER JOIN pizzeria pz ON m.pizzeria_id = pz.id
ORDER BY 1,2;


--Создать новый индекс BTree с именем idx_1, который должен улучшить показатель
--«Время выполнения» для этого SQL-запроса.
--Предоставить доказательства (EXPLAIN ANALYZE), что SQL-запрос был улучшен.


CREATE INDEX idx_1 ON pizzeria(rating);

SET enable_seqscan = ON;

--Без индекса
EXPLAIN ANALYZE
SELECT
    m.pizza_name AS pizza_name,
    max(rating) OVER (PARTITION BY rating ORDER BY rating ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS k
FROM  menu m
INNER JOIN pizzeria pz ON m.pizzeria_id = pz.id
ORDER BY 1,2;

--с индексом
SET enable_seqscan = OFF;

EXPLAIN ANALYZE
SELECT
    m.pizza_name AS pizza_name,
    max(rating) OVER (PARTITION BY rating ORDER BY rating ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS k
FROM  menu m
INNER JOIN pizzeria pz ON m.pizzeria_id = pz.id
ORDER BY 1,2;

--Время выполнения второго запроса ниже

