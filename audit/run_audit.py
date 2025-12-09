"""
Скрипт для запуска полного аудита проекта.

Запускает все checkers и testers, собирает результаты.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")

from audit.config import AuditConfig
from audit.checkers.import_checker import ImportChecker
from audit.checkers.schema_validator import SchemaValidator
from audit.checkers.api_validator import APIValidator
from audit.testers.memory_tester import MemoryTester
from audit.testers.retrieval_tester import RetrievalTester
from audit.testers.learning_tester import LearningTester
from audit.core.models import AuditReport, Severity

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_static_analysis(config: AuditConfig):
    """Запустить статический анализ."""
    logger.info("=" * 60)
    logger.info("PHASE 1: STATIC ANALYSIS")
    logger.info("=" * 60)
    
    results = []
    
    # Import Checker
    logger.info("\n[1/3] Running ImportChecker...")
    import_checker = ImportChecker(config)
    result = await import_checker.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    # Schema Validator
    logger.info("\n[2/3] Running SchemaValidator...")
    schema_validator = SchemaValidator(config)
    result = await schema_validator.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    # API Validator
    logger.info("\n[3/3] Running APIValidator...")
    api_validator = APIValidator(config)
    result = await api_validator.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    return results


async def run_runtime_tests(config: AuditConfig):
    """Запустить runtime тесты."""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: RUNTIME TESTS")
    logger.info("=" * 60)
    
    results = []
    
    # Memory Tester
    logger.info("\n[1/3] Running MemoryTester...")
    memory_tester = MemoryTester(config)
    result = await memory_tester.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    # Retrieval Tester
    logger.info("\n[2/3] Running RetrievalTester...")
    retrieval_tester = RetrievalTester(config)
    result = await retrieval_tester.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    # Learning Tester
    logger.info("\n[3/3] Running LearningTester...")
    learning_tester = LearningTester(config)
    result = await learning_tester.run()
    results.append(result)
    logger.info(f"  Found {len(result.issues)} issues")
    
    return results


def generate_report(test_results, output_file: Path):
    """Сгенерировать отчет."""
    # Collect all issues
    all_issues = []
    for result in test_results:
        all_issues.extend(result.issues)
    
    # Count by severity
    issues_by_severity = {
        "critical": len([i for i in all_issues if i.severity == Severity.CRITICAL]),
        "high": len([i for i in all_issues if i.severity == Severity.HIGH]),
        "medium": len([i for i in all_issues if i.severity == Severity.MEDIUM]),
        "low": len([i for i in all_issues if i.severity == Severity.LOW]),
    }
    
    # Count by category
    issues_by_category = {}
    for issue in all_issues:
        cat = issue.category.value
        issues_by_category[cat] = issues_by_category.get(cat, 0) + 1
    
    # Generate markdown report
    report = []
    report.append("# Fractal Memory Project Audit Report")
    report.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n## Executive Summary")
    report.append(f"\n- **Total Issues:** {len(all_issues)}")
    report.append(f"- 🔴 **Critical:** {issues_by_severity['critical']}")
    report.append(f"- 🟠 **High:** {issues_by_severity['high']}")
    report.append(f"- 🟡 **Medium:** {issues_by_severity['medium']}")
    report.append(f"- 🟢 **Low:** {issues_by_severity['low']}")
    
    report.append(f"\n## Issues by Category")
    for cat, count in sorted(issues_by_category.items(), key=lambda x: -x[1]):
        report.append(f"- **{cat}:** {count}")
    
    report.append(f"\n## Test Results")
    for result in test_results:
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        report.append(f"\n### {result.test_name} - {status}")
        report.append(f"Duration: {result.duration_ms:.2f}ms")
        report.append(f"Issues: {len(result.issues)}")
    
    # Critical issues
    critical_issues = [i for i in all_issues if i.severity == Severity.CRITICAL]
    if critical_issues:
        report.append(f"\n## 🔴 Critical Issues")
        for issue in critical_issues:
            report.append(f"\n{issue.to_markdown()}")
    
    # High issues
    high_issues = [i for i in all_issues if i.severity == Severity.HIGH]
    if high_issues:
        report.append(f"\n## 🟠 High Priority Issues")
        for issue in high_issues[:10]:  # First 10
            report.append(f"\n{issue.to_markdown()}")
        if len(high_issues) > 10:
            report.append(f"\n*... and {len(high_issues) - 10} more high priority issues*")
    
    # Write report
    report_text = '\n'.join(report)
    output_file.write_text(report_text, encoding='utf-8')
    
    return report_text


async def main():
    """Главная функция."""
    logger.info("Starting Fractal Memory Project Audit")
    logger.info("=" * 60)
    
    # Load config
    config = AuditConfig()
    
    # Check credentials
    if not config.has_neo4j_credentials():
        logger.warning("⚠️  No Neo4j credentials found!")
        logger.warning("   Some tests will be skipped.")
        logger.warning("   Set NEO4J_PASSWORD environment variable.")
    
    start_time = datetime.now()
    
    # Run static analysis
    static_results = await run_static_analysis(config)
    
    # Run runtime tests (if credentials available)
    if config.has_neo4j_credentials():
        runtime_results = await run_runtime_tests(config)
    else:
        logger.warning("\n⚠️  Skipping runtime tests (no database credentials)")
        runtime_results = []
    
    # Combine results
    all_results = static_results + runtime_results
    
    # Generate report
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING REPORT")
    logger.info("=" * 60)
    
    output_file = config.report_output_dir / f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_text = generate_report(all_results, output_file)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"\n✅ Audit complete!")
    logger.info(f"   Duration: {duration:.2f}s")
    logger.info(f"   Report: {output_file}")
    
    # Print summary
    all_issues = []
    for result in all_results:
        all_issues.extend(result.issues)
    
    critical = len([i for i in all_issues if i.severity == Severity.CRITICAL])
    high = len([i for i in all_issues if i.severity == Severity.HIGH])
    medium = len([i for i in all_issues if i.severity == Severity.MEDIUM])
    low = len([i for i in all_issues if i.severity == Severity.LOW])
    
    logger.info(f"\n📊 Summary:")
    logger.info(f"   Total issues: {len(all_issues)}")
    logger.info(f"   🔴 Critical: {critical}")
    logger.info(f"   🟠 High: {high}")
    logger.info(f"   🟡 Medium: {medium}")
    logger.info(f"   🟢 Low: {low}")
    
    if critical > 0:
        logger.warning(f"\n⚠️  {critical} CRITICAL issues found! Fix immediately!")
    elif high > 0:
        logger.warning(f"\n⚠️  {high} HIGH priority issues found!")
    else:
        logger.info(f"\n✅ No critical or high priority issues!")


if __name__ == "__main__":
    asyncio.run(main())
