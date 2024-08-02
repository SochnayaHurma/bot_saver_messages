def get_next_page(previous_page: int, action: str):
    match action:
        case 'up':
            page = previous_page + 1
        case 'down' if previous_page > 1:
            page = previous_page - 1
        case _:
            page = 1
    return page
