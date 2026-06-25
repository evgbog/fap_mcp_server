# MCP-сервер многомерных данных по продажам
# Итоговая версия — ежедневный разрез + date_level (март 2026)

from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP
import pandas as pd
import numpy as np
from datetime import datetime

np.random.seed(42)

# ====================== ЕЖЕДНЕВНЫЕ ДАННЫЕ ======================

start_date = datetime(2023, 1, 1)
end_date = datetime(2025, 12, 31)
date_range = pd.date_range(start=start_date, end=end_date, freq='D')

product_hierarchy = {
    "Электроника": ["SmartPhone X", "SmartPhone Pro", "Laptop Air", "Laptop Pro", "Wireless Headphones", "4K TV Ultra"],
    "Бытовая техника": ["Холодильник Smart", "Стиральная машина", "Пылесос робот", "Кофемашина", "Мультиварка"],
    "Одежда": ["Куртка зимняя", "Джинсы Slim", "Футболка Premium", "Кроссовки", "Худи"],
    "Мебель": ["Диван угловой", "Кровать двуспальная", "Стол обеденный", "Шкаф-купе"],
    "Косметика": ["Крем для лица", "Шампунь премиум", "Парфюм", "Маска для волос"],
    "Автотовары": ["Автомобильные шины", "Аккумулятор", "Видеорегистратор"],
    "Игрушки": ["Конструктор LEGO", "Кукла Barbie", "Машинка на пульте", "Настольная игра"]
}

n = 8000

dates = np.random.choice(date_range, n, replace=True)

categories = []
products = []
for _ in range(n):
    cat = np.random.choice(list(product_hierarchy.keys()))
    prod = np.random.choice(product_hierarchy[cat])
    categories.append(cat)
    products.append(prod)

data = {
    'date': dates,
    'product_category': categories,
    'product': products,
    'region': np.random.choice(['North', 'South', 'East', 'West', 'Central'], n),
    'sales': np.round(np.random.uniform(450, 24500, n), 2),
    'quantity': np.random.randint(1, 120, n).astype(int)
}

main_df = pd.DataFrame(data)

# Добавляем колонки для удобной агрегации
main_df['year'] = main_df['date'].dt.year
main_df['month'] = main_df['date'].dt.to_period('M').astype(str)  # '2025-01'
main_df['day'] = main_df['date'].dt.date

# ====================== МЕТАДАННЫЕ ======================

sources_metadata = {
    "synthetic-sales-2025": {
        "name": "Ежедневные продажи (демо)",
        "description": "Реалистичные ежедневные данные продаж за 2023–2025 годы с поддержкой агрегации по дням, месяцам и годам.",
        "type": "synthetic",
        "row_count": len(main_df),
        "last_update": "2026-03-12",
        "update_frequency": "daily",
        "relevance_score": 0.92,
        "has_data": True,
        "data_frame_key": "main",
        "dimensions": [
            {"id": "date",              "name": "Дата",               "description": "Дата продажи", "type": "temporal"},
            {"id": "year",              "name": "Год",                "description": "Год", "type": "temporal"},
            {"id": "month",             "name": "Месяц",              "description": "Месяц в формате YYYY-MM", "type": "temporal"},
            {"id": "product_category",  "name": "Категория продукта", "description": "Категория товара", "type": "categorical"},
            {"id": "product",           "name": "Продукт",            "description": "Наименование товара", "type": "categorical"},
            {"id": "region",            "name": "Регион",             "description": "Регион продаж", "type": "geographical"}
        ],
        "measures": [
            {
                "id": "sales",
                "name": "Выручка",
                "description": "Суммарная выручка от продаж",
                "important": True,
                "unit": "₽",
                "format": "currency",
                "data_type": "currency",
                "aggregation": "sum"
            },
            {
                "id": "quantity",
                "name": "Количество",
                "description": "Количество проданных единиц",
                "important": False,
                "unit": "шт",
                "format": "n0",
                "data_type": "integer",
                "aggregation": "sum"
            }
        ]
    }
}

mcp = FastMCP(
    name="MultiSourceSalesAnalytics",
    instructions="Сервер с ежедневными данными и поддержкой агрегации по date_level."
)

# ====================== ОБРАБОТКА ФИЛЬТРОВ ======================

def _apply_filters(df: pd.DataFrame, filters: Optional[Union[Dict, List]]) -> pd.DataFrame:
    if not filters:
        return df.copy()
    filtered = df.copy()

    if isinstance(filters, dict):
        for col, value in filters.items():
            if col in filtered.columns:
                if col == "date" and isinstance(value, list) and len(value) == 2:
                    # Диапазон дат
                    try:
                        start = pd.to_datetime(value[0])
                        end = pd.to_datetime(value[1])
                        filtered = filtered[(filtered['date'] >= start) & (filtered['date'] <= end)]
                    except:
                        filtered = filtered[filtered[col].isin(value)]
                elif isinstance(value, list):
                    filtered = filtered[filtered[col].isin(value)]
                else:
                    filtered = filtered[filtered[col] == value]
    return filtered

# ====================== ОСНОВНОЙ ИНСТРУМЕНТ ======================

@mcp.tool()
def query_data(
    source_id: str,
    dimensions: List[str],
    measures: List[str],
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    operation: str = "sum",
    date_level: Optional[str] = None   # "day", "month", "year"
) -> Dict[str, Any]:
    """Получает данные из заданного источника"""
    try:
        if source_id not in sources_metadata:
            raise ValueError(f"Источник '{source_id}' не найден")

        meta = sources_metadata[source_id]
        if not meta["has_data"]:
            return {"status": "error", "error": "У источника нет данных"}

        df = main_df.copy()
        filtered = _apply_filters(df, filters)

        # Обработка date_level
        group_cols = dimensions.copy()
        if date_level:
            level = date_level.lower()
            if level == "year":
                group_cols.append("year")
            elif level == "month":
                group_cols.append("month")
            elif level == "day":
                group_cols.append("date")
            else:
                raise ValueError(f"Неверный date_level: {date_level}. Допустимо: day, month, year")

        group_cols = list(dict.fromkeys(group_cols))  # удаляем дубликаты

        agg_dict = {m: operation for m in measures}

        if group_cols:
            result = filtered.groupby(group_cols).agg(agg_dict).reset_index()
        else:
            result = filtered.agg(agg_dict).to_frame().T

        return {
            "data": result.to_dict(orient='records'),
            "operation": operation,
            "date_level": date_level,
            "records": len(result),
            "source": source_id
        }

    except Exception as e:
        return {
            "status": "error",
            "error": "Ошибка при выполнении запроса",
            "message": str(e),
            "code": "QUERY_ERROR"
        }


# ====================== ВСПОМОГАТЕЛЬНЫЕ ИНСТРУМЕНТЫ ======================

@mcp.tool()
def get_data_sources() -> List[Dict[str, Any]]:
    """Список всех доступных источников данных"""
    return [{
        "id": sid,
        "name": meta["name"],
        "description": meta["description"],
        "type": meta["type"],
        "row_count": meta["row_count"],
        "last_update": meta["last_update"],
        "update_frequency": meta["update_frequency"],
        "relevance_score": meta["relevance_score"],
        "has_data": meta["has_data"]
    } for sid, meta in sources_metadata.items()]


@mcp.tool()
def get_dimensions(source_id: str) -> List[Dict[str, Any]]:
    """Измерения указанного источника"""
    if source_id not in sources_metadata:
        return [{"status": "error", "error": f"Источник '{source_id}' не найден"}]
    return sources_metadata[source_id]["dimensions"]


@mcp.tool()
def get_measures(source_id: str) -> List[Dict[str, Any]]:
    """Меры указанного источника"""
    if source_id not in sources_metadata:
        return [{"status": "error", "error": f"Источник '{source_id}' не найден"}]
    return sources_metadata[source_id]["measures"]


if __name__ == "__main__":
    print("MCP-сервер успешно запущен: MultiSourceSalesAnalytics")
    print(f"Записей: {len(main_df)}")
    print(f"Диапазон дат: {main_df['date'].min().date()} — {main_df['date'].max().date()}")
    mcp.run()