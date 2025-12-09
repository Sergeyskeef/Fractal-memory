"""
CLI interface for Fractal Memory Project Audit.

Usage:
    python -m audit.main --full                    # Full audit
    python -m audit.main --static-only             # Static analysis only
    python -m audit.main --runtime-only            # Runtime tests only
    python -m audit.main --output-format json      # JSON output
    python -m audit.main --output-file report.md   # Custom output file
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from audit.config import AuditConfig
from audit.checkers.import_checker import ImportChecker
from audit.checkers.schema_validator import SchemaValidator
from audit.checkers.api_validator import APIValidator
from audit.checkers.frontend_validator import FrontendValidator
from audit.checkers.config_validator import ConfigValidator
from audit.testers.memory_tester import MemoryTester
from audit.testers.retrieval_tester import RetrievalTester
from audit.testers.learning_tester import LearningTester
from audit.testers.e2e_validator import E2EFlowValidator
from audit.reports.generator import ReportGenerator
from audit.core.models import TestResult


# Setup logging
def setup_logging(verbose: bool = False):
    """Настроить логирование."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


logger = logging.getLogger(__name__)


async def run_static_analysis(config: AuditConfig) -> List[TestResult]:
    """
    Запустить статический анализ.
    
    Returns:
        Список результатов тестов
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: STATIC ANALYSIS")
    logger.info("=" * 60)
    
    results = []
    
    checkers = [
        ImportChecker(config),
        SchemaValidator(config),
        APIValidator(config),
        FrontendValidator(config),
        ConfigValidator(config),
    ]
    
    for i, checker in enumerate(checkers, 1):
        logger.info(f"\n[{i}/{len(checkers)}] Running {checker.name}...")
        result = await checker.run()
        results.append(result)
        
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        logger.info(f"  {status} - Found {len(result.issues)} issues")
    
    return results


async def run_runtime_tests(config: AuditConfig) -> List[TestResult]:
    """
    Запустить runtime тесты.
    
    Returns:
        Список результатов тестов
    """
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: RUNTIME TESTS")
    logger.info("=" * 60)
    
    results = []
    
    testers = [
        MemoryTester(config),
        RetrievalTester(config),
        LearningTester(config),
    ]
    
    for i, tester in enumerate(testers, 1):
        logger.info(f"\n[{i}/{len(testers)}] Running {tester.name}...")
        result = await tester.run()
        results.append(result)
        
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        logger.info(f"  {status} - Found {len(result.issues)} issues")
    
    return results


async def run_integration_tests(config: AuditConfig) -> List[TestResult]:
    """
    Запустить интеграционные тесты.
    
    Returns:
        Список результатов тестов
    """
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3: INTEGRATION TESTS")
    logger.info("=" * 60)
    
    results = []
    
    testers = [
        E2EFlowValidator(config),
    ]
    
    for i, tester in enumerate(testers, 1):
        logger.info(f"\n[{i}/{len(testers)}] Running {tester.name}...")
        result = await tester.run()
        results.append(result)
        
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        logger.info(f"  {status} - Found {len(result.issues)} issues")
    
    return results


async def run_full_audit(config: AuditConfig) -> List[TestResult]:
    """
    Запустить полный аудит.
    
    Returns:
        Список всех результатов тестов
    """
    results = []
    
    # Static analysis
    static_results = await run_static_analysis(config)
    results.extend(static_results)
    
    # Runtime tests (if credentials available)
    if config.has_neo4j_credentials():
        runtime_results = await run_runtime_tests(config)
        results.extend(runtime_results)
        
        # Integration tests
        integration_results = await run_integration_tests(config)
        results.extend(integration_results)
    else:
        logger.warning("\n⚠️  Skipping runtime and integration tests (no database credentials)")
        logger.warning("   Set NEO4J_PASSWORD environment variable to run full audit")
    
    return results


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Fractal Memory Project Audit Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full audit
  python -m audit.main --full
  
  # Run only static analysis
  python -m audit.main --static-only
  
  # Run only runtime tests
  python -m audit.main --runtime-only
  
  # Generate JSON report
  python -m audit.main --full --output-format json
  
  # Save to custom file
  python -m audit.main --full --output-file my_report.md
  
  # Verbose output
  python -m audit.main --full --verbose
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--full',
        action='store_true',
        help='Run full audit (static + runtime + integration)'
    )
    mode_group.add_argument(
        '--static-only',
        action='store_true',
        help='Run only static analysis'
    )
    mode_group.add_argument(
        '--runtime-only',
        action='store_true',
        help='Run only runtime tests'
    )
    mode_group.add_argument(
        '--integration-only',
        action='store_true',
        help='Run only integration tests'
    )
    
    # Output options
    parser.add_argument(
        '--output-format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file path (default: auto-generated in audit_reports/)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (default: audit_reports/)'
    )
    
    # Other options
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip printing summary to console'
    )
    
    args = parser.parse_args()
    
    # Default to full audit if no mode specified
    if not any([args.full, args.static_only, args.runtime_only, args.integration_only]):
        args.full = True
    
    return args


async def main():
    """Главная функция."""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    logger.info("Starting Fractal Memory Project Audit")
    logger.info("=" * 60)
    
    # Load config
    config = AuditConfig()
    
    # Check credentials for runtime tests
    if (args.full or args.runtime_only or args.integration_only) and not config.has_neo4j_credentials():
        logger.warning("⚠️  No Neo4j credentials found!")
        logger.warning("   Runtime and integration tests will be skipped.")
        logger.warning("   Set NEO4J_PASSWORD environment variable to run full audit.")
    
    start_time = time.time()
    
    # Run audit based on mode
    try:
        if args.full:
            results = await run_full_audit(config)
        elif args.static_only:
            results = await run_static_analysis(config)
        elif args.runtime_only:
            if not config.has_neo4j_credentials():
                logger.error("❌ Cannot run runtime tests without database credentials")
                sys.exit(1)
            results = await run_runtime_tests(config)
        elif args.integration_only:
            if not config.has_neo4j_credentials():
                logger.error("❌ Cannot run integration tests without database credentials")
                sys.exit(1)
            results = await run_integration_tests(config)
        else:
            logger.error("❌ No audit mode specified")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Audit interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Audit failed with error: {e}", exc_info=True)
        sys.exit(1)
    
    duration = time.time() - start_time
    
    # Generate report
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING REPORT")
    logger.info("=" * 60)
    
    # Setup report generator
    output_dir = Path(args.output_dir) if args.output_dir else config.report_output_dir
    generator = ReportGenerator(output_dir=output_dir)
    
    # Generate report
    if args.output_file:
        # Custom output file
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format from extension if not specified
        if args.output_format == 'markdown' and output_path.suffix == '.json':
            format = 'json'
        elif args.output_format == 'json' and output_path.suffix == '.md':
            format = 'markdown'
        else:
            format = args.output_format
        
        # Generate to temp location first
        temp_path = generator.generate_report(results, duration, format=format)
        
        # Move to desired location
        import shutil
        shutil.move(temp_path, output_path)
        report_path = str(output_path)
    else:
        # Auto-generated filename
        report_path = generator.generate_report(results, duration, format=args.output_format)
    
    logger.info(f"\n✅ Audit complete!")
    logger.info(f"   Duration: {duration:.2f}s")
    logger.info(f"   Report: {report_path}")
    
    # Print summary to console
    if not args.no_summary:
        # Create audit report for summary
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        
        from audit.core.models import AuditReport, Severity
        from collections import defaultdict
        
        issues_by_severity = defaultdict(int)
        for issue in all_issues:
            issues_by_severity[issue.severity.value] += 1
        
        issues_by_category = defaultdict(int)
        for issue in all_issues:
            issues_by_category[issue.category.value] += 1
        
        audit_report = AuditReport(
            timestamp=datetime.now(),
            total_issues=len(all_issues),
            issues_by_severity=dict(issues_by_severity),
            issues_by_category=dict(issues_by_category),
            test_results=results,
            all_issues=all_issues,
            duration_seconds=duration,
        )
        
        generator.print_summary(audit_report)
    
    # Exit with error code if critical issues found
    critical_count = sum(1 for r in results for i in r.issues if i.severity.value == 'critical')
    if critical_count > 0:
        logger.error(f"\n❌ {critical_count} CRITICAL issues found!")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
