--ДЕНЬ 9

--День направлен на ключевые практические навыки SQL-анализа, 
--необходимые для решения реальных бизнес-задач: 
--агрегацию данных (расчет сумм, средних, минимума/максимума), группировку по атрибутам,
--фильтрацию результатов, соединение таблиц и работу с условиями.

--ex00
--Написать SQL-запрос, который возвращает идентификаторы людей (person_id) 
--и соответствующее количество посещений любых пиццерий.
--Отсортировать результат по количеству посещений в порядке убывания (descending), 
--а затем по идентификатору человека (person_id) в порядке возрастания (ascending).
--Название колонок person_id, count_of_visits

SELECT 
    pv.person_id,
    COUNT(visit_date) AS count_of_visits
FROM person_visits pv
GROUP BY pv.person_id
ORDER BY count_of_visits DESC, person_id;

--ex01
--Изменить SQL-запрос из Задания 00 так, чтобы он возвращал имя человека (name),
--а не его идентификатор.
--Дополнительное условие - нужно вывести только топ-4 человека с максимальным количеством визитов 
--в каждой пиццерии, отсортированных по имени человека.

SELECT 
    p.name,
    COUNT(visit_date) AS count_of_visits
FROM person_visits pv
JOIN person p ON pv.person_id = p.id
GROUP BY p.name
ORDER BY count_of_visits DESC, p.name
LIMIT 4;

--ex02
--Написать SQL-запрос, который выведет топ-3 заведения, которые являются самыми популярными 
--по количеству посещений и по количеству заказов, объединив результаты в один список.
--Добавить столбец action_type, который будет содержать значения 'order' (заказ) или 
--'visit' (посещение) в зависимости от того, из какой таблицы взяты данные.
--Отсортировать итоговый результат в порядке возрастания по столбцу action_type 
--и в порядке убывания по столбцу с количеством (count).
--Названия столбцов name, count, action_type


(SELECT 
    pi.name AS name,
    COUNT(visit_date) AS count,
    'visit' AS action_type
FROM person_visits pv
JOIN pizzeria pi ON pi.id = pv.pizzeria_id
GROUP BY pi.name
ORDER BY count DESC
LIMIT 3)
UNION ALL
(SELECT 
    pi.name AS name,
    COUNT(order_date) AS count,
    'order' AS action_type
FROM person_order po
JOIN menu m ON m.id = po.menu_id
JOIN pizzeria pi ON pi.id = m.pizzeria_id
GROUP BY pi.name
ORDER BY count DESC
LIMIT 3)
ORDER BY action_type, count DESC;

--ex03
--Написать SQL-запрос, который покажет, как рестораны группируются по количеству посещений
--и по количеству заказов, а затем объединить эти данные по названию пиццерии.
--Можно использовать внутренний запрос из Задания 02 (Restaurants by Visits and by Orders) 
--без каких-либо ограничений на количество строк.
--Добавить следующие правила:
--Вычислить общую сумму заказов и посещений для каждой пиццерии
--(учесть, что не все пиццерии могут присутствовать в обеих таблицах).
--Отсортировать результаты по столбцу total_count (общее количество) в порядке убывания, 
--а затем по столбцу name (название) в порядке возрастания.
--Названия столбцов name, total_count

SELECT 
    name, 
    SUM(count) AS total_count
FROM (
    (SELECT 
        pi.name AS name,
        COUNT(visit_date) AS count
    FROM person_visits pv
    JOIN pizzeria pi ON pi.id = pv.pizzeria_id
    GROUP BY pi.name)
    UNION ALL
    (SELECT 
        pi.name AS name,
        COUNT(order_date) AS count
    FROM person_order po
    JOIN menu m ON m.id = po.menu_id
    JOIN pizzeria pi ON pi.id = m.pizzeria_id
    GROUP BY pi.name)
) AS combined_data
GROUP BY name
ORDER BY total_count DESC, name;

--ex04
--Написать SQL-запрос, который возвращает имя человека (person name)
--и соответствующее количество посещений любых пиццерий при условии, 
--что это количество превышает 3 раза (> 3).
--Запрещена конструкция WHERE
--Названия столбцов name, count_of_visits

SELECT
    p.name,
    COUNT(visit_date) AS count_of_visits
FROM person p
JOIN person_visits pv ON pv.person_id = p.id
GROUP BY p.name
HAVING COUNT(visit_date) > 3;

--ex05
--Написать простой SQL-запрос, который возвращает список уникальных имен людей, 
--сделавших хотя бы один заказ в любой из пиццерий.
--Отсортировать результат по имени человека.
--Запрещены конструкции GROUP BY, any type (UNION,...) working with sets

SELECT DISTINCT
    p.name
FROM person p
JOIN person_order po ON po.person_id = p.id
ORDER BY p.name;


--ex06
--Написать SQL-запрос, который возвращает для каждой пиццерии:
--общее количество заказов, среднюю цену, максимальную цену
--и минимальную цену на проданные пиццы.
--Результат должен быть отсортирован по названию пиццерии. 
--Округлить среднюю цену до двух знаков после запятой.
--Названия колонок name, count_of_orders, average_price, max_price, min_price

SELECT 
    pi.name,
    COUNT(order_date) AS count_of_orders,
    ROUND(AVG(price), 2) AS average_price,
    MAX(price) AS max_price,
    MIN(price) AS min_price
FROM pizzeria pi
JOIN menu m ON pi.id = m.pizzeria_id
JOIN person_order po ON m.id = po.menu_id 
GROUP BY pi.name
ORDER BY name;

--ex07
--Написать SQL-запрос, который возвращает общий средний рейтинг 
--(выходной атрибут называется global_rating) для всех ресторанов.
--Округлить среднее значение рейтинга до 4 знаков после запятой.

SELECT 
    ROUND(AVG(rating), 4) AS global_rating
FROM pizzeria;

--ex08
--Из данных известны личные адреса людей. 
--Предположим, что человек посещает только пиццерии в своем городе.
--Написать SQL-запрос, который возвращает:
--Адрес (person address)
--Название пиццерии (pizzeria name)
--Сумму его заказов (amount of orders) в этой пиццерии.
--Отсортировать результат сначала по адресу, а затем по названию заведения.
--Названия колонок address, name, count_of_orders

SELECT 
    p.address,
    pi.name,
    COUNT(order_date) AS count_of_orders
FROM person p
JOIN person_order po ON p.id = po.person_id 
JOIN menu m ON m.id = po.menu_id 
JOIN pizzeria pi ON pi.id = m.pizzeria_id
GROUP BY p.address, pi.name
ORDER BY p.address, pi.name;

--ex09
--Написать SQL-запрос, который возвращает агрегированную информацию по адресу каждого человека.
--В результат должны быть включены:
--вычисляемый столбец с формулой: 
--«Максимальный возраст - (Минимальный возраст / Максимальный возраст)»,
--средний возраст по каждому адресу average age per address),
--результат сравнения формулы и среднего возраста 
--(то есть, если значение формулы больше среднего возраста, то значение должно быть True,
--иначе - False).
--Результат необходимо отсортировать по столбцу с адресом.
--Названия столбцов address, formula, average, comparison

SELECT 
    p.address,
    ROUND(MAX(p.age) - (MIN(p.age) / MAX(p.age::numeric)), 2) AS formula,
    ROUND(AVG(p.age), 2) AS average,
    CASE 
        WHEN (MAX(p.age) - (MIN(p.age) / MAX(p.age::numeric))) > AVG(p.age) THEN true 
        ELSE false        
    END comparison
FROM person p
GROUP BY p.address
ORDER BY p.address;