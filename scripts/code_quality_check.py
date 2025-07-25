#!/usr/bin/env python3
"""
Code quality analysis script for Pokemon Gym streaming system.
Checks for common performance issues, code smells, and best practices.
"""

import os
import ast
import re
from typing import List, Dict, Tuple
from pathlib import Path
import json


class CodeQualityChecker:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues = []
        self.stats = {
            "total_files": 0,
            "python_files": 0,
            "typescript_files": 0,
            "total_lines": 0,
            "issues_found": 0,
        }
        
    def check_python_file(self, filepath: Path) -> List[Dict]:
        """Analyze a Python file for code quality issues."""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            self.stats["python_files"] += 1
            self.stats["total_lines"] += len(lines)
            
            # Parse AST
            try:
                tree = ast.parse(content)
                
                # Check for performance issues
                for node in ast.walk(tree):
                    # Check for synchronous file I/O in loops
                    if isinstance(node, ast.For) or isinstance(node, ast.While):
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Name) and child.func.id == 'open':
                                    issues.append({
                                        "file": str(filepath),
                                        "line": child.lineno,
                                        "severity": "high",
                                        "issue": "File I/O inside loop",
                                        "description": "Opening files inside loops can cause performance issues"
                                    })
                                    
                    # Check for unbuffered writes
                    if isinstance(node, ast.Call):
                        if (isinstance(node.func, ast.Attribute) and 
                            node.func.attr == 'write' and
                            isinstance(node.func.value, ast.Name)):
                            # Check if it's inside a with statement (good practice)
                            parent = None
                            for p_node in ast.walk(tree):
                                if hasattr(p_node, 'body') and node in ast.walk(p_node):
                                    parent = p_node
                                    break
                            
                            if not isinstance(parent, ast.With):
                                issues.append({
                                    "file": str(filepath),
                                    "line": node.lineno,
                                    "severity": "medium",
                                    "issue": "Unbuffered write operation",
                                    "description": "Consider using buffered writes or context managers"
                                })
                                
                    # Check for missing error handling
                    if isinstance(node, ast.FunctionDef):
                        has_try_except = any(isinstance(n, ast.Try) for n in ast.walk(node))
                        if 'api' in node.name.lower() or 'request' in node.name.lower():
                            if not has_try_except:
                                issues.append({
                                    "file": str(filepath),
                                    "line": node.lineno,
                                    "severity": "medium",
                                    "issue": "Missing error handling",
                                    "description": f"Function '{node.name}' should have error handling"
                                })
                                
            except SyntaxError as e:
                issues.append({
                    "file": str(filepath),
                    "line": e.lineno or 0,
                    "severity": "critical",
                    "issue": "Syntax error",
                    "description": str(e)
                })
                
            # Check for common patterns
            for i, line in enumerate(lines, 1):
                # Check for print statements (should use logging)
                if re.match(r'^\s*print\s*\(', line) and 'debug' not in filepath.name.lower():
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": "low",
                        "issue": "Using print instead of logging",
                        "description": "Consider using logger instead of print statements"
                    })
                    
                # Check for hardcoded URLs/ports
                if re.search(r'localhost:\d{4}|127\.0\.0\.1:\d{4}', line):
                    if not re.search(r'default\s*=|help\s*=', line):
                        issues.append({
                            "file": str(filepath),
                            "line": i,
                            "severity": "medium",
                            "issue": "Hardcoded URL/port",
                            "description": "Consider using configuration variables"
                        })
                        
                # Check for TODO/FIXME comments
                if re.search(r'#\s*(TODO|FIXME|XXX|HACK)', line, re.IGNORECASE):
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": "info",
                        "issue": "Unresolved TODO/FIXME",
                        "description": line.strip()
                    })
                    
        except Exception as e:
            issues.append({
                "file": str(filepath),
                "line": 0,
                "severity": "error",
                "issue": "File analysis error",
                "description": str(e)
            })
            
        return issues
        
    def check_typescript_file(self, filepath: Path) -> List[Dict]:
        """Analyze a TypeScript/React file for code quality issues."""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            self.stats["typescript_files"] += 1
            self.stats["total_lines"] += len(lines)
            
            for i, line in enumerate(lines, 1):
                # Check for console.log statements
                if re.search(r'console\.(log|error|warn)', line):
                    if 'debug' not in filepath.name.lower():
                        issues.append({
                            "file": str(filepath),
                            "line": i,
                            "severity": "low",
                            "issue": "Console statement in production code",
                            "description": "Remove console statements for production"
                        })
                        
                # Check for any type
                if re.search(r':\s*any\b', line):
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": "medium",
                        "issue": "Using 'any' type",
                        "description": "Avoid using 'any' type, use specific types instead"
                    })
                    
                # Check for missing error handling in fetch
                if 'fetch(' in line and '.catch' not in content[max(0, i-10):min(len(lines), i+10)]:
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": "high",
                        "issue": "Fetch without error handling",
                        "description": "Add .catch() or try-catch for fetch operations"
                    })
                    
                # Check for inefficient array operations in render
                if re.search(r'\.map\s*\(.*\)\.filter\s*\(', line):
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": "medium",
                        "issue": "Chained array operations",
                        "description": "Consider combining map and filter for better performance"
                    })
                    
        except Exception as e:
            issues.append({
                "file": str(filepath),
                "line": 0,
                "severity": "error",
                "issue": "File analysis error",
                "description": str(e)
            })
            
        return issues
        
    def analyze_project(self) -> None:
        """Analyze the entire project for code quality issues."""
        print("Analyzing Pokemon Gym streaming system code quality...")
        print("="*60)
        
        # Define paths to analyze
        paths_to_check = [
            self.project_root / "agents",
            self.project_root / "server",
            self.project_root / "streaming-dashboard",
            self.project_root / "evaluator",
        ]
        
        for path in paths_to_check:
            if path.exists():
                print(f"\nAnalyzing {path.name}/...")
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        self.stats["total_files"] += 1
                        
                        if file_path.suffix == ".py":
                            issues = self.check_python_file(file_path)
                            self.issues.extend(issues)
                            
                        elif file_path.suffix in [".ts", ".tsx", ".js", ".jsx"]:
                            issues = self.check_typescript_file(file_path)
                            self.issues.extend(issues)
                            
        self.stats["issues_found"] = len(self.issues)
        
    def print_report(self) -> None:
        """Print the code quality report."""
        print("\n" + "="*60)
        print("CODE QUALITY REPORT")
        print("="*60)
        
        print(f"\nFiles analyzed: {self.stats['total_files']}")
        print(f"Python files: {self.stats['python_files']}")
        print(f"TypeScript/JavaScript files: {self.stats['typescript_files']}")
        print(f"Total lines of code: {self.stats['total_lines']}")
        print(f"Issues found: {self.stats['issues_found']}")
        
        if self.issues:
            # Group by severity
            severity_groups = {}
            for issue in self.issues:
                severity = issue["severity"]
                if severity not in severity_groups:
                    severity_groups[severity] = []
                severity_groups[severity].append(issue)
                
            # Print by severity
            severity_order = ["critical", "high", "medium", "low", "info"]
            for severity in severity_order:
                if severity in severity_groups:
                    print(f"\n{severity.upper()} ({len(severity_groups[severity])} issues):")
                    print("-" * 40)
                    
                    for issue in severity_groups[severity][:10]:  # Show first 10
                        print(f"  {issue['file']}:{issue['line']}")
                        print(f"    Issue: {issue['issue']}")
                        print(f"    {issue['description']}")
                        print()
                        
                    if len(severity_groups[severity]) > 10:
                        print(f"  ... and {len(severity_groups[severity]) - 10} more")
                        
        # Save detailed report
        report = {
            "stats": self.stats,
            "issues": self.issues
        }
        
        with open("code_quality_report.json", "w") as f:
            json.dump(report, f, indent=2)
            
        print(f"\nDetailed report saved to code_quality_report.json")
        
        # Summary
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        
        high_priority_count = sum(1 for i in self.issues if i["severity"] in ["critical", "high"])
        if high_priority_count > 0:
            print(f"- Fix {high_priority_count} high-priority issues immediately")
            
        if any("File I/O inside loop" in i["issue"] for i in self.issues):
            print("- Optimize file I/O operations by moving them outside loops")
            
        if any("Fetch without error handling" in i["issue"] for i in self.issues):
            print("- Add proper error handling to all API calls")
            
        if any("any" in i["issue"] for i in self.issues):
            print("- Replace 'any' types with specific TypeScript types")
            
        print("\nOverall code quality score: ", end="")
        if self.stats["issues_found"] == 0:
            print("EXCELLENT ✓")
        elif high_priority_count == 0:
            print("GOOD")
        elif high_priority_count < 5:
            print("FAIR")
        else:
            print("NEEDS IMPROVEMENT")


def main():
    checker = CodeQualityChecker(".")
    checker.analyze_project()
    checker.print_report()


if __name__ == "__main__":
    main()