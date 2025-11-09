--ДЕНЬ 2
-- направлен на использование множеств и операторов объединения,
-- создание подзапросов, сортировку по нескольким столбцам, 
--а также разные виды соединений таблиц

--ex00
--Напиcать SQL-запрос, который объединит в один общий список идентификаторы меню и 
--названия пицц из таблицы menu, а также идентификаторы и имена людей из таблицы person.
--В итоговом результате столбцы должны называться object_id и object_name
--Сортировка по object_id, а затем по object_name.

SELECT id AS object_id, pizza_name AS object_name FROM menu
UNION
SELECT id AS object_id, name AS object_name FROM person
ORDER BY object_id, object_name;

--ex01
--Изменить SQL-запрос из "Задания 00" следующим образом:
--Удалить столбец object_id
--Изменить порядок сортировки: сначала данные из таблицы person (по object_name),
--затем из таблицы menu (также по object_name)
--Сохранить дублирующиеся строки.

SELECT object_name FROM
(SELECT pizza_name AS object_name, 2 AS sourse FROM menu
UNION ALL
SELECT name AS object_name, 1 AS sourse FROM person)
AS combi
ORDER BY sourse, object_name;

--ex02
--Написать SQL-запрос, который:
--Возвращает уникальные названия пицц из таблицы menu
--Сортирует результаты по столбцу pizza_name в порядке убывания
--Запрещены DISTINCT, GROUP BY, HAVING, все виды JOINs

SELECT pizza_name FROM menu
UNION
SELECT pizza_name FROM menu
ORDER BY pizza_name DESC;

--ex03
--Написать SQL-запрос, который:
--Находит пересечение данных по:
--Дате заказа (order_date) и ID человека (person_id) из таблицы person_order
--Дате визита (visit_date) и ID человека (person_id) из таблицы person_visits
--Т.е. найти идентификаторы людей, которые в один и тот же день и посетили заведение, 
--и сделали заказ пиццы.
--Сортировка сначала по дате действия (action_date) в порядке возрастания,
--а затем по person_id — в порядке убывания.
--Запрещены все виды JOINs

SELECT order_date AS action_date, person_id FROM person_order
INTERSECT
SELECT visit_date AS action_date, person_id FROM person_visits
ORDER BY action_date ASC, person_id DESC;

--ex04
--Написать SQL-запрос, который вернет разницу по значениям столбца person_id 
--между таблицами person_order и person_visits, при этом сохраняя дубликаты.
--Запрос должен учитывать только записи за 7 января 2022 года
--Запрещены все виды JOINs

SELECT person_id FROM person_order WHERE order_date = '2022-01-07'
EXCEPT ALL
SELECT person_id FROM person_visits WHERE visit_date = '07.01.2022'

--ex05
--Напиcfnm SQL-запрос, который вернет все возможные комбинации записей 
--из таблиц person и pizzeria.
--В результате выполнения запроса сначала должны идти столбцы с идентификаторами 
--из таблицы person, а затем — из таблицы pizzeria.

SELECT * FROM person
CROSS JOIN pizzeria
ORDER BY person.id, pizzeria.id;

--ex06
--Изменить SQL-запрос из задания 3 так, чтобы он возвращал имена людей вместо их идентификаторов.
--Сортировка:
--Сначала по дате действия (action_date) в порядке возрастания
--Затем по имени человека (person_name) в порядке убывания

SELECT action_date, name AS person_name FROM
(SELECT order_date AS action_date, person_id FROM person_order
INTERSECT
SELECT visit_date AS action_date, person_id FROM person_visits)
AS dates
JOIN person ON person.id = dates.person_id
ORDER BY action_date ASC, person_name DESC;

--ex07
--Написать SQL-запрос, который возвращает:
--Дату заказа из таблицы person_order
--Имя человека, сделавшего заказ (из таблицы person), 
--имя и возраст должны быть отформатированы по образцу Andrey (age:21)
--Сортировка по обоим столбцам в порядке возрастания.

SELECT order_date,
       name || ' (age:'||age||')' AS person_information
FROM person_order
INNER JOIN person ON person.id = person_order.person_id
ORDER BY 1,2;

--ex08
--Переписать SQL-запрос из Задания 07, используя конструкцию NATURAL JOIN

SELECT
    po.order_date,
    p.name || ' (age:' || p.age || ')' AS person_information
FROM (SELECT person_id as id, order_date FROM person_order) AS po
NATURAL JOIN person p
ORDER BY po.order_date, person_information;

--ex09
--Напиcать два SQL-запроса, которые возвращают список пиццерий, в которые не заходили люди: 
--первый — с использованием оператора IN, 
--второй — с использованием EXISTS.

SELECT name FROM pizzeria p 
WHERE p.id NOT IN (SELECT pizzeria_id FROM person_visits);

SELECT  name FROMm pizzeria p 
WHERE NOT EXISTS
(SELECT  1 FROM person_visits
WHERE p.id = person_visits.pizzeria_id);

--ex10

--Написать SQL-запрос, который вернёт список имён людей, заказавших пиццу в соответствующей пиццерии.
--С указанием: Имени клиента, Названия пиццы, Названия пиццерии
--Сортировка по трём столбцам (все по возрастанию):
--имя_пользователя (имя клиента)
--pizza_name (название пиццы)
--pizzeria_name (название пиццерии)

 SELECT name AS person_name, pizza_name, pizzeria_name FROM person p 
 JOIN person_order ON p.id = person_order.person_id 
 JOIN menu ON person_order.menu_id = menu.id
 JOIN (SELECT id, name ASs pizzeria_name FROM pizzeria) AS pizzeria_modi
 ON menu.pizzeria_id = pizzeria_modi.id 
 ORDER BY person_name, pizza_name, pizzeria_name;
