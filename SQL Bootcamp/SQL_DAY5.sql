--ДЕНЬ 5
--Направлен на создание и использование представления (views) для фильтрации данных, 
--генерирование временных диапазонов и нахождение пропущенных дат,
--работу с операциями над множествами, рассчет скидок и управление 
--материализованными представлениями, включая их обновление и удаление.

--ex00
--Создать два представления в базе данных (с атрибутами, аналогичными исходной таблице), 
--реализующие простую фильтрацию персон по полу.
--Присвоить представлениям соответствующие имена:
--v_persons_female (для лиц женского пола)
--v_persons_male (для лиц мужского пола)

CREATE VIEW v_persons_female 
AS SELECT * FROM person p 
WHERE gender = 'female';

CREATE VIEW v_persons_male 
AS SELECT * FROM person p 
WHERE gender = 'male';

--ex01
--Используя 2 представления из Задания 00, написать SQL-запрос,
--который выведет имена женщин и мужчин в одном списке.
--Сортировка списка по имени человека.

SELECT m.name FROM v_persons_male m
UNION
SELECT f.name FROM v_persons_female f
ORDER BY 1;


--ex02
--Создать представление базы данных с именем v_generated_dates, 
--которое будет «хранить» сгенерированные даты с 1 января по 31 января 2022 года в типе DATE.
--Необходимо упорядочить данные по столбцу generated_date

CREATE VIEW v_generated_dates
AS SELECT generate_series('2022-01-01'::date, '2022-01-31'::date, interval '1 day')::date
AS generated_date;

--ex03
--Написать SQL-запрос, который возвращает пропущенные дни посещений людей за январь 2022 года.
--Для этой задачи использовать представление v_generated_dates
--Отсортировать результат по столбцу missing_date

SELECT generated_date AS missing_date
FROM v_generated_dates 
WHERE generated_date NOT IN (SELECT visit_date FROM person_visits)
ORDER BY 1;

--ex04
--Написать SQL-запрос, реализующий формулу (R − S) ∪ (S − R), где:
--R — таблица person_visits с фильтром по дате 2 января 2022 года,
--S — та же таблица person_visits, но с фильтром по дате 6 января 2022 года.
--Вычисления должны выполняться над множествами значений столбца person_id, 
--и в результате должен быть только этот столбец. 
--Отсортировать вывод по person_id 
--Сохранить итоговый запрос в представлении v_symmetric_union.

CREATE VIEW v_symmetric_union
AS SELECT
(SELECT person_id FROM person_visits pv 
WHERE visit_date = '2022-01-02'
EXCEPT
SELECT person_id FROM person_visits pv 
WHERE visit_date = '2022-01-06') 
UNION
(SELECT person_id FROM person_visits pv 
WHERE visit_date = '2022-01-06'
EXCEPT
SELECT person_id FROMm person_visits pv 
WHERE visit_date = '2022-01-02')
ORDER BY 1; 

--ex05
--Создаить представление v_price_with_discount, которое возвращает заказы человека с указанием:
--имени клиента (person_name), названия пиццы (pizza_name), реальной цены (real_price),
--столбца discount_price (рассчитывается по формуле price - price * 0.1, то есть с 10% скидкой).
--Отсортировать результаты по имени клиента (person_name) и названию пиццы (pizza_name)
--Привести столбец discount_price к целочисленному типу (integer)

CREATE VIEW v_price_with_discount
AS SELECT 
	p.name AS name, 
	m.pizza_name, 
	m.price AS real_price, 
	cast (price - price * 0.1 AS int) AS discount_price
FROM person_order po
JOIN person p ON p.id = po.person_id 
JOIN menu m ON m.id = po.menu_id
ORDER BY name, pizza_name;

--ex06
--Создать материализованное представление mv_dmitriy_visits_and_eats (с включенными данными)
-- на основе SQL-запроса, который находит название пиццерии, где Дмитрий был 8 января 2022 года 
--и мог съесть пиццу дешевле 800 рублей

CREATE MATERIALIZED VIEW mv_dmitriy_visits_and_eats 
AS SELECT pizzeria.name FROM person p
JOIN person_visits pv ON p.id = pv.person_id
JOIN menu ON pv.pizzeria_id = menu.pizzeria_id
JOIN pizzeria ON pizzeria.id = menu.pizzeria_id
WHERE p.name = 'Dmitriy' AND visit_date = '2022-01-08' AND price < 800;

--ex07
--Обновить данные в материализованном представлении mv_dmitriy_visits_and_eats (Задание 06).
--Добавить новый визит Дмитрия, соответствующий условиям представления, 
--но с другой пиццерией (отличной от результата Задания 06)
--Обновить данные в mv_dmitriy_visits_and_eats

INSERT INTO person_visits (id, person_id, pizzeria_id, visit_date)
VALUES (
	(SELECT max(id) FROM person_visits)+1,
	(SELECT id FROM person WHERE name = 'Dmitriy'),
	(SELECT id FROM pizzeria WHERE pizzeria.name = 'DoDo Pizza'),
	'2022-01-08'
);

REFRESH MATERIALIZED VIEW mv_dmitriy_visits_and_eats;

--ex08
--Удалить виртуальные таблицы и материализованное представление.
DROP VIEW v_persons_male;
DROP VIEW v_persons_female;
DROP VIEW v_generated_dates;
DROP VIEW v_symmetric_union;
DROP VIEW v_price_with_discount;
DROP MATERIALIZED VIEW mv_dmitriy_visits_and_eats;