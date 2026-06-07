from sqlalchemy import text
from app.models.database import engine


SQL = """
ALTER TABLE products
ADD COLUMN IF NOT EXISTS external_id VARCHAR,
ADD COLUMN IF NOT EXISTS article VARCHAR,
ADD COLUMN IF NOT EXISTS description VARCHAR,
ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'local',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS power_type VARCHAR,
ADD COLUMN IF NOT EXISTS area_min FLOAT,
ADD COLUMN IF NOT EXISTS area_max FLOAT;

ALTER TABLE search_queries
ADD COLUMN IF NOT EXISTS min_price FLOAT,
ADD COLUMN IF NOT EXISTS max_price FLOAT,
ADD COLUMN IF NOT EXISTS power_type VARCHAR,
ADD COLUMN IF NOT EXISTS area_sotka FLOAT,
ADD COLUMN IF NOT EXISTS excluded_brand VARCHAR,
ADD COLUMN IF NOT EXISTS excluded_power_type VARCHAR;

CREATE TABLE IF NOT EXISTS search_results (
    id SERIAL PRIMARY KEY,
    search_query_id INTEGER NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    position INTEGER NOT NULL,
    score FLOAT DEFAULT 0,
    reasons_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_products_external_id
ON products(external_id);

CREATE INDEX IF NOT EXISTS ix_products_article
ON products(article);

CREATE INDEX IF NOT EXISTS ix_products_category
ON products(category);

CREATE INDEX IF NOT EXISTS ix_products_brand
ON products(brand);

CREATE INDEX IF NOT EXISTS ix_search_results_search_query_id
ON search_results(search_query_id);

CREATE INDEX IF NOT EXISTS ix_search_results_product_id
ON search_results(product_id);
"""


def main():
    with engine.begin() as connection:
        connection.execute(text(SQL))

    print("База данных обновлена.")


if __name__ == "__main__":
    main()