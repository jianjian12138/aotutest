# -*- coding: utf-8 -*-
"""
先进的测试需求分析服务
基于业务需求生成测试类型和测试点的结构化分析
"""

import json
import re
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

class AdvancedTestRequirementAnalyzer:
    """先进的测试需求分析器 - 基于业务需求生成测试类型和测试点"""
    
    def __init__(self):
        self.analysis_stages = [
            "document_preprocessing",
            "requirement_extraction", 
            "requirement_structuring",
            "quality_assessment",
            "risk_analysis"
        ]
    
    async def analyze_requirements_advanced(self, text: str, document_title: str = "") -> Dict[str, Any]:
        """
        先进的需求分析方法
        参考autogen_demo_v8的多智能体协作模式
        """
        try:
            logger.info(f"开始先进需求分析，文档标题: {document_title}")
            
            # 1. 文档预处理
            preprocessed_text = await self._preprocess_document(text)
            
            # 2. 需求提取和分析
            analysis_report = await self._generate_comprehensive_analysis(
                preprocessed_text, document_title
            )
            
            # 3. 结构化需求生成
            structured_requirements = await self._extract_structured_requirements(
                analysis_report, preprocessed_text
            )
            
            # 4. 质量评估
            quality_assessment = await self._assess_requirement_quality(
                structured_requirements
            )
            
            # 5. 风险分析
            risk_analysis = await self._analyze_risks(structured_requirements)
            
            # 6. 生成完整报告
            final_report = await self._generate_final_report(
                analysis_report, quality_assessment, risk_analysis
            )
            
            return {
                "analysis_report": final_report,
                "structured_requirements": structured_requirements,
                "quality_assessment": quality_assessment,
                "risk_analysis": risk_analysis,
                "requirements_count": len(structured_requirements.get("requirements", []))
            }
            
        except Exception as e:
            logger.error(f"先进需求分析失败: {e}")
            raise e
    
    async def _preprocess_document(self, text: str) -> str:
        """文档预处理"""
        # 清理文本
        text = re.sub(r'\s+', ' ', text)  # 合并多个空格
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 规范化换行
        
        # 提取关键信息段落
        sections = self._identify_document_sections(text)
        
        return text
    
    def _identify_document_sections(self, text: str) -> Dict[str, str]:
        """识别文档章节"""
        sections = {}
        
        # 常见章节标识符
        section_patterns = {
            "功能需求": r"(?i)(功能需求|functional\s+requirements?|features?)",
            "非功能需求": r"(?i)(非功能需求|non-functional\s+requirements?|quality)",
            "业务流程": r"(?i)(业务流程|business\s+process|workflow)",
            "用户角色": r"(?i)(用户角色|user\s+roles?|actors?)",
            "系统架构": r"(?i)(系统架构|system\s+architecture|technical)",
            "接口定义": r"(?i)(接口定义|interfaces?|apis?)"
        }
        
        for section_name, pattern in section_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                start = match.start()
                # 提取该段落后的内容（简化实现）
                section_text = text[start:start+1000]
                sections[section_name] = section_text
                break
        
        return sections
    
    async def _generate_comprehensive_analysis(self, text: str, title: str) -> str:
        """生成全面的测试需求分析报告"""
        
        # 模拟AI分析过程（实际项目中应调用真实的AI服务）
        await asyncio.sleep(1)
        
        # 基于文本内容生成更智能的分析
        text_length = len(text)
        word_count = len(text.split())
        
        # 识别关键业务词汇
        business_keywords = self._extract_business_keywords(text)
        
        # 识别功能模块（用于测试覆盖分析）
        modules = self._identify_functional_modules(text)
        
        # 识别测试类型
        test_types = self._identify_test_types(text)
        
        # 识别测试场景
        test_scenarios = self._identify_test_scenarios(text)
        
        analysis_report = f"""
# 测试需求分析报告

## 1. 业务需求概述
- **需求标题**: {title}
- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **业务领域**: {', '.join(business_keywords[:5]) if business_keywords else '通用系统'}

## 2. 测试类型与测试点

{self._format_detailed_test_points(test_types)}

## 3. 测试场景
{self._format_test_scenarios_analysis(test_scenarios)}

## 4. 功能模块测试覆盖
{self._format_modules_for_testing(modules)}
        """
        
        return analysis_report.strip()
    
    def _extract_business_keywords(self, text: str) -> List[str]:
        """提取业务关键词"""
        # 常见业务词汇
        business_terms = [
            "用户", "客户", "订单", "支付", "商品", "库存", "报表", "审核", "流程",
            "权限", "角色", "部门", "项目", "任务", "文档", "消息", "通知", "设置",
            "管理", "查询", "统计", "分析", "导入", "导出", "登录", "注册", "profile"
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for term in business_terms:
            if term in text_lower:
                found_keywords.append(term)
        
        return found_keywords
    
    def _identify_functional_modules(self, text: str) -> List[Dict[str, Any]]:
        """识别功能模块"""
        modules = []
        
        # 基于关键词识别模块
        if "用户" in text or "登录" in text:
            modules.append({
                "name": "用户管理模块",
                "priority": "★",
                "risk": "⚠️" if "第三方" in text else "",
                "description": "负责用户注册、登录、权限管理等功能"
            })
        
        if "订单" in text or "购买" in text:
            modules.append({
                "name": "订单管理模块", 
                "priority": "★",
                "risk": "⚠️",
                "description": "处理订单创建、支付、状态跟踪等业务流程"
            })
        
        if "报告" in text or "报表" in text or "统计" in text:
            modules.append({
                "name": "报表统计模块",
                "priority": "⚡",
                "risk": "",
                "description": "提供各类业务数据的统计和报表功能"
            })
        
        if "数据" in text or "信息" in text:
            modules.append({
                "name": "数据管理模块",
                "priority": "★",
                "risk": "",
                "description": "负责核心业务数据的增删改查操作"
            })
        
        return modules
    
    def _identify_user_roles(self, text: str) -> List[str]:
        """识别用户角色"""
        roles = []
        
        role_keywords = {
            "管理员": ["管理员", "admin", "administrator"],
            "普通用户": ["用户", "user", "客户", "customer"],
            "操作员": ["操作员", "operator", "工作人员"],
            "审核员": ["审核员", "审核", "reviewer", "审批"]
        }
        
        text_lower = text.lower()
        for role, keywords in role_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    roles.append(role)
                    break
        
        return list(set(roles)) if roles else ["普通用户", "管理员"]
    
    def _identify_business_flows(self, text: str) -> List[str]:
        """识别业务流程"""
        flows = []
        
        # 基于关键词模式识别流程
        if "登录" in text:
            flows.append("用户认证流程")
        if "注册" in text:
            flows.append("用户注册流程")
        if "订单" in text:
            flows.append("订单处理流程")
        if "支付" in text:
            flows.append("支付结算流程")
        if "审核" in text:
            flows.append("审核批准流程")
        if "报告" in text or "报表" in text:
            flows.append("报表生成流程")
        
        return flows if flows else ["数据处理流程", "用户操作流程"]
    
    def _identify_test_types(self, text: str) -> List[Dict[str, Any]]:
        """识别测试类型"""
        test_types = []
        
        # 功能测试
        if any(keyword in text for keyword in ["功能", "登录", "注册", "查询", "添加", "删除", "修改"]):
            test_types.append({
                "type": "功能测试",
                "priority": "高",
                "description": "验证系统功能是否按预期工作",
                "test_points": self._get_functional_test_points(text)
            })
        
        # 界面测试
        if any(keyword in text for keyword in ["界面", "页面", "用户体验", "交互", "显示"]):
            test_types.append({
                "type": "界面测试", 
                "priority": "中",
                "description": "验证用户界面的正确性和易用性",
                "test_points": self._get_ui_test_points(text)
            })
        
        # 性能测试
        if any(keyword in text for keyword in ["性能", "响应", "并发", "负载", "压力"]):
            test_types.append({
                "type": "性能测试",
                "priority": "中", 
                "description": "验证系统性能指标是否满足要求",
                "test_points": self._get_performance_test_points(text)
            })
        
        # 安全测试
        if any(keyword in text for keyword in ["安全", "权限", "登录", "密码", "认证"]):
            test_types.append({
                "type": "安全测试",
                "priority": "高",
                "description": "验证系统安全性和权限控制",
                "test_points": self._get_security_test_points(text)
            })
        
        # 数据测试
        if any(keyword in text for keyword in ["数据", "信息", "录入", "导入", "导出"]):
            test_types.append({
                "type": "数据测试",
                "priority": "高",
                "description": "验证数据处理的准确性和完整性",
                "test_points": self._get_data_test_points(text)
            })
        
        # 兼容性测试
        if any(keyword in text for keyword in ["兼容", "浏览器", "设备", "平台"]):
            test_types.append({
                "type": "兼容性测试",
                "priority": "中",
                "description": "验证系统在不同环境下的兼容性",
                "test_points": self._get_compatibility_test_points(text)
            })
        
        # 如果没有识别出特定测试类型，提供默认的测试类型
        if not test_types:
            test_types = [
                {
                    "type": "功能测试",
                    "priority": "高", 
                    "description": "验证系统基本功能",
                    "test_points": ["正常功能验证", "异常处理验证", "边界值测试"]
                },
                {
                    "type": "界面测试",
                    "priority": "中",
                    "description": "验证用户界面", 
                    "test_points": ["界面布局验证", "交互操作验证", "显示内容验证"]
                }
            ]
        
        return test_types
    
    def _identify_test_scenarios(self, text: str) -> List[str]:
        """识别测试场景"""
        scenarios = []
        
        # 基于关键词识别测试场景
        if "登录" in text:
            scenarios.extend(["正常登录场景", "用户名错误场景", "密码错误场景", "账户锁定场景"])
        if "注册" in text:
            scenarios.extend(["正常注册场景", "重复注册场景", "信息不完整场景"])
        if "订单" in text:
            scenarios.extend(["订单创建场景", "订单支付场景", "订单取消场景", "订单查询场景"])
        if "支付" in text:
            scenarios.extend(["正常支付场景", "支付失败场景", "支付超时场景"])
        if "数据" in text:
            scenarios.extend(["数据录入场景", "数据查询场景", "数据修改场景", "数据删除场景"])
        if "报表" in text or "统计" in text:
            scenarios.extend(["报表生成场景", "数据筛选场景", "报表导出场景"])
        
        return scenarios if scenarios else ["基本功能场景", "异常处理场景", "边界条件场景"]
    
    def _format_modules_analysis(self, modules: List[Dict[str, Any]]) -> str:
        """格式化模块分析"""
        if not modules:
            return "- 基础数据管理模块 (★)\n- 用户交互模块\n- 系统配置模块"
        
        result = []
        for module in modules:
            flags = f"{module.get('priority', '')}{module.get('risk', '')}"
            result.append(f"- {module['name']} ({flags})")
            result.append(f"  - {module['description']}")
        
        return "\n".join(result)
    
    def _format_user_roles_analysis(self, roles: List[str]) -> str:
        """格式化用户角色分析"""
        result = []
        for role in roles:
            result.append(f"- **{role}**: 系统的{role}，具有相应的功能权限")
        
        return "\n".join(result) if result else "- **普通用户**: 系统的基本用户\n- **管理员**: 系统管理人员"
    
    def _format_business_flows_analysis(self, flows: List[str]) -> str:
        """格式化业务流程分析"""
        result = []
        for i, flow in enumerate(flows, 1):
            result.append(f"{i}. **{flow}**: 系统核心业务流程之一")
        
        return "\n".join(result) if result else "1. **数据处理流程**: 系统核心业务流程\n2. **用户操作流程**: 用户交互流程"
    
    def _format_modules_for_testing(self, modules: List[Dict[str, Any]]) -> str:
        """格式化模块为测试覆盖分析"""
        if not modules:
            return "- 基础功能模块: 需要进行功能测试和数据测试\n- 用户交互模块: 需要进行界面测试和易用性测试\n- 系统配置模块: 需要进行配置测试和兼容性测试"
        
        result = []
        for module in modules:
            result.append(f"- **{module['name']}**:")
            result.append(f"  - 测试重点: {module['description']}")
            result.append(f"  - 测试复杂度: {module.get('priority', '中')}")
            if module.get('risk'):
                result.append(f"  - 风险等级: 高 {module.get('risk')}")
        
        return "\n".join(result)
    
    def _format_detailed_test_points(self, test_types: List[Dict[str, Any]]) -> str:
        """详细格式化测试点 - 重点突出测试点内容"""
        if not test_types:
            return """### 功能测试
- 基本功能验证
- 异常处理验证  
- 权限验证

### 界面测试
- 界面布局验证
- 交互操作验证
- 显示内容验证"""
        
        result = []
        for test_type in test_types:
            result.append(f"### {test_type['type']} (优先级: {test_type['priority']})")
            result.append(f"**测试目标**: {test_type['description']}")
            result.append("**测试点**:")
            
            test_points = test_type.get('test_points', [])
            for point in test_points:
                result.append(f"- {point}")
            
            result.append("")  # 空行分隔
        
        return "\n".join(result)
    
    def _format_test_types_analysis(self, test_types: List[Dict[str, Any]]) -> str:
        """格式化测试类型分析"""
        if not test_types:
            return "- **功能测试**: 验证系统基本功能\n- **界面测试**: 验证用户界面\n- **数据测试**: 验证数据处理"
        
        result = []
        for test_type in test_types:
            result.append(f"- **{test_type['type']}** (优先级: {test_type['priority']})")
            result.append(f"  - {test_type['description']}")
            if test_type.get('test_points'):
                points = test_type['test_points'][:3]  # 只显示前3个测试点
                for point in points:
                    result.append(f"  - ✓ {point}")
                if len(test_type['test_points']) > 3:
                    result.append(f"  - 共{len(test_type['test_points'])}个测试点...")
        
        return "\n".join(result)
    
    def _format_test_scenarios_analysis(self, scenarios: List[str]) -> str:
        """格式化测试场景分析"""
        if not scenarios:
            return "1. 基本功能场景\n2. 异常处理场景\n3. 边界条件场景"
        
        result = []
        for i, scenario in enumerate(scenarios[:8], 1):  # 最多显示8个场景
            result.append(f"{i}. {scenario}")
        
        if len(scenarios) > 8:
            result.append(f"... 共识别{len(scenarios)}个测试场景")
        
        return "\n".join(result)
    
    def _extract_business_rules(self, text: str) -> str:
        """提取业务规则"""
        rules = []
        
        # 基于文本内容智能生成业务规则
        if "登录" in text:
            rules.append("""
**BR-AUTH-001: 用户登录验证规则**
- 触发条件: 当用户提交登录信息时
- 系统行为: 系统应验证用户名和密码的正确性
- 异常处理: 如果验证失败3次，则锁定账户10分钟
- 业务影响: 影响系统安全性和用户体验
            """)
        
        if "数据" in text:
            rules.append("""
**BR-DATA-001: 数据完整性规则**
- 触发条件: 当用户提交数据时
- 系统行为: 系统应验证数据的完整性和格式正确性
- 异常处理: 如果数据不完整，则提示用户补充必填信息
- 业务影响: 确保数据质量和业务流程正常运行
            """)
        
        return "\n".join(rules) if rules else """
**BR-SYS-001: 系统通用规则**
- 触发条件: 用户执行任何操作时
- 系统行为: 系统应记录操作日志并进行权限验证
- 异常处理: 如果权限不足，则拒绝操作并记录日志
- 业务影响: 确保系统安全性和可追溯性
        """
    
    def _assess_functional_coverage(self, text: str) -> int:
        """评估功能覆盖度"""
        # 基于关键功能点的覆盖情况评估
        key_functions = ["增加", "删除", "修改", "查询", "导入", "导出", "统计", "审核"]
        covered = sum(1 for func in key_functions if func in text)
        return min(95, max(60, (covered / len(key_functions)) * 100))
    
    def _assess_nonfunctional_coverage(self, text: str) -> int:
        """评估非功能需求覆盖度"""
        nf_keywords = ["性能", "安全", "可用性", "兼容", "扩展"]
        covered = sum(1 for keyword in nf_keywords if keyword in text)
        return min(90, max(50, (covered / len(nf_keywords)) * 100))
    
    def _assess_interface_clarity(self, text: str) -> int:
        """评估接口定义清晰度"""
        interface_keywords = ["接口", "API", "参数", "返回", "格式"]
        covered = sum(1 for keyword in interface_keywords if keyword in text)
        return min(85, max(40, (covered / len(interface_keywords)) * 100))
    
    # 测试点获取方法
    def _get_functional_test_points(self, text: str) -> List[str]:
        """获取功能测试点"""
        test_points = []
        
        # 基于具体关键词生成相应的测试点
        if "登录" in text:
            test_points.extend(["正常登录验证", "用户名密码错误验证", "账户锁定验证", "登录状态保持验证"])
        if "注册" in text:
            test_points.extend(["正常注册验证", "重复用户名验证", "密码强度验证", "邮箱格式验证"])
        if "查询" in text or "搜索" in text:
            test_points.extend(["关键词查询验证", "空查询结果验证", "分页查询验证", "排序功能验证"])
        if "添加" in text or "创建" in text:
            test_points.extend(["正常添加验证", "必填字段验证", "数据格式验证", "重复数据验证"])
        if "修改" in text or "编辑" in text:
            test_points.extend(["正常修改验证", "数据一致性验证", "权限控制验证", "修改历史记录验证"])
        if "删除" in text:
            test_points.extend(["正常删除验证", "关联数据验证", "软删除验证", "批量删除验证"])
        if "支付" in text:
            test_points.extend(["正常支付流程验证", "支付失败处理验证", "支付金额验证", "支付方式切换验证"])
        if "订单" in text:
            test_points.extend(["订单创建验证", "订单状态更新验证", "订单取消验证", "订单查询验证"])
        if "用户" in text or "权限" in text:
            test_points.extend(["用户权限验证", "角色权限验证", "操作权限验证", "数据权限验证"])
        if "上传" in text or "文件" in text:
            test_points.extend(["文件上传验证", "文件格式验证", "文件大小限制验证", "文件下载验证"])
        if "导入" in text or "导出" in text:
            test_points.extend(["数据导入验证", "数据导出验证", "格式转换验证", "批量处理验证"])
        if "报表" in text or "统计" in text:
            test_points.extend(["报表生成验证", "数据统计验证", "报表筛选验证", "报表导出验证"])
        
        # 如果没有匹配到特定关键词，根据文本内容生成通用测试点
        if not test_points:
            # 分析文本中的动词，生成相应测试点
            if any(word in text for word in ["功能", "系统", "平台", "应用"]):
                test_points = ["核心功能验证", "业务流程验证", "用户操作验证", "系统响应验证"]
            elif any(word in text for word in ["管理", "维护", "配置"]):
                test_points = ["管理功能验证", "数据维护验证", "配置设置验证", "状态管理验证"]
            elif any(word in text for word in ["处理", "操作", "执行"]):
                test_points = ["处理流程验证", "操作响应验证", "执行结果验证", "异常处理验证"]
            else:
                test_points = ["基本功能验证", "业务逻辑验证", "异常处理验证", "边界条件验证"]
        
        return test_points
    
    def _get_ui_test_points(self, text: str) -> List[str]:
        """获取界面测试点"""
        test_points = []
        
        # 基础界面测试点
        base_points = [
            "页面布局正确性验证",
            "按钮链接可用性验证", 
            "文字内容正确性验证"
        ]
        test_points.extend(base_points)
        
        # 根据需求内容添加特定界面测试点
        if "表单" in text:
            test_points.extend(["表单验证提示", "表单提交反馈", "表单重置功能", "必填字段标识"])
        if "表格" in text or "列表" in text:
            test_points.extend(["表格排序功能", "表格分页功能", "表格筛选功能", "数据展示格式"])
        if "登录" in text:
            test_points.extend(["登录页面布局", "密码输入隐藏", "登录按钮状态", "错误提示显示"])
        if "支付" in text:
            test_points.extend(["支付页面布局", "支付方式选择", "金额显示格式", "支付结果反馈"])
        if "移动" in text or "手机" in text:
            test_points.extend(["移动端适配", "触摸操作响应", "屏幕尺寸适配"])
        if "搜索" in text or "查询" in text:
            test_points.extend(["搜索框设计", "搜索结果展示", "搜索历史提示"])
        
        return test_points
    
    def _get_performance_test_points(self, text: str) -> List[str]:
        """获取性能测试点"""
        test_points = [
            "页面加载时间测试",
            "接口响应时间测试"
        ]
        
        # 根据需求内容添加特定性能测试点
        if "并发" in text or "大量" in text:
            test_points.extend(["并发用户访问测试", "高并发场景测试", "系统资源占用测试"])
        if "数据库" in text or "查询" in text:
            test_points.extend(["数据库查询性能测试", "复杂查询优化测试"])
        if "文件" in text or "上传" in text:
            test_points.extend(["文件上传性能测试", "文件下载性能测试", "大文件处理测试"])
        if "支付" in text:
            test_points.extend(["支付接口响应测试", "支付并发处理测试", "支付超时处理测试"])
        if "批量" in text:
            test_points.extend(["批量数据处理测试", "批量操作性能测试"])
        if "报表" in text or "统计" in text:
            test_points.extend(["报表生成性能测试", "数据统计计算测试"])
        
        # 如果没有特定场景，添加通用性能测试点
        if len(test_points) == 2:  # 只有基础的两个测试点
            test_points.extend(["系统响应时间测试", "内存使用率测试", "CPU使用率测试"])
        
        return test_points
    
    def _get_security_test_points(self, text: str) -> List[str]:
        """获取安全测试点"""
        test_points = []
        
        # 基础安全测试点
        base_security_points = [
            "SQL注入攻击测试",
            "XSS跨站脚本测试"
        ]
        test_points.extend(base_security_points)
        
        # 根据需求内容添加特定安全测试点
        if "登录" in text or "认证" in text:
            test_points.extend(["暴力破解攻击测试", "会话劫持测试", "身份认证绕过测试", "密码策略测试"])
        if "权限" in text:
            test_points.extend(["权限提升测试", "越权访问测试", "角色权限验证", "数据权限控制测试"])
        if "支付" in text:
            test_points.extend(["支付数据加密测试", "交易完整性测试", "支付接口安全测试", "金融数据保护测试"])
        if "文件" in text or "上传" in text:
            test_points.extend(["恶意文件上传测试", "文件包含漏洞测试", "文件下载安全测试"])
        if "数据" in text:
            test_points.extend(["敏感数据泄露测试", "数据传输加密测试", "数据存储安全测试"])
        if "接口" in text or "API" in text:
            test_points.extend(["API接口安全测试", "接口鉴权测试", "接口参数验证测试"])
        
        # 通用安全测试点
        test_points.extend(["CSRF跨站请求伪造测试", "安全日志记录测试"])
        
        return test_points
    
    def _get_data_test_points(self, text: str) -> List[str]:
        """获取数据测试点"""
        test_points = [
            "数据完整性验证",
            "数据一致性验证"
        ]
        
        # 根据需求内容添加特定数据测试点
        if "导入" in text:
            test_points.extend(["数据导入格式测试", "大批量导入测试", "导入错误处理测试", "数据去重测试"])
        if "导出" in text:
            test_points.extend(["数据导出完整性测试", "导出格式正确性测试", "导出权限控制测试"])
        if "统计" in text or "报表" in text:
            test_points.extend(["统计数据准确性测试", "报表数据一致性测试", "数据聚合计算测试"])
        if "支付" in text or "订单" in text:
            test_points.extend(["交易数据准确性测试", "订单状态一致性测试", "金额计算准确性测试"])
        if "用户" in text:
            test_points.extend(["用户数据隐私测试", "用户信息完整性测试", "用户操作日志测试"])
        if "备份" in text or "恢复" in text:
            test_points.extend(["数据备份完整性测试", "数据恢复准确性测试", "增量备份测试"])
        
        # 通用数据测试点
        test_points.extend(["数据格式验证", "数据边界值测试"])
        
        return test_points
    
    def _get_compatibility_test_points(self, text: str) -> List[str]:
        """获取兼容性测试点"""
        test_points = [
            "Chrome浏览器兼容性测试",
            "Firefox浏览器兼容性测试",
            "Safari浏览器兼容性测试",
            "Edge浏览器兼容性测试",
            "移动端浏览器兼容性测试",
            "不同屏幕分辨率测试"
        ]
        
        if "移动" in text or "手机" in text:
            test_points.extend(["Android设备兼容性测试", "iOS设备兼容性测试"])
        
        return test_points
    
    # 测试相关评估方法
    def _identify_high_risk_test_points(self, text: str) -> str:
        """识别高风险测试点"""
        risk_points = []
        
        if "支付" in text or "金钱" in text:
            risk_points.append("- **支付功能测试**: 涉及资金安全，需要重点测试")
        if "权限" in text:
            risk_points.append("- **权限控制测试**: 可能导致越权访问，需要重点测试")
        if "数据" in text and "删除" in text:
            risk_points.append("- **数据删除测试**: 可能导致数据丢失，需要重点测试")
        if "第三方" in text or "集成" in text:
            risk_points.append("- **第三方集成测试**: 依赖外部系统，风险较高")
        
        return "\n".join(risk_points) if risk_points else "- **数据一致性测试**: 需要重点关注数据准确性\n- **权限验证测试**: 需要重点关注访问控制"
    
    def _assess_functional_complexity(self, text: str) -> str:
        """评估功能复杂度"""
        complexity_score = 0
        
        if "登录" in text: complexity_score += 1
        if "权限" in text: complexity_score += 2
        if "支付" in text: complexity_score += 3
        if "报表" in text: complexity_score += 2
        if "集成" in text: complexity_score += 3
        
        if complexity_score >= 8:
            return "高 - 功能复杂，需要充分测试"
        elif complexity_score >= 4:
            return "中 - 功能适中，需要全面测试"
        else:
            return "低 - 功能简单，基础测试覆盖"
    
    def _assess_data_complexity(self, text: str) -> str:
        """评估数据复杂度"""
        if "大量" in text or "批量" in text:
            return "高 - 涉及大量数据处理"
        elif "报表" in text or "统计" in text:
            return "中 - 涉及数据计算和统计"
        else:
            return "低 - 基本数据操作"
    
    def _assess_integration_complexity(self, text: str) -> str:
        """评估集成复杂度"""
        if "第三方" in text or "API" in text:
            return "高 - 涉及外部系统集成"
        elif "数据库" in text:
            return "中 - 涉及数据库集成"
        else:
            return "低 - 内部系统集成"
    
    def _assess_functional_test_coverage(self, text: str) -> int:
        """评估功能测试覆盖度"""
        key_functions = ["登录", "查询", "添加", "修改", "删除", "权限", "验证", "处理"]
        covered = sum(1 for func in key_functions if func in text)
        return min(95, max(70, (covered / len(key_functions)) * 100))
    
    def _assess_scenario_test_coverage(self, text: str) -> int:
        """评估场景测试覆盖度"""
        scenarios = ["正常", "异常", "边界", "性能", "安全", "兼容"]
        # 基于文本复杂度估算场景覆盖度
        word_count = len(text.split())
        base_coverage = min(90, max(60, word_count // 5))
        return base_coverage
    
    def _assess_data_test_coverage(self, text: str) -> int:
        """评估数据测试覆盖度"""
        data_keywords = ["数据", "信息", "录入", "导入", "导出", "统计", "报表"]
        covered = sum(1 for keyword in data_keywords if keyword in text)
        return min(85, max(65, (covered / len(data_keywords)) * 100))
    
    async def _extract_structured_requirements(self, analysis_report: str, original_text: str) -> Dict[str, Any]:
        """提取结构化需求"""
        await asyncio.sleep(0.5)  # 模拟处理时间
        
        # 基于分析报告和原始文本生成结构化需求
        requirements = []
        
        # 从文本中智能提取需求
        requirements_data = self._intelligent_requirement_extraction(original_text)
        
        return {"requirements": requirements_data}
    
    def _intelligent_requirement_extraction(self, text: str) -> List[Dict[str, Any]]:
        """智能测试需求提取 - 基于业务需求生成测试类型和测试点"""
        test_requirements = []
        req_counter = 1
        
        # 识别测试类型
        test_types = self._identify_test_types(text)
        
        # 为每个测试类型生成测试需求，避免重复
        for test_type in test_types:
            test_points = test_type.get('test_points', [])
            
            # 为每个测试点创建独立的测试需求，确保每个需求都不同
            for i, test_point in enumerate(test_points, 1):
                # 生成唯一的需求ID和名称
                unique_requirement_name = f"{test_point}"
                
                # 检查是否已有相同的需求名称，避免重复
                existing_names = [req['requirement_name'] for req in test_requirements]
                if unique_requirement_name in existing_names:
                    unique_requirement_name = f"{test_type['type']} - {test_point} ({i})"
                
                test_requirements.append({
                    "requirement_id": f"TEST{req_counter:03d}",
                    "requirement_name": unique_requirement_name,
                    "requirement_type": test_type['type'],
                    "parent_requirement": None,
                    "module": f"{test_type['type']}模块",
                    "requirement_level": test_type['priority'],
                    "reviewer": "测试工程师",
                    "estimated_hours": self._estimate_test_hours(test_type['type'], test_point),
                    "description": self._generate_test_description(test_type['type'], test_point, text),
                    "acceptance_criteria": self._generate_test_acceptance_criteria(test_type['type'], test_point)
                })
                req_counter += 1
        
        # 如果没有识别出特定的测试类型，生成默认的测试需求
        if not test_requirements:
            test_requirements = [
                {
                    "requirement_id": "TEST001",
                    "requirement_name": "功能测试 - 基本功能验证",
                    "requirement_type": "功能测试",
                    "parent_requirement": None,
                    "module": "功能测试模块",
                    "requirement_level": "高",
                    "reviewer": "测试工程师",
                    "estimated_hours": 8,
                    "description": "验证系统基本功能是否按预期工作，包括正常流程和异常处理。",
                    "acceptance_criteria": "1. 所有基本功能正常执行\n2. 异常情况得到正确处理\n3. 用户操作有明确反馈\n4. 功能响应时间在可接受范围内"
                },
                {
                    "requirement_id": "TEST002",
                    "requirement_name": "界面测试 - 用户界面验证",
                    "requirement_type": "界面测试",
                    "parent_requirement": None,
                    "module": "界面测试模块",
                    "requirement_level": "中",
                    "reviewer": "测试工程师",
                    "estimated_hours": 6,
                    "description": "验证用户界面的正确性、一致性和易用性，确保良好的用户体验。",
                    "acceptance_criteria": "1. 界面布局正确显示\n2. 交互元素功能正常\n3. 页面响应式适配良好\n4. 文字内容准确无误"
                },
                {
                    "requirement_id": "TEST003",
                    "requirement_name": "数据测试 - 数据完整性验证",
                    "requirement_type": "数据测试",
                    "parent_requirement": None,
                    "module": "数据测试模块",
                    "requirement_level": "高",
                    "reviewer": "测试工程师",
                    "estimated_hours": 10,
                    "description": "验证数据处理的准确性、完整性和一致性，确保数据质量。",
                    "acceptance_criteria": "1. 数据输入验证正确\n2. 数据存储完整准确\n3. 数据查询结果一致\n4. 数据备份恢复正常"
                }
            ]
        
        return test_requirements
    
    def _estimate_test_hours(self, test_type: str, test_point: str) -> int:
        """估算测试工时"""
        base_hours = {
            "功能测试": 8,
            "界面测试": 6,
            "性能测试": 12,
            "安全测试": 16,
            "数据测试": 10,
            "兼容性测试": 8
        }
        
        base = base_hours.get(test_type, 8)
        
        # 根据测试点复杂度调整工时
        if "复杂" in test_point or "集成" in test_point:
            return base + 4
        elif "简单" in test_point or "基本" in test_point:
            return max(4, base - 2)
        else:
            return base
    
    def _generate_test_description(self, test_type: str, test_point: str, original_text: str) -> str:
        """生成测试描述"""
        descriptions = {
            "功能测试": f"对{test_point}进行全面的功能性验证测试，确保功能按业务需求正确实现。",
            "界面测试": f"对{test_point}进行用户界面测试，验证界面的正确性和用户体验。",
            "性能测试": f"对{test_point}进行性能测试，验证系统在各种负载条件下的性能表现。",
            "安全测试": f"对{test_point}进行安全性测试，识别和验证潜在的安全风险点。",
            "数据测试": f"对{test_point}进行数据测试，验证数据处理的准确性和完整性。",
            "兼容性测试": f"对{test_point}进行兼容性测试，验证在不同环境下的兼容性。"
        }
        
        base_desc = descriptions.get(test_type, f"对{test_point}进行测试验证。")
        
        # 根据原始文本添加更多上下文
        if "电商" in original_text or "商城" in original_text:
            base_desc += " 特别关注电商业务场景下的测试覆盖。"
        elif "管理系统" in original_text:
            base_desc += " 重点验证管理系统的权限控制和数据安全。"
        
        return base_desc
    
    def _generate_test_acceptance_criteria(self, test_type: str, test_point: str) -> str:
        """生成测试验收标准"""
        criteria_templates = {
            "功能测试": [
                "功能按预期正常工作",
                "异常情况得到正确处理",
                "边界条件测试通过",
                "用户操作有明确反馈"
            ],
            "界面测试": [
                "界面布局符合设计规范",
                "交互元素响应正常",
                "页面在不同分辨率下正常显示",
                "文字内容准确完整"
            ],
            "性能测试": [
                "响应时间满足性能要求",
                "系统能承受预期负载",
                "资源使用率在合理范围内",
                "并发访问稳定可靠"
            ],
            "安全测试": [
                "安全漏洞测试通过",
                "权限控制验证有效",
                "敏感数据保护到位",
                "安全日志记录完整"
            ],
            "数据测试": [
                "数据输入验证正确",
                "数据存储完整准确",
                "数据查询结果一致",
                "数据完整性得到保证"
            ],
            "兼容性测试": [
                "主流浏览器兼容性良好",
                "不同操作系统下运行正常",
                "移动设备适配正确",
                "向后兼容性满足要求"
            ]
        }
        
        criteria = criteria_templates.get(test_type, [
            "测试目标达成",
            "测试结果符合预期",
            "无阻塞性问题",
            "文档记录完整"
        ])
        
        return "\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(criteria)])
    
    async def _assess_requirement_quality(self, structured_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """评估需求质量"""
        await asyncio.sleep(0.3)
        
        requirements = structured_requirements.get("requirements", [])
        total_reqs = len(requirements)
        
        if total_reqs == 0:
            return {"overall_score": 0, "assessment_details": "没有找到需求"}
        
        # 质量评估指标
        completeness_score = min(100, (total_reqs / 5) * 100)  # 需求完整性
        clarity_score = 85  # 需求清晰度
        testability_score = 80  # 可测试性
        
        overall_score = (completeness_score + clarity_score + testability_score) / 3
        
        return {
            "overall_score": round(overall_score, 1),
            "completeness_score": round(completeness_score, 1),
            "clarity_score": clarity_score,
            "testability_score": testability_score,
            "total_requirements": total_reqs,
            "assessment_details": f"共识别{total_reqs}个需求，质量评估得分{overall_score:.1f}分"
        }
    
    async def _analyze_risks(self, structured_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """风险分析"""
        await asyncio.sleep(0.2)
        
        requirements = structured_requirements.get("requirements", [])
        
        high_risks = []
        medium_risks = []
        low_risks = []
        
        # 基于需求特征分析风险
        for req in requirements:
            req_name = req.get("requirement_name", "")
            req_type = req.get("requirement_type", "")
            
            if "第三方" in req_name or "集成" in req_name:
                high_risks.append(f"{req_name}: 外部依赖风险")
            elif req_type == "性能需求":
                medium_risks.append(f"{req_name}: 性能达标风险")
            else:
                low_risks.append(f"{req_name}: 常规实现风险")
        
        # 如果没有具体风险，生成通用风险评估
        if not (high_risks or medium_risks or low_risks):
            medium_risks = ["技术实现复杂度风险", "需求变更风险"]
            low_risks = ["进度延期风险", "资源配置风险"]
        
        return {
            "high_risks": high_risks,
            "medium_risks": medium_risks, 
            "low_risks": low_risks,
            "total_risks": len(high_risks) + len(medium_risks) + len(low_risks)
        }
    
    async def _generate_final_report(self, analysis_report: str, quality_assessment: Dict, risk_analysis: Dict) -> str:
        """生成最终报告 - 简化版，重点突出测试点"""
        final_report = f"""{analysis_report}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*分析引擎版本: Advanced Test Requirement Analyzer v2.0*
        """
        
        return final_report


# 全局实例
advanced_analyzer = AdvancedTestRequirementAnalyzer()