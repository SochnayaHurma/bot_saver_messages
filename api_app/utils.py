import math

from config import settings


def paginate(
        expected_page: int,
        count_db_rows: int,
        max_rows: int = settings.pagination.MAX_ROWS
):
    per_page = max_rows * (expected_page - 1)
    last_page = math.ceil(count_db_rows / max_rows)
    if per_page >= count_db_rows:
        per_page = count_db_rows - max_rows
        expected_page = last_page
    if last_page <= 1:
        expected_page = last_page = 1
        per_page = 0
    return {
        'current_page': expected_page,
        'skip': per_page,
        'limit': max_rows,
        'last_page': last_page
    }