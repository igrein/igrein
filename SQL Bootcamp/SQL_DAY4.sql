--ДЕНЬ 4
--Направлене на извлеченеи данных из базы с помощью сложных SQL-запросов 
--и их измение при помощи языка управления данными (DML) — вставить, обновить и удалить
--записи для поддержания актуальности базы


--ex00
--Написать SQL-запрос, который возвращает список:
--названия пицц, цены на пиццы, названия пиццерий, даты посещений
--для клиента Kate с ценами в диапазоне от 800 до 1000 рублей.
--Упорядочить результаты по названию пиццы, цене и названию пиццерии.
--Названия колонок pizza_name, price, pizzeria_name, visit_date

SELECT pizza_name, price, pi.name AS pizzeria_name, visit_date 
FROM person p
JOIN person_visits pv ON p.id = pv.person_id 
JOIN pizzeria pi ON pi.id = pv.pizzeria_id 
JOIN menu m ON pi.id = m.pizzeria_id 
WHERE p.name = 'Kate' AND price BETWEEN 800 AND 1000
ORDER BY pizza_name, price, pizzeria_name;

--ex01
--Найти все идентификаторы меню, которые никто не заказывал.
--Результат должен быть отсортирован по идентификатору.

SELECT m.id AS menu_id FROM menu m
EXCEPT
SELECT m.id AS menu_id FROM menu m, person_order po 
WHERE m.id=po.menu_id 
ORDER BY menu_id;

SELECT id AS menu_id
FROM menu
WHERE id NOT IN (SELECT DISTINCT menu_id FROM person_order)
ORDER BY menu_id;


--ex02
--Используя SQL-запрос из Задания 01, вывести
--названия пицц из пиццерии, которые никто не заказывал, включая соответствующие цены.
--Результат должен быть отсортирован по названию пиццы и цене.
--Названия колонок pizza_name, price, pizzeria_name

SELECT pizza_name, price , pi.name AS pizzeria_name
FROM menu m
JOIN pizzeria pi ON m.pizzeria_id = pi.id
WHERE m.id NOT IN (SELECT DISTINCT menu_id FROM person_order)
ORDER BY pizza_name, price;

--ex03
--Найти пиццерии, которые посещали чаще женщины или чаще мужчины.
--Сохранить дубликаты при использовании операторов работы с множествами
--Сортировка результата по названию пиццерии.

SELECT pi.name AS pizzeria_name
FROM pizzeria pi
JOIN person_visits pv ON pi.id = pv.pizzeria_id 
JOIN person p ON p.id = pv.person_id 
GROUP BY pi.name
HAVING sum(CASE WHEN p.gender = 'male' THEN 1 ELSE 0 END) > 
       sum(CASE WHEN p.gender = 'female' THEN 1 ELSE 0 END)
UNION ALL    
SELECT pi.name AS pizzeria_name
FROM pizzeria pi
JOIN person_visits pv ON pi.id = pv.pizzeria_id 
JOIN person p ON p.id = pv.person_id 
GROUP BY pi.name
HAVING sum(CASE WHEN p.gender = 'female' THEN 1 ELSE 0 END) > 
       sum(CASE WHEN p.gender = 'male' THEN 1 ELSE 0 END)
ORDER BY pizzeria_name; 

--ex04
--Найти объединение пиццерий, в которые заказы делали исключительно женщины,
--и тех, в которые заказы делали исключительно мужчины.
--Не включать дубликаты.
--Результат должен быть отсортирован по названию пиццерии.

SELECT pi.name AS pizzeria_name FROM person_order po
JOIN person p ON p.id = po.person_id
JOIN menu m ON m.id = po.menu_id
JOIN pizzeria pi ON m.pizzeria_id = pi.id
GROUP BY pi.name
HAVING sum(CASE WHEN p.gender = 'female' THEN 1 ELSE 0 END) > 0 AND 
       sum(CASE WHEN p.gender = 'male' THEN 1 ELSE 0 END) = 0
UNION
SELECT pi.name AS pizzeria_name FROM person_order po
JOIN person p ON p.id = po.person_id
JOIN menu m ON m.id = po.menu_id
JOIN pizzeria pi ON m.pizzeria_id = pi.id
GROUP BY pi.name
HAVING sum(CASE WHEN p.gender = 'male' THEN 1 ELSE 0 END) > 0 AND
       sum(CASE WHEN p.gender = 'female' THEN 1 ELSE 0 END) = 0
ORDER BY pizzeria_name;


--ex05
--Написать SQL-запрос, который вернет список пиццерий, которые посещал Андрей,
--но из которых он не делал заказов.
--Результат должен быть отсортирован по названию пиццерии.

SELECT pi.name AS pizzeria_name FROM person p
JOIN person_visits pv ON p.id = pv.person_id
JOIN pizzeria pi ON pi.id = pv.pizzeria_id 
WHERE p.name = 'Andrey'
EXCEPT
SELECT pi.name AS pizzeria_name FROM person p
JOIN person_order po ON p.id = po.person_id
JOIN menu m ON m.id = po.menu_id
JOIN pizzeria pi ON pi.id = m.pizzeria_id 
WHERE p.name = 'Andrey'
ORDER BY pizzeria_name;

--ex06
--Найти совпадающие названия пицц с одинаковой ценой, но из разных пиццерий. 
--Результат должен быть отсортирован по названию пиццы.
--Имена столбцов pizza_name, pizzeria_name_1, pizzeria_name_2, price

SELECT
	menu_1.pizza_name, 
	menu_1.name AS pizzeria_name_1,
	menu_2.name AS pizzeria_name_2,
	menu_1.price
FROM 
	(SELECT pizza_name, pi.name, price, pi.id AS pizzeria_id 
	FROM menu m
	JOIN pizzeria pi ON pi.id = m.pizzeria_id) AS menu_1
JOIN 
	(SELECT pizza_name, pi.name, price, pi.id AS pizzeria_id 
	FROM menu m
	JOIN pizzeria pi ON pi.id = m.pizzeria_id) AS menu_2
ON menu_1.price = menu_2.price 
	AND menu_1.pizzeria_id < menu_2.pizzeria_id
ORDER BY menu_1.pizza_name;


--ex07
--Добавить новую пиццу с названием «Greek pizza» (id = 19) по цене 800 рублей 
--в ресторане «Dominos» (pizzeria_id = 2).

INSERT INTO menu 
VALUES (19, 2, 'Greek pizza', 800);

--ex08
--Добавить новую пиццу с названием «Sicilian pizza» 
--(с ID, рассчитанным как «максимальный существующий ID + 1») 
--по цене 900 рублей в ресторан «Dominos»
--(использовать подзапрос для получения идентификатора пиццерии)
--Не использовать прямые числовые значения для идентификаторов Primary key и pizzeria.

INSERT INTO menu 
VALUES (
    (SELECT max(id) FROM menu) + 1,
    (SELECT id FROM pizzeria WHERE name = 'Dominos'),
    'Sicilian pizza', 
    900
);


--ex09
--Зафиксировать новые посещения ресторана Domino's Денисом и Ириной 24 февраля 2022 года
--Не использовать прямые числовые значения для идентификаторов Primary key и pizzeria.

INSERT INTO person_visits
VALUES (
	(SELECT max(id) FROM person_visits) +1,
	(SELECT id FROM person WHERE name = 'Denis'),
	(SELECT id FROM pizzeria WHERE name = 'Dominos'),
	'2022-02-24'),
	(
	(SELECT max(id) FROM person_visits) + 2,
	(SELECT id FROM person WHERE name = 'Irina'),
	(SELECT id FROM pizzeria WHERE name = 'Dominos'),
	'2022-02-24');

--ex10
--Зарегистрировать новые заказы от Дениса и Ирины 24 февраля 2022 года 
--на новое блюдо меню — «Sicilian pizza».
--Не использовать прямые числовые значения для идентификаторов Primary key и pizzeria.

INSERT INTO person_order
VALUES (
	(SELECT max(id) FROM person_order) +1,
	(SELECT id FROM person WHERE name = 'Denis'),
	(SELECT id FROM menu WHERE pizza_name = 'Sicilian pizza'),
	'2022-02-24'),
	(
	(SELECT max(id) FROM person_order) + 2,
	(SELECT id FROM person WHERE name = 'Irina'),
	(SELECT id FROM menu  WHERE pizza_name = 'Sicilian pizza'),
	'2022-02-24');

--ex11
--Изменить цену на «Greek pizza», уменьшив её на 10% от текущего значения.

UPDATE menu 
SET price = price*0.9
WHERE pizza_name = 'Greek pizza';

--ex12
--Зарегистрировать новые заказы "Greek pizza" для всех клиентов 25 февраля 2022 года.
--Не использовать прямые числовые значения для идентификаторов Primary key и pizzeria.
--Не использовать оконные функции, такие как ROW_NUMBER()
--Не использовать отдельные операторы INSERT

INSERT INTO person_order (id, person_id, menu_id, order_date)
SELECT
	(SELECT max(id) FROM person_order)+person.id,
	person.id,
	(SELECT id FROM menu WHERE pizza_name = 'Greek pizza'),
	'2022-02-25'
FROM person;

--ex13
--Написать два SQL-запроса (DML), которые удалят все новые заказы из задания 12 по дате заказа.
--удалят пиццу «Greek pizza» из меню.

DELETE FROM person_order WHERE order_date = '2022-02-25';

DELETE FROM menu WHERE pizza_name = 'Greek pizza';


