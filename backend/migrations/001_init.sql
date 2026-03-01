-- ============================================
-- Схема базы данных маркетплейса
-- ============================================

-- Включаем расширение UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- TODO: Создать таблицу order_statuses
CREATE TABLE IF NOT EXISTS order_statuses
(
    status      VARCHAR(50) PRIMARY KEY,
    description TEXT
);
-- Столбцы: status (PK), description


-- TODO: Вставить значения статусов
INSERT INTO order_statuses (status, description)
VALUES ('created', 'created status'),
       ('paid', 'paid status'),
       ('cancelled', 'cancelled status'),
       ('shipped', 'shipped status'),
       ('completed', 'completed status');
-- created, paid, cancelled, shipped, completed


-- TODO: Создать таблицу users
CREATE TABLE IF NOT EXISTS users
(
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email      VARCHAR(255) UNIQUE NOT NULL CHECK ( email ~* '^[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$' and email != ''),
    name       VARCHAR(255),
    created_at TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);
-- Столбцы: id (UUID PK), email, name, created_at
-- Ограничения:
--   - email UNIQUE
--   - email NOT NULL и не пустой
--   - email валидный (regex через CHECK)


-- TODO: Создать таблицу orders
CREATE TABLE IF NOT EXISTS orders
(
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID        NOT NULL REFERENCES users (id),
    status       VARCHAR(50) NOT NULL REFERENCES order_statuses (status),
    total_amount INTEGER CHECK ( total_amount >= 0 ),
    created_at   TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);

-- Столбцы: id (UUID PK), user_id (FK), status (FK), total_amount, created_at
-- Ограничения:
--   - user_id -> users(id)
--   - status -> order_statuses(status)
--   - total_amount >= 0


-- TODO: Создать таблицу order_items
CREATE TABLE order_items
(
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id     UUID         NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_name VARCHAR(512) NOT NULL CHECK ( product_name != '' ),
    price        NUMERIC(12, 2) CHECK ( price >= 0 ),
    quantity     INTEGER CHECK ( quantity > 0 )
);
-- Столбцы: id (UUID PK), order_id (FK), product_name, price, quantity
-- Ограничения:
--   - order_id -> orders(id) CASCADE
--   - price >= 0
--   - quantity > 0
--   - product_name не пустой


-- TODO: Создать таблицу order_status_history
CREATE TABLE IF NOT EXISTS order_status_history
(
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id   UUID        NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    status     VARCHAR(50) NOT NULL REFERENCES order_statuses (status),
    changed_at TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);
-- Столбцы: id (UUID PK), order_id (FK), status (FK), changed_at
-- Ограничения:
--   - order_id -> orders(id) CASCADE
--   - status -> order_statuses(status)


-- ============================================
-- КРИТИЧЕСКИЙ ИНВАРИАНТ: Нельзя оплатить заказ дважды
-- ============================================
-- TODO: Создать функцию триггера check_order_not_already_paid()
-- При изменении статуса на 'paid' проверить что его нет в истории
-- Если есть - RAISE EXCEPTION
CREATE OR REPLACE FUNCTION check_order_not_already_paid()
    RETURNS TRIGGER AS
$$
BEGIN

    IF NEW.satus = 'paid' AND OLD.status != 'paid' THEN
        IF EXISTS (SELECT 1
                   FROM order_status_history
                   WHERE order_id = NEW.id
                     AND status = 'paid') THEN
            RAISE EXCEPTION 'Заказ % уже оплачен', NEW.id;
        END IF;
    END IF;

END ;
$$ LANGUAGE plpgsql;



-- TODO: Создать триггер trigger_check_order_not_already_paid
-- BEFORE UPDATE ON orders FOR EACH ROW

CREATE TRIGGER trigger_check_order_not_already_paid
    BEFORE UPDATE
    ON orders
    FOR EACH ROW
EXECUTE FUNCTION check_order_not_already_paid();

-- ============================================
-- БОНУС (опционально)
-- ============================================
-- TODO: Триггер автоматического пересчета total_amount

CREATE OR REPLACE FUNCTION recalc_total_amount()
    RETURNS TRIGGER AS
$$
DECLARE
    target_order_id UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        target_order_id := OLD.order_od;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.order_id != OLD.order_id THEN
            UPDATE orders
            SET total_amount = coalesce((SELECT SUM(price * total_amount)
                                         FROM order_items
                                         WHERE order_id = OLD.order_id), 0)
            WHERE id = OLD.order_id;
        end if;

        target_order_id := NEW.order_id;
    ELSE
        target_order_id := NEW.order_id;
    END IF;

    UPDATE orders
    SET total_amount = (SELECT coalesce(SUM(price * quantity), 0)
                        FROM order_items
                        WHERE order_id = NEW.order_Id)
    WHERE id = NEW.order_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER recalc_total_amount_trigger
    AFTER INSERT OR UPDATE OR DELETE
    ON order_items
    FOR EACH ROW
EXECUTE FUNCTION recalc_total_amount();


-- TODO: Триггер автоматической записи в историю при изменении статуса
-- TODO: Триггер записи начального статуса при создании заказа

CREATE OR REPLACE FUNCTION log_order_status_change()
    RETURNS TRIGGER AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO order_status_history(id, order_id, status)
        VALUES (uuid_generate_v4(), NEW.id, NEW.status);
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.status != OLD.status THEN
            INSERT INTO order_status_history(order_id, status)
            VALUES (NEW.id, NEW.status);
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_order_status_change_trigger
    AFTER UPDATE OR INSERT
    ON orders
    FOR EACH ROW
EXECUTE FUNCTION log_order_status_change();
