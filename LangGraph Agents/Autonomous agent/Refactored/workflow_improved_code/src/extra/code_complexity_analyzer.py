import re
from typing import List, Optional, Dict, Any
import os

class ComplexityMetrics:
    def __init__(self,
                 cyclomatic_complexity: int,
                 dependency_count: int,
                 parameter_count: Optional[int],
                 lines_of_code: Dict[str, int],
                 nesting_depth: int,
                 comment_ratio: float,
                 implementation_depth_score: int):
        self.cyclomatic_complexity = cyclomatic_complexity
        self.dependency_count = dependency_count
        self.parameter_count = parameter_count
        self.lines_of_code = lines_of_code
        self.nesting_depth = nesting_depth
        self.comment_ratio = comment_ratio
        self.implementation_depth_score = implementation_depth_score

class ImplementationPattern:
    SHALLOW_IMPLEMENTATION = 'SHALLOW_IMPLEMENTATION'
    COMMENT_HEAVY = 'COMMENT_HEAVY'
    TODO_MARKERS = 'TODO_MARKERS'
    MISSING_ERROR_HANDLING = 'MISSING_ERROR_HANDLING'
    HARDCODED_RETURNS = 'HARDCODED_RETURNS'
    DUPLICATED_CODE = 'DUPLICATED_CODE'
    INTERFACE_ONLY = 'INTERFACE_ONLY'
    MOCK_HEAVY = 'MOCK_HEAVY'

class ImplementationPatternDetails:
    def __init__(self, pattern_type: str, description: str, confidence: int, lines: List[int], snippets: List[str]):
        self.pattern_type = pattern_type
        self.description = description
        self.confidence = confidence
        self.lines = lines
        self.snippets = snippets

class CodeComplexityAnalyzer:
    def __init__(self):
        pass

    def analyze_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        metrics = self.calculate_metrics(code)
        patterns = self.detect_suspicious_patterns(code)
        return {
            'complexity_metrics': metrics,
            'suspicious_patterns': patterns
        }

    def calculate_metrics(self, code: str) -> ComplexityMetrics:
        lines = code.split('\n')
        physical = len(lines)
        comment_regex = re.compile(r'^\s*(#|"""|\'\'\')')
        comment_lines = len([line for line in lines if comment_regex.match(line)])
        logical_lines = len([line for line in lines if line.strip() and not comment_regex.match(line)])

        # Cyclomatic complexity estimation: count branching keywords
        branching_keywords = ['if ', 'for ', 'while ', 'case ', 'except ', 'and ', 'or ']
        branches = 0
        for kw in branching_keywords:
            branches += len(re.findall(r'\b' + re.escape(kw.strip()) + r'\b', code))
        cyclomatic_complexity = branches + 1

        # Dependency count: count import statements
        dependency_count = len(re.findall(r'^\s*(import|from)\s+', code, re.MULTILINE))

        # Parameter count: try to find function definitions and count parameters of first function
        parameter_count = None
        func_match = re.search(r'def\s+\w+\s*\(([^)]*)\):', code)
        if func_match:
            params = func_match.group(1)
            if params.strip():
                parameter_count = len([p for p in params.split(',') if p.strip()])
            else:
                parameter_count = 0

        nesting_depth = self.calculate_nesting_depth(code)

        comment_ratio = comment_lines / (logical_lines or 1)

        implementation_depth_score = self.calculate_implementation_depth_score(
            cyclomatic_complexity=cyclomatic_complexity,
            nesting_depth=nesting_depth,
            logical_lines=logical_lines,
            comment_ratio=comment_ratio
        )

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic_complexity,
            dependency_count=dependency_count,
            parameter_count=parameter_count,
            lines_of_code={
                'physical': physical,
                'logical': logical_lines,
                'comments': comment_lines
            },
            nesting_depth=nesting_depth,
            comment_ratio=comment_ratio,
            implementation_depth_score=implementation_depth_score
        )

    def calculate_nesting_depth(self, code: str) -> int:
        lines = code.split('\n')
        current_depth = 0
        max_depth = 0
        for line in lines:
            # Count indentation level (number of leading spaces divided by 4)
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            depth = indent // 4
            if depth > max_depth:
                max_depth = depth
        return max_depth

    def calculate_implementation_depth_score(self, cyclomatic_complexity: int, nesting_depth: int,
                                             logical_lines: int, comment_ratio: float) -> int:
        MIN_LOGICAL_LINES = 3
        MIN_CYCLOMATIC = 2
        MAX_COMMENT_RATIO = 2.5

        score = 70

        if logical_lines < MIN_LOGICAL_LINES:
            score -= 30
        elif logical_lines < MIN_LOGICAL_LINES * 2:
            score -= 15

        if cyclomatic_complexity >= MIN_CYCLOMATIC:
            score += 10

        if comment_ratio > MAX_COMMENT_RATIO:
            score -= 20

        if 0 < nesting_depth <= 3:
            score += 10
        elif nesting_depth > 3:
            score -= 10

        return max(0, min(100, score))

    def detect_suspicious_patterns(self, code: str) -> List[ImplementationPatternDetails]:
        patterns = []
        lines = code.split('\n')

        # TODO/FIXME markers
        todo_regex = re.compile(r'\b(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE)
        todo_lines = [(i + 1, line) for i, line in enumerate(lines) if todo_regex.search(line)]
        if todo_lines:
            patterns.append(ImplementationPatternDetails(
                pattern_type=ImplementationPattern.TODO_MARKERS,
                description='Code contains TODO or FIXME markers indicating incomplete implementation',
                confidence=95,
                lines=[ln for ln, _ in todo_lines],
                snippets=[line for _, line in todo_lines]
            ))

        # Shallow implementation: less than 3 non-empty lines
        non_empty_lines = [line for line in lines if line.strip()]
        if len(non_empty_lines) < 3:
            patterns.append(ImplementationPatternDetails(
                pattern_type=ImplementationPattern.SHALLOW_IMPLEMENTATION,
                description='Entity has minimal implementation with few lines of code',
                confidence=90,
                lines=[1],
                snippets=[code]
            ))

        # Missing error handling in async code (Python async def)
        async_pattern = re.compile(r'\basync\s+def\b')
        try_catch_pattern = re.compile(r'\btry\b[\s\S]*\bexcept\b')
        if async_pattern.search(code) and not try_catch_pattern.search(code):
            patterns.append(ImplementationPatternDetails(
                pattern_type=ImplementationPattern.MISSING_ERROR_HANDLING,
                description='Async code without error handling',
                confidence=75,
                lines=[1],
                snippets=['Async code without try/except or error handling']
            ))

        # Hardcoded return values
        return_literal_regex = re.compile(r'return\s+(["\'].*?["\']|\d+|True|False|None|\[\s*\]|\{\s*\})')
        if return_literal_regex.search(code):
            patterns.append(ImplementationPatternDetails(
                pattern_type=ImplementationPattern.HARDCODED_RETURNS,
                description='Function returns hardcoded literal values',
                confidence=80,
                lines=[1],
                snippets=[return_literal_regex.search(code).group(0)]
            ))

        # Comment heavy code: more comment lines than code lines * 2
        comment_lines = len([line for line in lines if re.match(r'^\s*(#|"""|\'\'\')', line)])
        code_lines = len(lines) - comment_lines
        if comment_lines > code_lines * 2:
            patterns.append(ImplementationPatternDetails(
                pattern_type=ImplementationPattern.COMMENT_HEAVY,
                description='Code has more comments than actual implementation',
                confidence=85,
                lines=[1],
                snippets=[f"{comment_lines} lines of comments vs {code_lines} lines of code"]
            ))

        return patterns

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python code_complexity_analyzer.py <path_to_python_file>")
        sys.exit(1)
    analyzer = CodeComplexityAnalyzer()
    result = analyzer.analyze_file(sys.argv[1])
    if result:
        metrics = result['complexity_metrics']
        print("Cyclomatic Complexity:", metrics.cyclomatic_complexity)
        print("Dependency Count:", metrics.dependency_count)
        print("Parameter Count:", metrics.parameter_count)
        print("Lines of Code:", metrics.lines_of_code)
        print("Nesting Depth:", metrics.nesting_depth)
        print("Comment Ratio:", metrics.comment_ratio)
        print("Implementation Depth Score:", metrics.implementation_depth_score)
        print("\nSuspicious Patterns Detected:")
        for pattern in result['suspicious_patterns']:
            print(f"- {pattern.pattern_type}: {pattern.description} (Confidence: {pattern.confidence}%)")
            for line, snippet in zip(pattern.lines, pattern.snippets):
                print(f"  Line {line}: {snippet}")
