import json
from datetime import datetime

class HtmlReportExporter:
    """HTML 测试报告生成器"""
    
    @staticmethod
    def generate_html(report, data):
        # 1. 提取基础统计数据
        passed = data['total_cases'] - data['failed_cases'] - data['skipped_cases']
        failed = data['failed_cases']
        skipped = data['skipped_cases']
        duration = data.get('duration', 0)
        
        # 2. 准备用例详情数据
        details_list = data.get('test_details', [])
        details_json = json.dumps([{
            'name': d.get('name', ''),
            'status': d.get('status', 'UNKNOWN'),
            'duration': d.get('duration', 0),
            'error_message': d.get('error_message', ''),
            'result': d.get('result', {})
        } for d in details_list], ensure_ascii=False)
        
        # 3. 构造 HTML 模板 (含 CSS、JS、ECharts)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>测试详情报告 - {data.get('name', '未命名')}</title>
            
            <!-- 引入字体 -->
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            
            <!-- 引入 ECharts CDN -->
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
            
            <style>
                :root {{
                    --primary-color: #409eff;
                    --success-color: #67c23a;
                    --danger-color: #f56c6c;
                    --info-color: #909399;
                    --bg-color: #f5f7fa;
                    --card-bg: rgba(255, 255, 255, 0.9);
                    --text-main: #303133;
                    --text-secondary: #606266;
                    --border-color: #ebeef5;
                    --shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
                }}

                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}

                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
                    background-color: var(--bg-color);
                    color: var(--text-main); 
                    line-height: 1.6; 
                    padding: 30px;
                    background-image: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
                    min-height: 100vh;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                    animation: fadeInDown 0.8s ease;
                }}

                h1 {{ 
                    color: var(--text-main); 
                    font-size: 2.2rem;
                    font-weight: 700;
                    margin-bottom: 10px;
                }}
                
                .subtitle {{
                    color: var(--text-secondary);
                    font-size: 1.1rem;
                }}

                .glass-card {{
                    background: var(--card-bg);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 12px;
                    box-shadow: var(--shadow);
                    padding: 30px;
                    margin-bottom: 30px;
                    transition: transform 0.3s ease;
                }}
                
                .glass-card:hover {{
                    transform: translateY(-2px);
                }}

                .row {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-bottom: 30px;
                }}

                .col-summary {{ flex: 2; min-width: 300px; }}
                .col-chart {{ flex: 1; min-width: 300px; }}

                .summary-grid {{ 
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 20px;
                }}

                .stat-item {{
                    background: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid var(--border-color);
                    display: flex;
                    flex-direction: column;
                }}

                .stat-label {{ 
                    color: var(--text-secondary); 
                    font-size: 0.9rem;
                    margin-bottom: 8px;
                }}

                .stat-value {{ 
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: var(--text-main);
                }}
                
                .stat-value.passed {{ color: var(--success-color); }}
                .stat-value.failed {{ color: var(--danger-color); }}
                .stat-value.skipped {{ color: var(--info-color); }}

                #pieChart {{
                    width: 100%;
                    height: 250px;
                }}

                .section-title {{
                    font-size: 1.5rem;
                    margin-bottom: 20px;
                    color: var(--text-main);
                    border-left: 4px solid var(--primary-color);
                    padding-left: 10px;
                }}

                /* Filter Tabs */
                .filters {{
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                }}

                .filter-btn {{
                    padding: 8px 16px;
                    border: 1px solid var(--border-color);
                    background: #fff;
                    border-radius: 20px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.2s ease;
                }}

                .filter-btn:hover {{
                    border-color: var(--primary-color);
                    color: var(--primary-color);
                }}

                .filter-btn.active {{
                    background: var(--primary-color);
                    color: white;
                    border-color: var(--primary-color);
                }}
                .filter-btn.active[data-filter="PASSED"] {{ background: var(--success-color); border-color: var(--success-color); }}
                .filter-btn.active[data-filter="FAILED"] {{ background: var(--danger-color); border-color: var(--danger-color); }}
                .filter-btn.active[data-filter="SKIPPED"] {{ background: var(--info-color); border-color: var(--info-color); }}

                /* Accordion Styles */
                .case-item {{
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    margin-bottom: 12px;
                    background: #fff;
                    overflow: hidden;
                    animation: fadeIn 0.5s ease;
                }}

                .case-header {{
                    padding: 15px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    cursor: pointer;
                    background: #fdfdfd;
                    transition: background 0.2s;
                }}
                
                .case-header:hover {{
                    background: #f5f7fa;
                }}

                .case-title-wrap {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }}

                .case-status-tag {{
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    color: white;
                }}

                .status-PASSED {{ background-color: var(--success-color); }}
                .status-FAILED {{ background-color: var(--danger-color); }}
                .status-SKIPPED {{ background-color: var(--info-color); }}

                .case-duration {{
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                    background: var(--bg-color);
                    padding: 3px 8px;
                    border-radius: 4px;
                }}

                .case-body {{
                    display: none;
                    padding: 0;
                    border-top: 1px solid var(--border-color);
                }}

                .case-body.open {{
                    display: block;
                    animation: slideDown 0.3s ease-out forwards;
                }}

                .detail-section {{
                    padding: 20px;
                }}

                .error-block {{
                    background: #fef0f0;
                    color: #f56c6c;
                    padding: 15px;
                    border-radius: 6px;
                    font-size: 13px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-family: Consolas, Monaco, monospace;
                    margin-bottom: 15px;
                    border-left: 4px solid var(--danger-color);
                    overflow-x: auto;
                }}

                .json-block {{
                    background: #282c34;
                    color: #abb2bf;
                    padding: 15px;
                    border-radius: 6px;
                    font-size: 13px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-family: Consolas, Monaco, monospace;
                    overflow-x: auto;
                }}

                .label-title {{
                    font-weight: 600;
                    margin-bottom: 8px;
                    display: block;
                    font-size: 0.95rem;
                }}

                @keyframes fadeInDown {{
                    from {{ opacity: 0; transform: translateY(-20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                
                @keyframes fadeIn {{
                    from {{ opacity: 0; }}
                    to {{ opacity: 1; }}
                }}

                @keyframes slideDown {{
                    from {{ opacity: 0; transform: translateY(-10px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>测试引擎运行报告</h1>
                    <div class="subtitle">{data.get('name', 'N/A')} · {data.get('project_name', 'N/A')}</div>
                </div>

                <div class="row">
                    <div class="glass-card col-summary">
                        <h2 class="section-title">执行概览</h2>
                        <div class="summary-grid">
                            <div class="stat-item">
                                <span class="stat-label">测试类型</span>
                                <span class="stat-value" style="font-size: 1.2rem;">{data.get('test_type', 'N/A')}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">总用时</span>
                                <span class="stat-value">{duration:.2f} s</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">通过率</span>
                                <span class="stat-value">{data.get('pass_rate', 0)}%</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">执行环境</span>
                                <span class="stat-value" style="font-size: 1.1rem;">{data.get('environment_name', '-')}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">执行人</span>
                                <span class="stat-value" style="font-size: 1.1rem;">{data.get('executor_name', '-')}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">生成时间</span>
                                <span class="stat-value" style="font-size: 1rem;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="glass-card col-chart">
                        <h2 class="section-title">结果分布</h2>
                        <div id="pieChart"></div>
                    </div>
                </div>

                <div class="glass-card">
                    <h2 class="section-title">测试详情 ({data.get('total_cases', 0)} 个)</h2>
                    
                    <div class="filters">
                        <button class="filter-btn active" data-filter="ALL">全部 ({data.get('total_cases', 0)})</button>
                        <button class="filter-btn" data-filter="PASSED">通过 ({passed})</button>
                        <button class="filter-btn" data-filter="FAILED">失败 ({failed})</button>
                        <button class="filter-btn" data-filter="SKIPPED">跳过 ({skipped})</button>
                    </div>

                    <div id="casesContainer">
                        <!-- Cases will be rendered here by JS -->
                    </div>
                </div>
            </div>

            <script>
                // 注入测试数据
                const testData = {details_json};
                const chartData = [
                    {{ value: {passed}, name: '通过', itemStyle: {{ color: '#67c23a' }} }},
                    {{ value: {failed}, name: '失败', itemStyle: {{ color: '#f56c6c' }} }},
                    {{ value: {skipped}, name: '跳过', itemStyle: {{ color: '#909399' }} }}
                ];

                // 渲染图表
                const initChart = () => {{
                    const chartDom = document.getElementById('pieChart');
                    const myChart = echarts.init(chartDom);
                    const option = {{
                        tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} ({{d}}%)' }},
                        legend: {{ top: 'bottom' }},
                        series: [{{
                            name: '测试结果',
                            type: 'pie',
                            radius: ['40%', '70%'],
                            avoidLabelOverlap: false,
                            itemStyle: {{ borderRadius: 10, borderColor: '#fff', borderWidth: 2 }},
                            label: {{ show: false, position: 'center' }},
                            emphasis: {{ label: {{ show: true, fontSize: 18, fontWeight: 'bold' }} }},
                            labelLine: {{ show: false }},
                            data: chartData
                        }}]
                    }};
                    myChart.setOption(option);
                    
                    window.addEventListener('resize', () => myChart.resize());
                }};

                // 渲染用例列表
                const renderCases = (filter = 'ALL') => {{
                    const container = document.getElementById('casesContainer');
                    container.innerHTML = '';
                    
                    const filteredData = filter === 'ALL' 
                        ? testData 
                        : testData.filter(d => d.status === filter);
                        
                    if (filteredData.length === 0) {{
                        container.innerHTML = `<div style="text-align:center; padding: 40px; color: #909399;">暂无数据</div>`;
                        return;
                    }}

                    filteredData.forEach((item, index) => {{
                        const duration = (item.duration || 0).toFixed(2);
                        const cleanResult = item.result ? JSON.stringify(item.result, null, 2) : '';
                        
                        const div = document.createElement('div');
                        div.className = 'case-item';
                        div.innerHTML = `
                            <div class="case-header" onclick="toggleAccordion(this)">
                                <div class="case-title-wrap">
                                    <span class="case-status-tag status-${{item.status}}">${{item.status}}</span>
                                    <span style="font-weight: 500;">${{item.name}}</span>
                                </div>
                                <span class="case-duration">${{duration}}s</span>
                            </div>
                            <div class="case-body">
                                <div class="detail-section">
                                    ${{item.error_message ? `
                                    <span class="label-title">错误信息</span>
                                    <div class="error-block">${{item.error_message}}</div>
                                    ` : ''}}
                                    
                                    ${{cleanResult && cleanResult !== '{{}}' ? `
                                    <span class="label-title">执行快照</span>
                                    <div class="json-block">${{cleanResult}}</div>
                                    ` : ''}}
                                    
                                    ${{!item.error_message && (!cleanResult || cleanResult === '{{}}') ? `
                                    <div style="color: #909399; font-size: 13px;">用例执行成功，未生成特定的返回结果或错误信息。</div>
                                    ` : ''}}
                                </div>
                            </div>
                        `;
                        container.appendChild(div);
                    }});
                }};

                // Accordion Toggle Logic
                window.toggleAccordion = (headerElement) => {{
                    const body = headerElement.nextElementSibling;
                    const isOpen = body.classList.contains('open');
                    
                    // Close all bodies
                    document.querySelectorAll('.case-body').forEach(el => el.classList.remove('open'));
                    
                    if (!isOpen) {{
                        body.classList.add('open');
                    }}
                }};

                // Filter Buttons Logic
                document.querySelectorAll('.filter-btn').forEach(btn => {{
                    btn.addEventListener('click', (e) => {{
                        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                        e.target.classList.add('active');
                        renderCases(e.target.dataset.filter);
                    }});
                }});

                // 初始化
                document.addEventListener('DOMContentLoaded', () => {{
                    initChart();
                    renderCases();
                }});
            </script>
        </body>
        </html>
        """
        return html_content
