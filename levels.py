# Справочник уровней игроков

PLAYER_LEVELS = {
    "L1": {
        "name": "Категория L1",
        "emoji": "🟢",
        "levels": {
            "1.0": "Уровень 1.0",
            "1.25": "Уровень 1.25",
            "1.5": "Уровень 1.5",
            "1.75": "Уровень 1.75"
        }
    },
    "L2": {
        "name": "Категория L2",
        "emoji": "🔵",
        "levels": {
            "2.0": "Уровень 2.0",
            "2.25": "Уровень 2.25",
            "2.5": "Уровень 2.5",
            "2.75": "Уровень 2.75"
        }
    },
    "L3": {
        "name": "Категория L3",
        "emoji": "🟡",
        "levels": {
            "3.0": "Уровень 3.0",
            "3.25": "Уровень 3.25",
            "3.5": "Уровень 3.5",
            "3.75": "Уровень 3.75"
        }
    },
    "L4": {
        "name": "Категория L4",
        "emoji": "🟠",
        "levels": {
            "4.0": "Уровень 4.0",
            "4.25": "Уровень 4.25",
            "4.5": "Уровень 4.5",
            "4.75": "Уровень 4.75"
        }
    },
    "L5": {
        "name": "Категория L5",
        "emoji": "🔴",
        "levels": {
            "5.0": "Уровень 5.0",
            "5.25": "Уровень 5.25",
            "5.5": "Уровень 5.5",
            "5.75": "Уровень 5.75"
        }
    }
}


def get_level_name(level_code):
    """
    Получить название уровня по коду
    
    Args:
        level_code (str): Код уровня, например "3.5"
    
    Returns:
        str: Название уровня, например "Уровень 3.5", или "Не установлен"
    
    Examples:
        >>> get_level_name("3.5")
        'Уровень 3.5'
        >>> get_level_name("1.0")
        'Уровень 1.0'
        >>> get_level_name(None)
        'Не установлен'
    """
    if not level_code:
        return "Не установлен"
    
    for category in PLAYER_LEVELS.values():
        if level_code in category["levels"]:
            return category["levels"][level_code]
    
    return "Не установлен"


def get_category_by_level(level_code):
    """
    Получить код категории по уровню
    
    Args:
        level_code (str): Код уровня, например "3.5"
    
    Returns:
        str: Код категории "L1", "L2", "L3", "L4", "L5" или None
    
    Examples:
        >>> get_category_by_level("3.5")
        'L3'
        >>> get_category_by_level("1.0")
        'L1'
        >>> get_category_by_level("5.0")
        'L5'
    """
    if not level_code:
        return None
    
    for cat_code, category in PLAYER_LEVELS.items():
        if level_code in category["levels"]:
            return cat_code
    
    return None


def get_category_name(category_code):
    """
    Получить полное название категории
    
    Args:
        category_code (str): Код категории "L1", "L2", "L3", "L4", "L5"
    
    Returns:
        str: Полное название категории
    
    Examples:
        >>> get_category_name("L3")
        'Категория L3'
    """
    if category_code in PLAYER_LEVELS:
        return PLAYER_LEVELS[category_code]["name"]
    return "Неизвестная категория"


def get_level_info(level_code):
    """
    Получить полную информацию об уровне
    
    Args:
        level_code (str): Код уровня, например "3.5"
    
    Returns:
        dict: Словарь с информацией об уровне или None
        {
            'code': '3.5',
            'name': 'Уровень 3.5',
            'category': 'L3',
            'category_name': 'Категория L3',
            'emoji': '🟡'
        }
    
    Examples:
        >>> info = get_level_info("3.5")
        >>> info['name']
        'Уровень 3.5'
        >>> info['category']
        'L3'
    """
    if not level_code:
        return None
    
    for cat_code, category in PLAYER_LEVELS.items():
        if level_code in category["levels"]:
            return {
                'code': level_code,
                'name': category["levels"][level_code],
                'category': cat_code,
                'category_name': category["name"],
                'emoji': category["emoji"]
            }
    
    return None


def format_level_display(level_code):
    """
    Отформатировать уровень для отображения пользователю
    """
    if not level_code:
        return "⭐ Уровень: Не установлен"
    
    info = get_level_info(level_code)
    if info:
        return (
            f"⭐ Уровень: {info['code']} ({info['name']})\n"
            f"📊 Категория: {info['category_name']}"
        )
    
    return "⭐ Уровень: Не установлен"


def check_level_in_range(player_level, min_level, max_level):
    """
    Проверить, входит ли уровень игрока в диапазон
    
    Args:
        player_level (str): Уровень игрока, например "3.5"
        min_level (str): Минимальный уровень, например "3.0"
        max_level (str): Максимальный уровень, например "4.5"
    
    Returns:
        bool: True если уровень в диапазоне, False если нет
    
    Examples:
        >>> check_level_in_range("3.5", "3.0", "4.5")
        True
        >>> check_level_in_range("2.5", "3.0", "4.5")
        False
        >>> check_level_in_range(None, "3.0", "4.5")
        False
    """
    if not player_level or not min_level or not max_level:
        return False
    
    try:
        player = float(player_level)
        min_lvl = float(min_level)
        max_lvl = float(max_level)
        
        return min_lvl <= player <= max_lvl
    except (ValueError, TypeError):
        return False


def get_all_levels_list():
    """
    Получить список всех доступных уровней
    
    Returns:
        list: Список кортежей (код, название)
        
    Examples:
        >>> levels = get_all_levels_list()
        >>> levels[0]
        ('1.0', 'Уровень 1.0')
    """
    all_levels = []
    for category in PLAYER_LEVELS.values():
        for code, name in category["levels"].items():
            all_levels.append((code, name))
    return all_levels