--ДЕНЬ 8

--Реализация бизнес-требований, обеспечение целостности данных через ограничения и индексы, 
--оптимизация производительности БД, работа с последовательностями и массовыми операциями,
--а также документирование структуры базы

--ex00
--Добавить новую бизнес-возможность в модель данных. 
--Каждый клиент хочет видеть персональную скидку, а каждый бизнес стремится быть ближе 
--к своим покупателям.
--Представить систему персональных скидок для клиентов с одной стороны и пиццерий — с другой. 
--Нужно создать новую таблицу отношений (имя person_discounts) со следующими правилами:
--Определить атрибут id в качестве Primary Key
--Определить атрибуты person_id и pizzeria_id как Foreign Keys для соответствующих таблиц 
--(типы данных должны совпадать с типами столбцов id в соответствующих родительских таблицах).
--Задать явные имена для ограничений внешнего ключа, используя шаблон fk_{table_name}_{column_name},
-- например, fk_person_discounts_person_id.
--Добавить атрибут discount для хранения значения скидки в процентах.
--Значение скидки может быть числом с плавающей запятой (тип данных numeric).


CREATE TABLE person_discounts (
    id BIGINT PRIMARY KEY,
    person_id BIGINT NOT NULL,
    pizzeria_id BIGINT NOT NULL,
    discount NUMERIC,
    CONSTRAINT uk_person_discounts UNIQUE (person_id, pizzeria_id),
    CONSTRAINT fk_person_discounts_person_id FOREIGN KEY (person_id) REFERENCES person(id),
    CONSTRAINT fk_person_discounts_pizzeria_id FOREIGN KEY (pizzeria_id) REFERENCES pizzeria(id)
);

--ex01
--Yаписать DML-оператор (INSERT INTO ... SELECT ...), который заполнит таблицу 
--person_discounts новыми записями, следуя приведенным правилам:
--Uруппировка данных по столбцам person_id и pizzeria_id.
--Рассчитать размер персональной скидки по следующему псевдокоду:
--Если количество заказов = 1, то скидка = 10.5
--Иначе если количество заказов = 2, то скидка = 22
--Иначе скидка = 30

--Чтобы создать первичный ключ для таблицы person_discounts,
--использовать следующую SQL-конструкцию: ROW_NUMBER() OVER () AS id

INSERT INTO person_discounts (id, person_id, pizzeria_id, discount)
SELECT 
    ROW_NUMBER() OVER () AS id,
    person_id,
    pizzeria_id, 
    CASE
        WHEN COUNT(order_date) = 1 THEN 10.5
        WHEN COUNT(order_date) = 2 THEN 22
        ELSE 30
    END discount
FROM person_order po
JOIN menu m ON po.menu_id = m.id
GROUP BY person_id, pizzeria_id;

--ex02
--Написать SQL-запрос, который возвращает список заказов с фактической стоимостью
-- и стоимостью с примененной скидкой для каждого клиента в соответствующей пиццерии. 
--Сортировка результатов по имени клиента и названию пиццы.
--Названия столбцов name, pizza_name, price, discount_price, pizzeria_name

SELECT
    p.name,
    m.pizza_name,
    m.price,
    (m.price - m.price * d.discount / 100) AS discount_price,
    pi.name AS pizzeria_name
FROM person p
JOIN person_order po ON p.id = po.person_id
JOIN menu m ON m.id = po.menu_id
JOIN pizzeria pi ON pi.id = m.pizzeria_id
JOIN person_discounts d ON p.id = d.person_id AND pi.id = d.pizzeria_id
ORDER BY p.name, m.pizza_name;

--ex03
--Создаnm уникальный многоколоночный индекс (с именем idx_person_discounts_unique),
-- который предотвратит дублирование пар идентификаторов person_id и pizzeria_id.
--После создания нового индекса, предоставить любое простое SQL-выражение,
--которое демонстрирует использование индекса (с помощью EXPLAIN ANALYZE).

CREATE UNIQUE INDEX idx_person_discounts_unique ON person_discounts (person_id, pizzeria_id);

SET enable_seqscan = OFF;

EXPLAIN ANALYZE
SELECT person_id, pizzeria_id
FROM person_discounts
WHERE person_id > 2 AND pizzeria_id > 3;

SET enable_seqscan = ON;

--ex04
--Добавить следующие правила ограничений (constraints) для существующих столбцов 
--таблицы person_discounts:
---Столбец person_id не должен содержать NULL (имя ограничения ch_nn_person_id).
--Столбец pizzeria_id не должен содержать NULL (имя ограничения ch_nn_pizzeria_id).
--Столбец discount не должен содержать NULL (имя ограничения ch_nn_discount).
--Столбец discount должен иметь значение по умолчанию 0 (0%).
--Столбец discount должен содержать значения в диапазоне от 0 до 100 
--(имя ограничения ch_range_discount).

ALTER TABLE person_discounts 
ADD CONSTRAINT ch_nn_person_id CHECK (person_id IS NOT NULL),
ADD CONSTRAINT ch_nn_pizzeria_id CHECK (pizzeria_id IS NOT NULL),
ADD CONSTRAINT ch_nn_discount CHECK (discount IS NOT NULL),
ALTER COLUMN discount SET DEFAULT 0,
ADD CONSTRAINT ch_range_discount CHECK (discount >= 0 AND discount <= 100);

--ex05
--В соответствии с политикой управления данными (Data Governance Policies), 
--необходимо добавить комментарии к таблице и ее столбцам.


COMMENT ON TABLE person_discounts
IS 'Таблица содержит информацию о персональных скидках клиентов в пиццериях';

COMMENT ON COLUMN person_discounts.id IS 'Уникальный идентификатор скидки';
COMMENT ON COLUMN person_discounts.person_id 
IS 'Уникальный идентификатор человека, которому предоставляется скидка';
COMMENT ON COLUMN person_discounts.pizzeria_id 
IS 'Уникальный идентификатор пиццерии, в которой предоставляется скидка';
COMMENT ON COLUMN person_discounts.discount 
IS 'Процент скидки у человека в конкретной пиццерии из расчета:
был ранее сделан один заказ - 10,5% скидки, два заказа - 22%, 3 - 30%';

--ex06
--Необходимо создать последовательность базы данных с именем seq_person_discounts 
--(начиная со значения 1) и установить значение по умолчанию для атрибута id
--таблицы person_discounts, чтобы оно автоматически бралось из seq_person_discounts
--при каждой вставке
--Важно: следующее значение последовательности должно быть равно 1.
--В этом случае нужно установить актуальное значение для последовательности на основе формулы: 
-- "количество строк в таблице person_discounts" + 1
--Нельзя использовать жёстко заданные значения (hard-coded) для количества строк,
--чтобы установить правильное значение для последовательности.

CREATE SEQUENCE IF NOT EXISTS seq_person_discounts
START 1
MINVALUE 1
NO MAXVALUE;

SELECT setval('seq_person_discounts', (SELECT MAX(id) + 1 FROM person_discounts));

ALTER TABLE person_discounts
ALTER COLUMN id SET DEFAULT nextval('seq_person_discounts');
