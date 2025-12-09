"""
Report generator for audit results.

Generates:
- Markdown reports for human reading
- JSON reports for machine processing
- Recommendations based on issue patterns
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from ..core.models import Issue, TestResult, AuditReport, Severity, Category


class ReportGenerator:
    """Генератор отчётов аудита."""
    
    def __init__(self, output_dir: Path = None):
        """
        Args:
            output_dir: Директория для сохранения отчётов (по умолчанию audit_reports/)
        """
        self.output_dir = output_dir or Path("audit_reports")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(
        self,
        test_results: List[TestResult],
        duration_seconds: float,
        format: str = "markdown"
    ) -> str:
        """
        Генерация отчёта.
        
        Args:
            test_results: Результаты тестов
            duration_seconds: Длительность аудита
            format: Формат отчёта ("markdown" или "json")
        
        Returns:
            Путь к сгенерированному файлу
        """
        # Collect all issues
        all_issues = []
        for result in test_results:
            all_issues.extend(result.issues)
        
        # Create audit report
        audit_report = self._create_audit_report(
            test_results=test_results,
            all_issues=all_issues,
            duration_seconds=duration_seconds
        )
        
        # Generate report based on format
        if format == "json":
            return self.generate_json_report(audit_report)
        else:
            return self.generate_markdown_report(audit_report)
    
    def generate_markdown_report(self, audit_report: AuditReport) -> str:
        """
        Генерация Markdown отчёта.
        
        Args:
            audit_report: Данные аудита
        
        Returns:
            Путь к файлу отчёта
        """
        # Generate filename
        timestamp_str = audit_report.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"audit_report_{timestamp_str}.md"
        filepath = self.output_dir / filename
        
        # Build report content
        lines = []
        
        # Header
        lines.append("# Fractal Memory Project Audit Report")
        lines.append("")
        lines.append(f"**Date:** {audit_report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Total Issues:** {audit_report.total_issues}")
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        
        for severity in ["critical", "high", "medium", "low"]:
            count = audit_report.issues_by_severity.get(severity, 0)
            emoji = severity_emoji.get(severity, "")
            lines.append(f"- {emoji} **{severity.capitalize()}:** {count}")
        
        lines.append("")
        
        # Issues by Category
        lines.append("## Issues by Category")
        for category, count in sorted(audit_report.issues_by_category.items(), key=lambda x: -x[1]):
            lines.append(f"- **{category}:** {count}")
        lines.append("")
        
        # Test Results Summary
        lines.append("## Test Results")
        lines.append("")
        
        for result in audit_report.test_results:
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            lines.append(f"### {result.test_name} - {status}")
            lines.append(f"Duration: {result.duration_ms:.2f}ms")
            lines.append(f"Issues: {len(result.issues)}")
            lines.append("")
        
        # Critical Issues
        critical_issues = audit_report.get_critical_issues()
        if critical_issues:
            lines.append("## 🔴 Critical Issues")
            lines.append("")
            for issue in critical_issues[:10]:  # Limit to 10
                lines.append(issue.to_markdown())
                lines.append("")
        
        # High Priority Issues
        high_issues = audit_report.get_high_issues()
        if high_issues:
            lines.append("## 🟠 High Priority Issues")
            lines.append("")
            # Show first 10, mention if there are more
            for issue in high_issues[:10]:
                lines.append(issue.to_markdown())
                lines.append("")
            
            if len(high_issues) > 10:
                lines.append(f"*... and {len(high_issues) - 10} more high priority issues*")
                lines.append("")
        
        # Recommendations
        recommendations = self.generate_recommendations(audit_report.all_issues)
        if recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. **{rec['title']}**")
                lines.append(f"   - {rec['description']}")
                lines.append(f"   - Priority: {rec['priority']}")
                lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Report generated in {audit_report.duration_seconds:.2f} seconds*")
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return str(filepath)
    
    def generate_json_report(self, audit_report: AuditReport) -> str:
        """
        Генерация JSON отчёта.
        
        Args:
            audit_report: Данные аудита
        
        Returns:
            Путь к файлу отчёта
        """
        # Generate filename
        timestamp_str = audit_report.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"audit_report_{timestamp_str}.json"
        filepath = self.output_dir / filename
        
        # Convert to dict
        report_dict = audit_report.to_dict()
        
        # Add recommendations
        report_dict['recommendations'] = self.generate_recommendations(audit_report.all_issues)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_recommendations(self, issues: List[Issue]) -> List[Dict[str, Any]]:
        """
        Генерация рекомендаций на основе паттернов проблем.
        
        Args:
            issues: Список проблем
        
        Returns:
            Список рекомендаций
        """
        recommendations = []
        
        # Group issues by category
        issues_by_category = defaultdict(list)
        for issue in issues:
            issues_by_category[issue.category].append(issue)
        
        # Analyze patterns and generate recommendations
        
        # 1. Import issues
        if Category.IMPORTS in issues_by_category:
            import_issues = issues_by_category[Category.IMPORTS]
            critical_imports = [i for i in import_issues if i.severity == Severity.CRITICAL]
            
            if critical_imports:
                recommendations.append({
                    'title': 'Fix critical import errors',
                    'description': f'Found {len(critical_imports)} critical import errors that prevent code from running',
                    'priority': 'critical',
                    'affected_issues': len(critical_imports),
                    'action': 'Review and fix all import statements, ensure modules exist',
                })
        
        # 2. Schema issues
        if Category.SCHEMA in issues_by_category:
            schema_issues = issues_by_category[Category.SCHEMA]
            field_issues = [i for i in schema_issues if 'field' in i.description.lower()]
            
            if field_issues:
                recommendations.append({
                    'title': 'Update code to match Neo4j schema',
                    'description': f'Found {len(field_issues)} issues with non-existent fields in Neo4j',
                    'priority': 'high',
                    'affected_issues': len(field_issues),
                    'action': 'Update Cypher queries to use actual schema fields',
                })
        
        # 3. API issues
        if Category.API in issues_by_category:
            api_issues = issues_by_category[Category.API]
            
            if api_issues:
                recommendations.append({
                    'title': 'Ensure API consistency',
                    'description': f'Found {len(api_issues)} API compatibility issues',
                    'priority': 'high',
                    'affected_issues': len(api_issues),
                    'action': 'Standardize data structures and API contracts between components',
                })
        
        # 4. Memory issues
        if Category.MEMORY in issues_by_category:
            memory_issues = issues_by_category[Category.MEMORY]
            consolidation_issues = [i for i in memory_issues if 'consolidation' in i.description.lower()]
            
            if consolidation_issues:
                recommendations.append({
                    'title': 'Fix memory consolidation logic',
                    'description': f'Found {len(consolidation_issues)} issues with memory consolidation',
                    'priority': 'high',
                    'affected_issues': len(consolidation_issues),
                    'action': 'Review and fix L0→L1→L2→L3 consolidation logic',
                })
        
        # 5. Config issues
        if Category.CONFIG in issues_by_category:
            config_issues = issues_by_category[Category.CONFIG]
            critical_config = [i for i in config_issues if i.severity == Severity.CRITICAL]
            
            if critical_config:
                recommendations.append({
                    'title': 'Fix critical configuration issues',
                    'description': f'Found {len(critical_config)} critical configuration problems',
                    'priority': 'critical',
                    'affected_issues': len(critical_config),
                    'action': 'Set up .env file with all required variables',
                })
        
        # 6. Frontend issues
        if Category.FRONTEND in issues_by_category:
            frontend_issues = issues_by_category[Category.FRONTEND]
            cors_issues = [i for i in frontend_issues if 'cors' in i.description.lower()]
            
            if cors_issues:
                recommendations.append({
                    'title': 'Configure CORS properly',
                    'description': f'Found {len(cors_issues)} CORS configuration issues',
                    'priority': 'high',
                    'affected_issues': len(cors_issues),
                    'action': 'Set up CORS middleware in backend to allow frontend origin',
                })
        
        # 7. Integration issues
        if Category.INTEGRATION in issues_by_category:
            integration_issues = issues_by_category[Category.INTEGRATION]
            
            if integration_issues:
                recommendations.append({
                    'title': 'Fix integration issues',
                    'description': f'Found {len(integration_issues)} integration problems',
                    'priority': 'high',
                    'affected_issues': len(integration_issues),
                    'action': 'Ensure all components work together correctly',
                })
        
        # 8. General recommendation based on total issues
        if len(issues) > 100:
            recommendations.append({
                'title': 'Prioritize critical and high severity issues',
                'description': f'Total of {len(issues)} issues found - focus on critical and high priority first',
                'priority': 'medium',
                'affected_issues': len(issues),
                'action': 'Create a plan to address issues by severity, starting with critical',
            })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 99))
        
        return recommendations
    
    def _create_audit_report(
        self,
        test_results: List[TestResult],
        all_issues: List[Issue],
        duration_seconds: float
    ) -> AuditReport:
        """Создать объект AuditReport."""
        
        # Count issues by severity
        issues_by_severity = defaultdict(int)
        for issue in all_issues:
            issues_by_severity[issue.severity.value] += 1
        
        # Count issues by category
        issues_by_category = defaultdict(int)
        for issue in all_issues:
            issues_by_category[issue.category.value] += 1
        
        return AuditReport(
            timestamp=datetime.now(),
            total_issues=len(all_issues),
            issues_by_severity=dict(issues_by_severity),
            issues_by_category=dict(issues_by_category),
            test_results=test_results,
            all_issues=all_issues,
            duration_seconds=duration_seconds,
        )
    
    def print_summary(self, audit_report: AuditReport):
        """Вывести краткую сводку в консоль."""
        
        print("\n" + "="*60)
        print("AUDIT SUMMARY")
        print("="*60)
        print(f"\nTotal Issues: {audit_report.total_issues}")
        print(f"Duration: {audit_report.duration_seconds:.2f}s")
        print("\nBy Severity:")
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        
        for severity in ["critical", "high", "medium", "low"]:
            count = audit_report.issues_by_severity.get(severity, 0)
            emoji = severity_emoji.get(severity, "")
            print(f"  {emoji} {severity.capitalize()}: {count}")
        
        print("\nBy Category:")
        for category, count in sorted(audit_report.issues_by_category.items(), key=lambda x: -x[1])[:5]:
            print(f"  - {category}: {count}")
        
        print("\nTest Results:")
        passed = sum(1 for r in audit_report.test_results if r.passed)
        failed = len(audit_report.test_results) - passed
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        
        print("\n" + "="*60)
