--ДЕНЬ 1 
--направлен на изучение создание SQL-запросов с использованием 
--внутренних подзапросов в частях FROM и SELECT,
--а также фильтрацию данных по диапазоу дат

--ex00
--Задача написать запрос SELECT, который вернет имена и возраст всех людей из города «Казань»

SELECT name, age 
FROM person
WHERE address = 'Kazan';

--ex01
--Задача написать запрос SELECT, который выведет имена и возраст всех женщин из города «Казань».
--Отсортировать результат по имени

SELECT name, age FROM person
WHERE (address = 'Kazan') AND (gender = 'female')
ORDER BY name;

--ex02
--Составить два разных по синтаксису запроса SELECT, 
--которые вернут список пиццерий (название и рейтинг) с рейтингом от 3.5 до 5 включительно, 
--отсортированный по рейтингу.

SELECT name, rating FROM pizzeria
WHERE rating >= 3.5 AND rating <= 5
ORDER BY rating;

SELECT name, rating FROM pizzeria
WHERE rating BETWEEN 3.5 AND 5
ORDER BY rating;

--ex03
--Составить запрос SELECT, который вернет уникальные идентификаторы людей, 
--посетивших пиццерии в период с 6 по 9 января 2022 года (включительно), 
--либо посетивших пиццерии с идентификатором 2.
--Отсортировать результа по идентификатору человека в порядке убывания.

SELECT DISTINCT person_id FROM person_visits
WHERE (visit_date BETWEEN '2022-01-06' AND '2022-01-09') OR (pizzeria_id = 2)
ORDER BY person_id DESC;

--ex04
--Составить запрос SELECT, который вернет одно вычисляемое поле с именем person_information 
--в виде одной строки, как показано в примере:
--Anna (age:16,gender:'female',address:'Moscow')
--Сортировка по этому вычисляемому полю в порядке возрастания

SELECT name || ' (age:'|| age::text || ',gender:''' || gender ||''',address:''' || address || ''')' 
AS person_information
FROM person
ORDER BY name;

--ex05
--Написать запрос SELECT, который вернет имена людей 
--(используя внутренний запрос в части SELECT),
-- которые сделали заказы по меню с идентификаторами 13, 14 и 18, 
--при этом дата заказа должна быть 7 января 2022 года.
--Запрещены IN, все виды JOINs

SELECT
(SELECT name FROM person WHERE po.person_id = id) AS name
FROM person_order po
WHERE (menu_id = 13 OR menu_id = 14 OR menu_id = 18) AND order_date = '2022-01-07';

--ex06
--Используя конструкцию SQL из Задания 05, добавить в оператор SELECT 
--новый вычисляемый столбец с именем check_name. 
--В этом столбце необходимо реализовать проверку по следующему псевдокоду:
--if (person_name == 'Denis'), вернуть true, иначе вернуть false.
--Запрещены IN, все виды JOINs

SELECT
(SELECT name FROM person WHERE po.person_id = id) AS name,
((SELECT name FROM person WHERE po.person_id = id) = 'Denis') AS check_name
FROM person_order po
WHERE (menu_id = 13 OR menu_id = 14 OR menu_id = 18) AND order_date = '2022-01-07';

--ex07
--Написать SQL-запрос, который вернет идентификаторы людей, их имена и интервал 
--по возрасту в виде нового вычисляемого столбца с именем interval_info, 
--согласно следующему псевдокоду:
--if (age >= 10 and age <= 20) - вернуть «interval #1»
--else if (age > 20 and age < 24) - вернуть «interval #2»
--во всех остальных случаях - вернуть «interval #3»
--Сортировка результата по столбцу interval_info в порядке возрастания.

SELECT id, name,
    CASE 
        WHEN age BETWEEN 10 AND 20 THEN 'interval #1'
        WHEN age > 20 AND age < 24 THEN 'interval #2'
        ELSE 'interval #3'
    END AS interval_info
FROM person
ORDER BY interval_info;

--ex08
--Написать SQL-запрос, который возвращает все столбцы из таблицы person_order, 
--где идентификатор является четным числом.
--Результат должен быть отсортирован по этому идентификатору.

SELECT *
FROM person_order po 
WHERE id%2 = 0
ORDER BY id;

--ex09
--Составить запрос SELECT, который вернет имена людей и названия пиццерий 
--на основе таблицы person_visits с датами посещений в период с 7 по 9 января 2022 года (включительно), 
--используя внутренний запрос в части FROM.
--Сортировка по имени человека в порядке возрастания и по названию пиццерии в порядке убывания.
--Запрещены все виды JOINs

SELECT
    (SELECT name FROM person WHERE id = pv.person_id) AS person_name,
    (SELECT name FROM pizzeria WHERE id = pv.pizzeria_id) AS pizzeria_name
FROM (SELECT person_id, pizzeria_id, visit_date 
      FROM person_visits 
      WHERE visit_date BETWEEN '2022-01-07' AND '2022-01-09') AS pv
ORDER BY person_name ASC, pizzeria_name DESC;