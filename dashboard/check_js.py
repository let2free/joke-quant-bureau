import re

with open('etf_monitor.html', 'r', encoding='utf-8') as f:
    content = f.read()

script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    lines = js_code.split('\n')
    
    # 检查是否有未闭合的模板字符串
    in_template = False
    for i, line in enumerate(lines, 1):
        for char in line:
            if char == '`':
                in_template = not in_template
        if in_template and i % 50 == 0:
            print(f'Line {i}: 可能在模板字符串中')
    
    # 检查openManageModal函数是否存在
    if 'function openManageModal' in js_code:
        print('openManageModal 函数存在')
    else:
        print('错误：openManageModal 函数不存在')
    
    # 检查是否有语法错误
    try:
        compile(js_code, '<string>', 'exec')
        print('JavaScript 语法检查通过')
    except SyntaxError as e:
        print(f'JavaScript 语法错误: {e}')
