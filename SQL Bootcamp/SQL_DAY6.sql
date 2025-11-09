--ДЕНЬ 6
--Применить SQL-инструменты для решения классической задачи коммивояжёра 
--(Traveling Salesman Problem)

--ex00
--Изучить граф. В нём четыре города (a, b, c и d) 
--и дуги между ними с указанием стоимости (или налогов).
--На самом деле стоимость одинакова в обе стороны, то есть cost(a, b) = cost(b, a).
--Создать таблицу с названными узлами по структуре {point1, point2, cost} 
--и заполнить её данными согласно изображению 
--Напиcать SQL-запрос, который вернет все маршруты (также называемые путями) 
--с минимальной суммарной стоимостью путешествия, если стартовать из города «a».
--Нужно найти самый дешевый способ посетить все города и вернуться в исходную точку.
--Отсортировать результат сначала по total_cost, а затем по маршруту (tour).

CREATE TABLE travel_costs (
    point1 VARCHAR NOT NULL,
    point2 VARCHAR NOT NULL,
    cost INTEGER NOT NULL DEFAULT 10
);

INSERT INTO travel_costs (point1, point2, cost)
VALUES
    ('a', 'b', 10),
    ('a', 'c', 15),
    ('a', 'd', 20),
    ('b', 'a', 10),
    ('b', 'c', 35),
    ('b', 'd', 25),
    ('c', 'a', 15),
    ('c', 'b', 35),
    ('c', 'd', 30),
    ('d', 'a', 20),
    ('d', 'b', 25),
    ('d', 'c', 30);

WITH RECURSIVE part_tour AS (
    SELECT
        ARRAY['a'::VARCHAR] AS travel_tour,
        'a'::VARCHAR AS last_city,
        0 AS total_cost

    UNION ALL

    SELECT
        travel_tour || tc.point2,
        tc.point2,
        total_cost + tc.cost
    FROM part_tour
    JOIN travel_costs tc ON last_city = tc.point1
    WHERE tc.point2 <> ALL(travel_tour) AND array_length(travel_tour, 1) < 4
),
completed_tours AS (
    SELECT
        array_append(travel_tour, 'a') AS tour,
        total_cost + (
            SELECT cost
            FROM travel_costs
            WHERE point1 = last_city AND point2 = 'a'
        ) AS total_cost
    FROM part_tour
    WHERE array_length(travel_tour, 1) = 4
)
SELECT
    total_cost,
    tour
FROM completed_tours
WHERE total_cost = (SELECT MIN(total_cost) FROM completed_tours)
ORDER BY
    total_cost,
    tour;


--ex01
--Добавить возможность вывести дополнительные строки с самой высокой стоимостью к SQL-запросу
--из предыдущего упражнения

WITH RECURSIVE part_tour AS (
    SELECT
        ARRAY['a'::VARCHAR] AS travel_tour,
        'a'::VARCHAR AS last_city,
        0 AS total_cost

    UNION ALL

    SELECT
        travel_tour || tc.point2,
        tc.point2,
        total_cost + tc.cost
    FROM part_tour
    JOIN travel_costs tc ON last_city = tc.point1
    WHERE tc.point2 <> ALL(travel_tour) AND array_length(travel_tour, 1) < 4
),
completed_tours AS (
    SELECT
        array_append(travel_tour, 'a') AS tour,
        total_cost + (
            SELECT cost
            FROM travel_costs
            WHERE point1 = last_city AND point2 = 'a'
        ) AS total_cost
    FROM part_tour
    WHERE array_length(travel_tour, 1) = 4
)
SELECT
    total_cost,
    tour
FROM completed_tours
WHERE total_cost = (SELECT MIN(total_cost) FROM completed_tours)
    OR total_cost = (SELECT MAX(total_cost) FROM completed_tours)
ORDER BY
    total_cost,
    tour;
