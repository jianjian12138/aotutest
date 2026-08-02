import re
import logging

logger = logging.getLogger(__name__)

class CaseGenerator:
    """测试用例生成服务"""
    
    @staticmethod
    def parse_playwright_code(code: str):
        """
        解析Playwright代码并转换为测试步骤列表
        目前支持标准codegen生成的同步代码
        """
        steps = []
        lines = code.split('\n')
        
        step_order = 1
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 解析 page.goto
            if 'page.goto(' in line:
                match = re.search(r"page\.goto\(['\"](.*?)['\"]\)", line)
                if match:
                    steps.append({
                        'step_order': step_order,
                        'action_type': 'custom', # 暂时映射为自定义，或者需要增加 navigate 类型
                        'description': f'导航至 {match.group(1)}',
                        'action_params': {'code': line, 'type': 'goto', 'url': match.group(1)}
                    })
                    step_order += 1
                    continue
            
            # 解析 page.click
            if 'page.click(' in line:
                match = re.search(r"page\.click\(['\"](.*?)['\"]\)", line)
                if match:
                    selector = match.group(1)
                    steps.append({
                        'step_order': step_order,
                        'action_type': 'click',
                        'description': f'点击元素 {selector}',
                        'action_params': {'selector': selector}
                    })
                    step_order += 1
                    continue
            
            # 解析 page.locator(...).click()
            if '.click()' in line and 'page.locator(' in line:
                match = re.search(r"page\.locator\(['\"](.*?)['\"]\)", line)
                if match:
                    selector = match.group(1)
                    steps.append({
                        'step_order': step_order,
                        'action_type': 'click',
                        'description': f'点击元素 {selector}',
                        'action_params': {'selector': selector}
                    })
                    step_order += 1
                    continue

            # 解析 page.fill / page.locator(...).fill()
            if '.fill(' in line:
                # page.fill('selector', 'value')
                fill_match = re.search(r"page\.fill\(['\"](.*?)['\"],\s*['\"](.*?)['\"]\)", line)
                if fill_match:
                    selector = fill_match.group(1)
                    value = fill_match.group(2)
                    steps.append({
                        'step_order': step_order,
                        'action_type': 'fill',
                        'description': f'在 {selector} 输入 "{value}"',
                        'action_params': {'selector': selector, 'value': value},
                        'input_value': value
                    })
                    step_order += 1
                    continue
                
                # page.locator('selector').fill('value')
                locator_match = re.search(r"page\.locator\(['\"](.*?)['\"]\)\.fill\(['\"](.*?)['\"]\)", line)
                if locator_match:
                    selector = locator_match.group(1)
                    value = locator_match.group(2)
                    steps.append({
                        'step_order': step_order,
                        'action_type': 'fill',
                        'description': f'在 {selector} 输入 "{value}"',
                        'action_params': {'selector': selector, 'value': value},
                        'input_value': value
                    })
                    step_order += 1
                    continue

            # 解析 expect (断言)
            if 'expect(' in line:
                # expect(page.locator('...')).to_be_visible()
                if 'to_be_visible()' in line:
                    match = re.search(r"expect\(page\.locator\(['\"](.*?)['\"]\)\)", line)
                    if match:
                        selector = match.group(1)
                        steps.append({
                            'step_order': step_order,
                            'action_type': 'assert',
                            'description': f'断言元素 {selector} 可见',
                            'assert_type': 'isVisible',
                            'action_params': {'selector': selector}
                        })
                        step_order += 1
                        continue
                
                # expect(page.locator('...')).to_have_text('...')
                if 'to_have_text(' in line:
                    match = re.search(r"expect\(page\.locator\(['\"](.*?)['\"]\)\)\.to_have_text\(['\"](.*?)['\"]\)", line)
                    if match:
                        selector = match.group(1)
                        text = match.group(2)
                        steps.append({
                            'step_order': step_order,
                            'action_type': 'assert',
                            'description': f'断言元素 {selector} 文本包含 "{text}"',
                            'assert_type': 'textContains',
                            'assert_value': text,
                            'action_params': {'selector': selector, 'text': text}
                        })
                        step_order += 1
                        continue

            # 其他未识别的步骤作为自定义代码处理
            # 简单过滤掉无关代码
            if line.startswith('from ') or line.startswith('import ') or line == 'with sync_playwright() as p:' or line == 'browser = p.chromium.launch()' or line == 'context = browser.new_context()' or line == 'page = context.new_page()' or line == 'browser.close()':
                continue

            # 记录为自定义代码步骤
            steps.append({
                'step_order': step_order,
                'action_type': 'custom',
                'description': f'执行代码: {line[:50]}...',
                'action_params': {'code': line}
            })
            step_order += 1
            
        return steps
