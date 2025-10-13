# Справочник уровней игроков

PLAYER_LEVELS = {
    "C": {
        "name": "Категория C (Любители)",
        "emoji": "🟢",
        "levels": {
            "1.0": "Новички",
            "1.5": "Начинающий",
            "2.0": "Продолжающий",
            "2.5": "Продвинутый"
        }
    },
    "B": {
        "name": "Категория B (Опытные)",
        "emoji": "🟡",
        "levels": {
            "3.0": "Опытный",
            "3.5": "Адванс",
            "4.0": "Адванс+",
            "4.5": "Эксперт"
        }
    },
    "A": {
        "name": "Категория A (Профи)",
        "emoji": "🔴",
        "levels": {
            "5.0": "Bronze",
            "5.5": "Silver",
            "6.0": "Gold",
            "6.5": "Platinum",
            "7.0": "Premier Padel",
            "7.5": "TOP Premier Padel"
        }
    }
}


def get_level_name(level_code):
    """
    Получить название уровня по коду
    
    Args:
        level_code (str): Код уровня, например "3.5"
    
    Returns:
        str: Название уровня, например "Адванс", или "Не установлен"
    
    Examples:
        >>> get_level_name("3.5")
        'Адванс'
        >>> get_level_name("1.0")
        'Новички'
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
        str: Код категории "C", "B", "A" или None
    
    Examples:
        >>> get_category_by_level("3.5")
        'B'
        >>> get_category_by_level("1.0")
        'C'
        >>> get_category_by_level("5.0")
        'A'
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
        category_code (str): Код категории "C", "B", "A"
    
    Returns:
        str: Полное название категории
    
    Examples:
        >>> get_category_name("B")
        'Категория B (Опытные)'
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
            'name': 'Адванс',
            'category': 'B',
            'category_name': 'Категория B (Опытные)',
            'emoji': '🟡'
        }
    
    Examples:
        >>> info = get_level_info("3.5")
        >>> info['name']
        'Адванс'
        >>> info['category']
        'B'
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
            f"📊 Категория: {info['category_name']}"  # ← ИЗМЕНИЛИ! Убрали {info['category']} -
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
        ('1.0', 'Новички')
    """
    all_levels = []
    for category in PLAYER_LEVELS.values():
        for code, name in category["levels"].items():
            all_levels.append((code, name))
    return all_levels