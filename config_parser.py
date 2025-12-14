import re
import json
import sys

def remove_comments(text: str) -> str:
    """Удаляет однострочные и многострочные комментарии."""
    # Многострочные комментарии /+ ... +/
    text = re.sub(r'/\+\s*([\s\S]*?)\s*\+/', '', text)
    
    # Однострочные комментарии ' до конца строки
    lines = []
    for line in text.splitlines():
        if "'" in line:
            line = line.split("'", 1)[0].rstrip()
        lines.append(line)
    return "\n".join(lines)

def tokenize_value(value_str: str):
    """Простой токенизатор для значения (для разбора массивов и вложенных структур)."""
    tokens = []
    i = 0
    while i < len(value_str):
        c = value_str[i]
        if c.isspace():
            i += 1
            continue
        if c in ',)':
            tokens.append(c)
            i += 1
            continue
        if c == '(':
            tokens.append(c)
            i += 1
            continue
        if c == '#':
            tokens.append(c)
            i += 1
            continue
        # Строка в кавычках
        if c == '"':
            start = i
            i += 1
            while i < len(value_str) and value_str[i] != '"':
                i += 1
            i += 1  # пропустить закрывающую "
            tokens.append(value_str[start:i])
            continue
        # Слово/число
        start = i
        while i < len(value_str) and not value_str[i].isspace() and value_str[i] not in ',)(':
            i += 1
        tokens.append(value_str[start:i])
    return tokens

def parse_value(tokens: list, pos: int, constants: dict):
    """Парсит значение из списка токенов, начиная с позиции pos."""
    if pos >= len(tokens):
        raise ValueError("Неожиданный конец значения")
    
    token = tokens[pos]
    
    # Вычисление константы $(имя)
    if token.startswith('$(') and token.endswith(')'):
        name = token[2:-1]
        if name not in constants:
            raise ValueError(f"Неизвестная константа: {name}")
        return constants[name], pos + 1
    
    # Строка
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1], pos + 1
    
    # Hex число
    if re.match(r'^0[xX][0-9a-fA-F]+$', token):
        return int(token, 16), pos + 1
    
    # Десятичное число
    if re.match(r'^-?\d+$', token):
        return int(token), pos + 1
    
    # Массив #( ... )
    if token == '#(':
        pos += 1
        array = []
        while pos < len(tokens) and tokens[pos] != ')':
            val, pos = parse_value(tokens, pos, constants)
            array.append(val)
            if tokens[pos] == ',':
                pos += 1
        if pos >= len(tokens) or tokens[pos] != ')':
            raise ValueError("Незакрытый массив")
        return array, pos + 1
    
    # По умолчанию - строка (например, true/false/имя)
    return token, pos + 1

def parse_config(text: str) -> dict:
    constants = {}
    result = {}
    
    # Удаляем комментарии
    text = remove_comments(text)
    
    # Обрабатываем def имя = значение;
    text = re.sub(r'\s+', ' ', text)  # нормализуем пробелы для простоты
    def_matches = list(re.finditer(r'def\s+([a-zA-Z_]\w*)\s*=\s*(.*?);', text))
    for match in def_matches:
        name = match.group(1)
        val_str = match.group(2)
        toks = tokenize_value(val_str)
        value, _ = parse_value(toks, 0, constants)
        constants[name] = value
    
    # Удаляем def из текста
    for match in reversed(def_matches):
        text = text[:match.start()] + text[match.end():]
    
    # Обрабатываем обычные присваивания ключ = значение;
    assignments = re.finditer(r'([a-zA-Z_]\w*)\s*=\s*(.*?);', text)
    for match in assignments:
        key = match.group(1)
        val_str = match.group(2)
        toks = tokenize_value(val_str)
        value, _ = parse_value(toks, 0, constants)
        result[key] = value
    
    return result
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python config_parser.py <файл.conf>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        config_text = f.read()
    
    try:
        config = parse_config(config_text)
        print(json.dumps(config, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Ошибка парсинга: {e}", file=sys.stderr)
        sys.exit(1)
