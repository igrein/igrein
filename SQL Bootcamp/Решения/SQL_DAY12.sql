-- ДЕНЬ 12

-- День направлен на изучение принципов построения хранилищ данных (DWH) и создания ETL-процессов.
-- В рамках проекта предстоит работать с "неидеальными" данными: обрабатывать пропущенные значения,
-- связывать информацию из разных источников и корректно агрегировать показатели.
-- Эти навыки essential для построения ETL-пайплайнов, анализа данных с историей изменений
-- и подготовки данных для отчетности.

-- ex00 - Classical DWH
-- Задача: Расчет общего объема транзакций с учетом аномалий данных в распределенной системе
-- Требуется обработать данные из трех независимых источников (Green, Red, Blue Source Databases)
-- с рисками несогласованности данных и NULL значениями.
-- Ключевые аспекты:
-- - Обработка NULL значений в полях name и lastname через значение "not defined"
-- - Работа с историческими изменениями курсов валют (взятие последнего актуального курса)
-- - Суммирование денежных движений по пользователям и типам балансов
-- - Конвертация сумм в USD с использованием последних известных курсов
-- - Сортировка результатов по убыванию имени и возрастанию фамилии и типа баланса

SELECT 
    COALESCE(u.name, 'not defined') AS name,
    COALESCE(u.lastname, 'not defined') AS lastname,
    b.type,
    SUM(b.money) AS volume,
    COALESCE(c.name, 'not defined') AS currency_name,
    COALESCE(c.rate_to_usd, 1) AS last_rate_to_usd,
    SUM(b.money) * COALESCE(c.rate_to_usd, 1) AS total_volume_in_usd
FROM balance b
LEFT JOIN "user" u ON u.id = b.user_id
LEFT JOIN (
    SELECT DISTINCT ON (id)
        id,
        name,
        rate_to_usd,
        updated
    FROM currency
    ORDER BY id, updated DESC
) c ON b.currency_id = c.id
GROUP BY 
    COALESCE(u.name, 'not defined'),
    COALESCE(u.lastname, 'not defined'),
    b.type,
    COALESCE(c.name, 'not defined'),
    COALESCE(c.rate_to_usd, 1)
ORDER BY 
    name DESC,
    lastname ASC,
    type ASC;


-- ex01 - Detailed Query  
-- Задача: Детализированный анализ операций с временной привязкой курсов валют
-- Требуется найти для каждой операции баланса соответствующий курс валюты
-- на основе временных меток операций и обновлений курсов.
-- Ключевые аспекты:
-- - Поиск ближайшего курса валюты в прошлом относительно даты операции
-- - При отсутствии курсов в прошлом - поиск ближайшего курса в будущем
-- - Игнорирование валют, отсутствующих в справочнике Currency
-- - Обработка NULL значений в пользовательских данных
-- - Конвертация сумм операций в USD с использованием найденных курсов
-- - Сортировка по убыванию имени и возрастанию фамилии и названия валюты

INSERT INTO currency VALUES (100, 'EUR', 0.85, '2022-01-01 13:29');
INSERT INTO currency VALUES (100, 'EUR', 0.79, '2022-01-08 13:29');


WITH currency_rate AS (
    SELECT 
        b.user_id,
        b.money,
        b.currency_id,
        b.updated AS balance_updated,
        COALESCE(
            (SELECT c1.rate_to_usd 
            FROM currency c1
            WHERE c1.id = b.currency_id AND c1.updated <= b.updated 
            ORDER BY c1.updated DESC
            LIMIT 1),
            (SELECT c2.rate_to_usd 
            FROM currency c2
            WHERE c2.id = b.currency_id AND c2.updated > b.updated 
            ORDER BY c2.updated
            LIMIT 1)
        ) AS rate_to_usd,
        (SELECT name FROM currency WHERE id = b.currency_id LIMIT 1) AS currency_name
    FROM balance b 
    WHERE EXISTS (SELECT 1 FROM currency c WHERE c.id = b.currency_id)
)
SELECT 
    COALESCE(u.name, 'not defined') AS name,
    COALESCE(u.lastname, 'not defined') AS lastname,
    cr.currency_name,
    cr.money * cr.rate_to_usd AS currency_in_usd
FROM currency_rate cr
LEFT JOIN "user" u ON u.id = cr.user_id
ORDER BY name DESC, lastname, currency_name;
