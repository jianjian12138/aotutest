"""
AI测试报告PDF生成器
使用reportlab生成专业的PDF报告
"""
import os
from datetime import datetime
from typing import Dict, List, Any
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    import logging
    logger = logging.getLogger('django')
    logger.warning(f"reportlab import failed: {e}")

import logging
logger = logging.getLogger('django')


class AIReportPDFGenerator:
    """AI测试报告PDF生成器"""

    def __init__(self, report_data: Dict[str, Any], report_type: str = 'summary'):
        """
        初始化PDF生成器

        Args:
            report_data: 报告数据
            report_type: 报告类型 (summary/detailed/performance)
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 库未安装，请运行: pip install reportlab")

        self.report_data = report_data
        self.report_type = report_type
        self.buffer = BytesIO()

        # 注册中文字体
        self._register_fonts()

        # 创建样式
        self.styles = self._create_styles()

    def _register_fonts(self):
        """注册中文字体"""
        try:
            # 尝试注册系统中常见的中文字体
            font_paths = [
                # macOS
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                # Linux
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                # Windows
                'C:/Windows/Fonts/simhei.ttf',
                'C:/Windows/Fonts/msyh.ttf',
            ]

            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                        font_registered = True
                        logger.info(f"✅ Registered Chinese font: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to register font {font_path}: {e}")
                        continue

            if not font_registered:
                logger.warning("⚠️ No Chinese font found, PDF may not display Chinese correctly")
                # 使用Helvetica作为备用
                self.font_name = 'Helvetica'
            else:
                self.font_name = 'ChineseFont'

        except Exception as e:
            logger.error(f"❌ Error registering fonts: {e}")
            self.font_name = 'Helvetica'

    def _create_styles(self):
        """创建文档样式"""
        styles = getSampleStyleSheet()

        # 自定义样式
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name,
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=18,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=20,
        ))

        styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=styles['Heading3'],
            fontName=self.font_name,
            fontSize=14,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=10,
            spaceBefore=15,
        ))

        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            leading=16,
        ))

        styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d'),
        ))

        return styles

    def generate(self) -> BytesIO:
        """
        生成PDF文档

        Returns:
            BytesIO: PDF文件的字节流
        """
        # 创建PDF文档
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # 构建文档内容
        story = []
        story.extend(self._build_header())
        story.append(Spacer(1, 0.5*cm))

        # 根据报告类型生成不同内容
        if self.report_type == 'summary':
            story.extend(self._build_summary_report())
        elif self.report_type == 'detailed':
            story.extend(self._build_detailed_report())
        elif self.report_type == 'performance':
            story.extend(self._build_performance_report())

        # 生成PDF
        doc.build(story)
        self.buffer.seek(0)
        return self.buffer

    def _build_header(self):
        """构建报告头部"""
        story = []

        # 标题
        report_type_names = {
            'summary': '执行摘要报告',
            'detailed': '详细步骤报告',
            'performance': '性能分析报告'
        }
        title = f"AI测试执行 - {report_type_names.get(self.report_type, '测试报告')}"
        story.append(Paragraph(title, self.styles['CustomTitle']))

        # 执行详情
        overview = self.report_data.get('overview', {})
        execution_details = self.report_data.get('execution_details', {})

        # 创建执行信息表格
        info_data = [
            ['用例名称', execution_details.get('case_name', 'N/A')],
            ['执行状态', overview.get('status', 'N/A')],
            ['执行模式', execution_details.get('execution_mode', 'N/A')],
            ['执行时长', overview.get('duration_formatted', 'N/A')],
            ['完成率', f"{overview.get('completion_rate', 0)}%"],
            ['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ]

        info_table = Table(info_data, colWidths=[5*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('PAD', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        return story

    def _build_summary_report(self):
        """构建摘要报告"""
        story = []

        # 任务统计
        story.append(Paragraph('任务统计', self.styles['CustomHeading2']))

        statistics = self.report_data.get('statistics', {})
        if statistics:
            stats_data = [
                ['统计项', '数量'],
                ['总任务数', str(statistics.get('total', 0))],
                ['已完成', str(statistics.get('completed', 0))],
                ['待执行', str(statistics.get('pending', 0))],
                ['失败', str(statistics.get('failed', 0))],
                ['跳过', str(statistics.get('skipped', 0))],
            ]

            stats_table = Table(stats_data, colWidths=[8*cm, 7*cm])
            stats_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#3498db')),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('PAD', (0, 0), (-1, -1), 8),
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.5*cm))

        # 任务时间线
        story.append(Paragraph('任务执行时间线', self.styles['CustomHeading2']))

        timeline = self.report_data.get('timeline', [])
        if timeline:
            timeline_data = [['任务ID', '描述', '状态']]
            for task in timeline:
                status_display = task.get('status_display', 'N/A')
                timeline_data.append([
                    f"任务 {task.get('id', 'N/A')}",
                    task.get('description', 'N/A'),
                    status_display
                ])

            timeline_table = Table(timeline_data, colWidths=[2.5*cm, 8*cm, 4.5*cm])
            timeline_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PAD', (0, 0), (-1, -1), 6),
            ]))
            story.append(timeline_table)

        # 添加性能分析摘要（如果数据可用）
        self._add_performance_summary(story)

        return story

    def _add_performance_summary(self, story):
        """添加性能分析摘要到报告"""
        # 检查是否有性能数据
        metrics = self.report_data.get('metrics')
        action_distribution = self.report_data.get('action_distribution')

        if not metrics and not action_distribution:
            return

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph('性能摘要', self.styles['CustomHeading2']))

        # 性能指标
        if metrics:
            perf_data = [
                ['指标', '值'],
                ['总步骤数', str(metrics.get('total_steps', 0))],
                ['平均耗时', f"{metrics.get('avg_step_duration', 0)} 秒"],
                ['最长耗时', f"{metrics.get('max_step_duration', 0)} 秒"],
                ['最短耗时', f"{metrics.get('min_step_duration', 0)} 秒"],
            ]

            perf_table = Table(perf_data, colWidths=[8*cm, 7*cm])
            perf_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#27ae60')),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('PAD', (0, 0), (-1, -1), 6),
            ]))
            story.append(perf_table)
            story.append(Spacer(1, 0.3*cm))

        # 操作类型分布（简要）
        if action_distribution:
            action_names = {
                'click': '点击',
                'input': '输入',
                'scroll': '滚动',
                'wait': '等待',
                'switch_tab': '切换标签',
                'navigate': '导航',
                'open_tab': '新标签',
                'done': '完成',
                'other': '其他'
            }

            distribution_data = [['操作', '次数']]
            for key, name in action_names.items():
                count = action_distribution.get(key, 0)
                if count > 0:
                    distribution_data.append([name, str(count)])

            if len(distribution_data) > 1:
                distribution_table = Table(distribution_data, colWidths=[8*cm, 7*cm])
                distribution_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#27ae60')),
                    ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ecf0f1')),
                    ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('PAD', (0, 0), (-1, -1), 6),
                ]))
                story.append(distribution_table)

    def _build_detailed_report(self):
        """构建详细步骤报告"""
        story = []

        # 执行步骤详情
        story.append(Paragraph('执行步骤详情', self.styles['CustomHeading2']))

        detailed_steps = self.report_data.get('detailed_steps', [])
        if detailed_steps:
            for step in detailed_steps:
                # 步骤标题
                step_header = f"步骤 {step.get('step_number', 'N/A')}"
                story.append(Paragraph(step_header, self.styles['CustomHeading3']))

                # 步骤内容
                step_data = [
                    ['操作', step.get('action', 'N/A')],
                    ['元素', step.get('element', '-')],
                    ['状态', step.get('status', 'N/A')],
                ]

                # 如果有思考过程，添加到表格中
                thinking = step.get('thinking', '')
                if thinking:
                    step_data.append(['思考', thinking])

                step_table = Table(step_data, colWidths=[3*cm, 12*cm])
                step_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PAD', (0, 0), (-1, -1), 6),
                ]))
                story.append(step_table)
                story.append(Spacer(1, 0.3*cm))

        # 错误信息
        errors = self.report_data.get('errors', [])
        if errors:
            story.append(Paragraph('错误信息', self.styles['CustomHeading2']))
            for error in errors:
                error_style = ParagraphStyle(
                    'ErrorStyle',
                    parent=self.styles['CustomNormal'],
                    textColor=colors.red,
                    fontName=self.font_name
                )
                story.append(Paragraph(f"• {error.get('message', 'Unknown error')}", error_style))

        return story

    def _build_performance_report(self):
        """构建性能分析报告"""
        story = []

        # 性能指标
        story.append(Paragraph('性能指标', self.styles['CustomHeading2']))

        metrics = self.report_data.get('metrics', {})
        if metrics:
            metrics_data = [
                ['指标', '值'],
                ['总步骤数', str(metrics.get('total_steps', 0))],
                ['平均步骤耗时', f"{metrics.get('avg_step_duration', 0)} 秒"],
                ['最长步骤耗时', f"{metrics.get('max_step_duration', 0)} 秒"],
                ['最短步骤耗时', f"{metrics.get('min_step_duration', 0)} 秒"],
            ]

            metrics_table = Table(metrics_data, colWidths=[8*cm, 7*cm])
            metrics_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('PAD', (0, 0), (-1, -1), 8),
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 0.5*cm))

        # 操作类型分布
        story.append(Paragraph('操作类型分布', self.styles['CustomHeading2']))

        action_distribution = self.report_data.get('action_distribution', {})
        if action_distribution:
            action_names = {
                'click': '点击',
                'input': '输入',
                'scroll': '滚动',
                'wait': '等待',
                'switch_tab': '切换标签',
                'navigate': '导航',
                'open_tab': '新标签',
                'done': '任务完成',
                'other': '其他'
            }

            distribution_data = [['操作类型', '次数']]
            for key, name in action_names.items():
                count = action_distribution.get(key, 0)
                if count > 0:
                    distribution_data.append([name, str(count)])

            distribution_table = Table(distribution_data, colWidths=[8*cm, 7*cm])
            distribution_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#3498db')),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('PAD', (0, 0), (-1, -1), 8),
            ]))
            story.append(distribution_table)
            story.append(Spacer(1, 0.5*cm))

        # 性能瓶颈
        bottlenecks = self.report_data.get('bottlenecks', [])
        if bottlenecks:
            story.append(Paragraph('性能瓶颈', self.styles['CustomHeading2']))

            bottleneck_data = [['步骤', '操作', '耗时(秒)', '慢于平均']]
            for bn in bottlenecks:
                bottleneck_data.append([
                    f"步骤 {bn.get('step_number', 'N/A')}",
                    bn.get('action', 'N/A'),
                    str(bn.get('duration', 0)),
                    f"{bn.get('slower_than_avg_by', 0)}%"
                ])

            bottleneck_table = Table(bottleneck_data, colWidths=[2*cm, 8*cm, 3*cm, 2*cm])
            bottleneck_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('PAD', (0, 0), (-1, -1), 6),
            ]))
            story.append(bottleneck_table)
            story.append(Spacer(1, 0.5*cm))

        # 优化建议
        recommendations = self.report_data.get('recommendations', [])
        if recommendations:
            story.append(Paragraph('优化建议', self.styles['CustomHeading2']))
            for i, rec in enumerate(recommendations, 1):
                story.append(Paragraph(f"{i}. {rec}", self.styles['CustomNormal']))

        return story
