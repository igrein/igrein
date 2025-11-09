--ДЕНЬ 3

--Задания направлены на работу с SQL и реляционными базами данных:
--понимание реляционной алгебры, использование различных типов соединений (JOIN),
--создание запросов с помощью CTE, обработку пропущенных значений, фильтрацию и сортировку данных

--ex00
--Написать SQL-запрос, который выведет список пиццерий с их рейтингом, 
--но только тех, которые никто не посещал

SELECT name, rating
FROM pizzeria
LEFT JOIN person_visits pv
ON pizzeria.id = pv.pizzeria_id
WHERE pv.pizzeria_id IS NULL;

--ex01
--Написать SQL-запрос, который возвращает отсутствующие даты с 1 по 10 января 2022 года 
--(включительно) для посещений людьми с идентификаторами 1 и 2, то есть дни, пропущенные обоими.
--Сортировка по дате посещения в порядке возрастания.
--Запрещены NOT IN, IN, NOT EXISTS, EXISTS, UNION, EXCEPT, INTERSECT

SELECT missing_date::date
FROM generate_series('2022-01-01', '2022-01-10', interval '1 day') AS missing_date
LEFT JOIN person_visits pv 
ON pv.visit_date = missing_date AND (pv.person_id = 1 OR pv.person_id = 2)
WHERE pv.person_id IS NULL
ORDER BY missing_date::date;

--ex02
--Написать SQL-запрос, который возвращает:
--Полный список имён людей, посетивших (или не посетивших) пиццерии 
--в период с 1 по 3 января 2022 года
--Полный список пиццерий, которые посетили (или не посетили) за этот период
--Названия колонок person_name, visit_date, pizzeria_name
--Значения NULL в столбцах person_name и pizzeria_name заменить на '-'. 
--Сортировка по всем трём столбцам.
--Запрещены NOT IN, IN, NOT EXISTS, EXISTS, UNION, EXCEPT, INTERSECT

SELECT
	COALESCE (person.name, '-') AS person_name, 
	visit_date, 
	COALESCE (pizzeria.name, '-') AS pizzeria_name FROM person
FULL JOIN
(SELECT person_id, pizzeria_id, visit_date
FROM person_visits
WHERE visit_date BETWEEN '2022-01-01' AND '2022-01-03') AS visits_modi
ON person.id = visits_modi.person_id 
FULL JOIN pizzeria ON pizzeria.id = visits_modi.pizzeria_id 
ORDER BY person_name, visit_date, pizzeria_name;

--ex03
--Переписать SQL-запрос из задания 01, используя CTE (Common Table Expression)
--Реализовать в CTE-блоке генератор дат. Результат должен совпадать с результатом из Задания 01
--Запрещены NOT IN, IN, NOT EXISTS, EXISTS, UNION, EXCEPT, INTERSECT

WITH missing_date AS
	(SELECT missing_date::date
	FROM generate_series('2022-01-01', '2022-01-10', interval '1 day') AS missing_date)
SELECT missing_date::date FROM missing_date
LEFT JOIN person_visits pv 
ON pv.visit_date = missing_date AND (pv.person_id = 1 OR pv.person_id = 2)
WHERE pv.person_id IS NULL
ORDER BY missing_date::date;

--ex04
--Найти полную информацию обо всех возможных вариантах пиццерий и ценах на пиццу 
--с грибами или пепперони.
--Сортировка по названию пиццы и названию пиццерии.
--Названиям колонок pizza_name, pizzeria_name, price

SELECT pizza_name, pi.name AS pizzeria_name, price FROM menu m 
JOIN pizzeria pi ON m.pizzeria_id =pi.id
WHERE (pizza_name = 'mushroom pizza' OR pizza_name = 'pepperoni pizza')
ORDER BY pizza_name, pizzeria_name;

--ex05
--Найти имена всех женщин старше 25 лет и отсортировать результат по имени

SELECT name FROM person p
WHERE gender = 'female' AND age > 25
ORDER BY name;

--ex06
--Найти все названия пицц (и соответствующие названия пиццерий из таблицы menu), 
--которые заказывали Денис или Анна.
--Сортировка по обеим колонкам.
--Названия колонок pizza_name, pizzeria_name

SELECT pizza_name, pi.name AS pizzeria_name
FROM menu m 
JOIN pizzeria pi ON m.pizzeria_id = pi.id 
JOIN
	(SELECT  name AS person_name, menu_id
	FROM person_order po
	JOIN person p ON po.person_id = p.id 
	WHERE name = 'Denis' OR name = 'Anna') AS menu_position
ON m.id = menu_position. menu_id
ORDER BY pizza_name, pizzeria_name

--ex07
--Найти название пиццерии, которую Дмитрий посетил 8 января 2022 года, 
--где он мог заказать пиццу дешевле 800 рублей

SELECT pizzeria.name  FROM person p
JOIN person_visits pv ON p.id = pv.person_id
JOIN menu ON pv.pizzeria_id = menu.pizzeria_id
JOIN pizzeria ON pizzeria.id = menu.pizzeria_id
WHERE p.name = 'Dmitriy' AND visit_date = '2022-01-08' AND price < 800;

--ex08
--Найти имена всех мужчин из Москвы или Самары, 
--которые заказывали пиццу с пепперони, грибами или оба вида сразу.
--Сортировка по именам в обратном алфавитном порядке.

SELECT p.name FROM person p
JOIN person_order po ON p.id = po.person_id 
JOIN menu m ON m.id = po.menu_id
WHERE (address = 'Moscow' OR address = 'Samara')
	AND gender = 'male'
	AND (m.pizza_name = 'mushroom pizza' OR m.pizza_name = 'pepperoni pizza')
ORDER BY p.name DESC;

--ex09
--Найти имена всех женщин, которые заказывали и пепперони, и сырную пиццу 
--(в любое время и в любых пиццериях).
--СОртировка по именам в алфавитном порядке.

SELECT p.name FROM person p
JOIN person_order po ON p.id = po.person_id 
JOIN menu m ON m.id = po.menu_id
WHERE gender = 'female' AND m.pizza_name = 'cheese pizza'
INTERSECT
SELECT p.name FROM person p
JOIN person_order po ON p.id = po.person_id 
JOIN menu m ON m.id = po.menu_id
WHERE gender = 'female' AND m.pizza_name = 'pepperoni pizza'
ORDER BY name;

--ex10
--Найти имена людей, проживающих по одному адресу (в одном городе).
--Сортировка по трем колонкам: по имени первого человека, имени второго человека и общему адресу.
--Названия колонок person_name1, person_name2, common_address

SELECT 
	p.name AS person_name1,
	pp.name AS person_name2, 
	p.address AS common_address
FROM  person p
JOIN person pp ON pp.address = p.address 
	AND p.id > pp.id
ORDER BY 1,2,3
