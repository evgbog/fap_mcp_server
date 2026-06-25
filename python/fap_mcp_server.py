import json
import requests

from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP

import pprint
from datetime import datetime
from pathlib import Path

SERVICE_URL = "http://10.30.222.13:8110/fp10.x/app/PPService.axd"
FORE_EXEC_TOKEN = "{483A82ED-9A21-BC4F-A329-1A6D8D320AA6}"
METABASE_ID = "DUPR_PG"
MCP_MODULE_KEY = "81677"

import json
import pprint
from datetime import datetime
from pathlib import Path
from typing import Any


def log_params(
        file_path: str | Path,
        *args: Any,
        sep: str = "=" * 80,
        timestamp: bool = True,
        **kwargs: Any
) -> None:
    """
    Логирует переданные параметры в текстовый файл в удобочитаемом формате.

    Args:
        file_path: путь к файлу лога
        *args: позиционные параметры
        **kwargs: именованные параметры
        sep: разделитель между записями
        timestamp: добавлять ли временную метку
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    if timestamp:
        lines.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]")

    lines.append("Параметры вызова:")

    # Позиционные аргументы
    if args:
        lines.append("  Позиционные аргументы:")
        for i, arg in enumerate(args):
            lines.append(f"    {i}: {format_value(arg)}")

    # Именованные аргументы
    if kwargs:
        lines.append("  Именованные аргументы:")
        for key, value in kwargs.items():
            lines.append(f"    {key}: {format_value(value)}")

    if not args and not kwargs:
        lines.append("  Нет переданных параметров")

    lines.append(sep)

    # Записываем в файл
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def format_value(value: Any, indent: int = 4) -> str:
    """Форматирует значение в читаемый вид (особенно dict, list, set и т.д.)"""
    if isinstance(value, (dict, list, tuple, set)):
        try:
            # Используем pprint для красивого вывода
            pp = pprint.PrettyPrinter(
                indent=indent,
                width=100,
                sort_dicts=False,
                compact=False
            )
            formatted = pp.pformat(value)
            # Убираем лишние отступы в начале
            if '\n' in formatted:
                return '\n' + formatted
            return formatted
        except:
            pass

    # Для простых типов
    if isinstance(value, str):
        return f'"{value}"'
    elif value is None:
        return 'None'
    elif isinstance(value, bool):
        return str(value)

    # Пробуем через json (для объектов, которые можно сериализовать)
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except:
        return str(value)


def fore_exec_atomic(metabase_id, token, module_key, method_name, *args):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "ForeExecAtomic":
            {
                "tArg":
                    {
                        "token": token,
                        "metabaseId": metabase_id,
                        "objKey": module_key,
                        "foreArg":
                            {
                                "methodName": method_name,
                                "args":
                                    {
                                        "it":
                                            [
                                            ]
                                    }
                            }
                    }
            }
    }

    for index, value in enumerate(args):
        payload['ForeExecAtomic']['tArg']['foreArg']['args']['it'].append({'k': str(index+1), 'value': value})

    # print(payload)

    try:
        response = None
        response = requests.post(
            SERVICE_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        # Проверка статуса
        response.raise_for_status()

        # Получаем JSON
        data = response.json()
        result_data = json.loads(data["ForeExecAtomicResult"]["result"])
        return result_data, True, '', ''

    except requests.exceptions.HTTPError as e:
        return None, False, 'Ошибка HTTP: ' + str(e), response.text if response is not None else ''
    except requests.exceptions.RequestException as e:
        return None, False, 'Ошибка соединения: ' + str(e), response.text if response is not None else ''
    except ValueError:
        return None, False, 'Сервер вернул не JSON', response.text if response is not None else ''

# val, ExecOk, ErrorName, ResponseText = fore_exec_atomic(METABASE_ID, FORE_EXEC_TOKEN, "81677", "MCP_GetDataSources")
# print(val, ExecOk, ErrorName, ResponseText)
# exit()

# ====================== FastMCP ======================

mcp = FastMCP(
    name="FAP_AI_Analytics",
    instructions="MCP-сервер для многомерной аналитики в ФАП мощным инструментом query_data."
)

# ====================== ИНСТРУМЕНТЫ ======================

@mcp.tool()
def get_data_sources() -> List[Dict[str, Any]]:
    """Список всех доступных источников данных"""
    val, ExecOk, ErrorName, ResponseText = fore_exec_atomic(METABASE_ID, FORE_EXEC_TOKEN, MCP_MODULE_KEY, "MCP_GetDataSources")
    if ExecOk:
        return val['data_sources']
    else:
        return [{"error": "Не удалось получить список источников данных"}]

@mcp.tool()
def get_dimensions(source_id: str) -> List[Dict[str, str]]:
    """Измерения указанного источника"""
    val, ExecOk, ErrorName, ResponseText = fore_exec_atomic(METABASE_ID, FORE_EXEC_TOKEN, MCP_MODULE_KEY, "MCP_GetDimensions", source_id)
    if ExecOk:
        return val['dimensions']
    else:
        return [{"error": "Не удалось получить список измерений"}]

@mcp.tool()
def get_measures(source_id: str) -> List[Dict[str, Any]]:
    """Меры указанного источника"""
    val, ExecOk, ErrorName, ResponseText = fore_exec_atomic(METABASE_ID, FORE_EXEC_TOKEN, MCP_MODULE_KEY, "MCP_GetMetrics", source_id)
    if ExecOk:
        return val['metrics']
    else:
        return [{"error": "Не удалось получить список мер"}]

@mcp.tool()
def query_data(
    source_id: str,
    dimensions: List[str],
    measures: List[str],
    # filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]], str]] = None,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]], str, None]] = None,
    operation: str = "sum",
    date_level: Optional[str] = None  # "day", "month", "year"
) -> Dict[str, Any]:
    # логирование параметров для отладки
    log_params("mcp.log", type='Вызов  query_data()',  source_id=source_id, dimensions=dimensions, measures=measures, filters=filters, date_level=date_level)
    # сформируем строку фильтра
    filter_str = ""
    if filters is None or filters == "null" or filters == "" or filters == "None" or filters == "{}"  or filters == "[]":
        pass
    elif isinstance(filters, dict):
        parts = []
        for dim, values in filters.items():
            if isinstance(values, list):
                values_str = "|".join(str(v) for v in values)  # str() на случай, если значения не строки
            else:
                values_str = str(values)
            parts.append(f"{dim}:{values_str}")
        filter_str = ";".join(parts)
    elif isinstance(filters, str):
        filters = json.loads(filters)
        parts = []
        for dim, values in filters.items():
            if isinstance(values, list):
                values_str = "|".join(str(v) for v in values)  # str() на случай, если значения не строки
            else:
                values_str = str(values)
            parts.append(f"{dim}:{values_str}")
        filter_str = ";".join(parts)
    else:
        log_params("mcp.log", type='Результат  query_data()', result={"error": "Некорректный параметр filters"})
        return {"error": "Некорректный параметр filters"}
    if date_level is None or date_level == "null":
        date_level = ""
    val, ExecOk, ErrorName, ResponseText = fore_exec_atomic(METABASE_ID, FORE_EXEC_TOKEN, MCP_MODULE_KEY, "MCP_QueryData", source_id, ','.join(dimensions), ','.join(measures), filter_str, 'sum', date_level)
    if ExecOk:
        log_params("mcp.log", type='Результат  query_data()', result=val['query_data'])
        return val['query_data']
    else:
        log_params("mcp.log", type='Результат  query_data()', result={"error": "Не удалось получить данные. " + ErrorName})
        return {"error": "Не удалось получить данные" + ErrorName}



if __name__ == "__main__":
    print("MCP-сервер запущен: Многомерный анализ в ФАП")
    # mcp.run()
    mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8000
        )

# TESTS
# print(get_measures('CUB_RAW_MATERIALS_IND'))
# print(get_data_sources())
# print(query_data('OBJ80708_MCP', [], ['0', '1'], []))
# print(query_data('OBJ80708_MCP', ['month'], ['f_1'], '{"date": ["2020-01-01", "2020-03-31"]}', date_level="month"))
# print(query_data('OBJ80708_MCP', ['DIM_TERR'], ['f_1']))
# print(query_data('OBJ80708_MCP', ['DIM_TERR'], ['f_1'], {'DIM_TERR':['Пермский край', 'Самарская область']})) # 48348578308.0
# print(query_data('OBJ80708_MCP', ['DIM_TERR'], ['f_1'], {'DIM_TERR':['Пермский край']})) # 48348578308.0
# print(query_data('OBJ80708_MCP', ['DIM_TERR'], ['f_1'], {'DIM_TERR':'Пермский край'})) # 48348578308.0


