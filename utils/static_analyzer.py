"""
Static Analyzer Module for Resume PDF Validation

This module analyzes compiled resume PDFs for:
- Page Count: Verifies exactly 1 page
- Skills Section: Checks if all skill categories fit on single lines
- Bullet Points: Detects orphans (bullets with <15 chars on continuation line)
"""

import os
import re
from typing import Dict, List, Any, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class StaticAnalyzer:
    """Analyzes resume PDFs for layout and formatting issues."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize the static analyzer with a PDF file path.
        
        Args:
            pdf_path: Path to the compiled resume PDF file
        """
        self.pdf_path = pdf_path
        self.doc = None
        self.issues: List[Dict[str, Any]] = []
        self.passed_checks: List[Dict[str, Any]] = []
        
    def open_pdf(self) -> bool:
        """
        Open the PDF file for analysis.
        
        Returns:
            True if successful, False otherwise
        """
        if fitz is None:
            self.issues.append({
                "check": "PyMuPDF",
                "issue": "PyMuPDF (fitz) is not installed",
                "severity": "error"
            })
            return False
            
        try:
            self.doc = fitz.open(self.pdf_path)
            return True
        except Exception as e:
            self.issues.append({
                "check": "PDF Load",
                "issue": f"Failed to open PDF: {str(e)}",
                "severity": "error"
            })
            return False
    
    def close_pdf(self):
        """Close the PDF document if open."""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def check_page_count(self) -> bool:
        """
        Verify that the resume is exactly 1 page.
        
        Returns:
            True if page count is exactly 1, False otherwise
        """
        if not self.doc:
            return False
            
        page_count = len(self.doc)
        
        if page_count == 1:
            self.passed_checks.append({
                "check": "Page Count",
                "detail": "Resume is exactly 1 page"
            })
            return True
        else:
            self.issues.append({
                "check": "Page Count",
                "issue": f"Resume has {page_count} page(s), expected exactly 1",
                "severity": "warning" if page_count == 0 else "error"
            })
            return False
    
    def check_skills_section(self) -> bool:
        """
        Check if all skill categories fit on single lines.
        
        This analyzes text blocks in the PDF to detect if skill sections
        wrap to multiple lines, which may indicate overcrowding.
        
        Returns:
            True if all skills fit on single lines, False otherwise
        """
        if not self.doc:
            return False
            
        skills_found = False
        skills_wrapping = False
        
        # Common skill section headers to look for
        skill_headers = [
            r"skills", r"technical skills", r"core competencies",
            r"programming", r"languages", r"technologies",
            r"tools", r"frameworks", r"expertise"
        ]
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict").get("blocks", [])
            
            in_skills_section = False
            current_skill_line_y = None
            skill_line_tolerance = 5  # pixels tolerance for same line
            
            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks
                    continue
                    
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "")
                
                block_text_lower = block_text.lower().strip()
                
                # Check if this is a skills section header
                for header_pattern in skill_headers:
                    if re.search(header_pattern, block_text_lower):
                        in_skills_section = True
                        skills_found = True
                        break
                
                if in_skills_section:
                    # Analyze lines within this block
                    for line in block.get("lines", []):
                        line_text = ""
                        line_bbox = line.get("bbox", (0, 0, 0, 0))
                        line_y = line_bbox[1]  # Top y-coordinate
                        
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        
                        line_text = line_text.strip()
                        
                        # Skip empty lines or very short lines
                        if len(line_text) < 2:
                            continue
                        
                        # Check if this looks like a skill entry (contains commas, pipes, or common tech terms)
                        is_skill_line = (
                            "," in line_text or 
                            "|" in line_text or 
                            "•" in line_text or
                            re.search(r"\b(python|java|javascript|react|node|aws|docker|kubernetes|sql|git|linux|html|css)\b", line_text, re.IGNORECASE)
                        )
                        
                        if is_skill_line:
                            # Check if line width exceeds typical page width threshold
                            line_width = line_bbox[2] - line_bbox[0]
                            page_width = page.rect.width
                            
                            # If line takes up most of the page width, it might be wrapping
                            if line_width > page_width * 0.85:
                                # Check if next line starts very close in y-position (indicating wrap)
                                if current_skill_line_y is not None:
                                    if abs(line_y - current_skill_line_y) < skill_line_tolerance:
                                        skills_wrapping = True
                                        self.issues.append({
                                            "check": "Skills Section",
                                            "issue": f"Skill line appears to wrap: '{line_text[:50]}...'",
                                            "severity": "info"
                                        })
                            current_skill_line_y = line_y
                            
                            # Exit skills section if we hit a new major section
                            if re.match(r"^(experience|education|projects|work|history)", line_text_lower := line_text.lower()):
                                in_skills_section = False
                                break
        
        if skills_found and not skills_wrapping:
            self.passed_checks.append({
                "check": "Skills Section",
                "detail": "All skill categories fit on single lines"
            })
            return True
        elif not skills_found:
            self.passed_checks.append({
                "check": "Skills Section",
                "detail": "No explicit skills section detected (may use alternative formatting)"
            })
            return True
        else:
            return False
    
    def check_bullet_orphans(self) -> bool:
        """
        Detect orphaned bullet points (bullets with <15 chars on continuation line).
        
        An orphan occurs when a bullet point's content continues on the next line
        but the continuation line has fewer than 15 characters.
        
        Returns:
            True if no orphans found, False otherwise
        """
        if not self.doc:
            return False
            
        orphans_found = False
        min_continuation_chars = 15
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict").get("blocks", [])
            
            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks
                    continue
                
                lines = block.get("lines", [])
                
                for i, line in enumerate(lines):
                    line_text = ""
                    line_bbox = line.get("bbox", (0, 0, 0, 0))
                    
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    
                    line_text = line_text.strip()
                    
                    # Check if this line starts with a bullet
                    bullet_patterns = [r"^•", r"^-", r"^\*", r"^›", r"^‣"]
                    is_bullet_line = any(re.match(pattern, line_text) for pattern in bullet_patterns)
                    
                    if is_bullet_line and i < len(lines) - 1:
                        # Get the next line to check for orphan
                        next_line = lines[i + 1]
                        next_text = ""
                        next_bbox = next_line.get("bbox", (0, 0, 0, 0))
                        
                        for span in next_line.get("spans", []):
                            next_text += span.get("text", "")
                        
                        next_text = next_text.strip()
                        
                        # Check if next line is indented similarly (continuation)
                        current_indent = line_bbox[0]
                        next_indent = next_bbox[0]
                        
                        # If next line is indented more than current, it's likely a continuation
                        if next_indent > current_indent + 5:
                            if len(next_text) > 0 and len(next_text) < min_continuation_chars:
                                orphans_found = True
                                self.issues.append({
                                    "check": "Bullet Orphans",
                                    "issue": f"Bullet continuation line has only {len(next_text)} chars: '{next_text}'",
                                    "severity": "info"
                                })
        
        if not orphans_found:
            self.passed_checks.append({
                "check": "Bullet Orphans",
                "detail": "No orphaned bullet continuations detected"
            })
            return True
        else:
            return False
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run all static analysis checks on the PDF.
        
        Returns:
            Dictionary containing analysis results with:
            - pass: Boolean indicating if all critical checks passed
            - issues: List of issues found
            - passed_checks: List of checks that passed
        """
        # Reset state
        self.issues = []
        self.passed_checks = []
        
        # Open PDF
        if not self.open_pdf():
            return {
                "pass": False,
                "issues": self.issues,
                "passed_checks": self.passed_checks
            }
        
        try:
            # Run all checks
            page_ok = self.check_page_count()
            skills_ok = self.check_skills_section()
            bullets_ok = self.check_bullet_orphans()
            
            # Determine overall pass status
            # Pass if no errors (warnings and infos are acceptable)
            has_errors = any(issue.get("severity") == "error" for issue in self.issues)
            overall_pass = not has_errors
            
            return {
                "pass": overall_pass,
                "issues": self.issues,
                "passed_checks": self.passed_checks
            }
        finally:
            self.close_pdf()


def analyze_resume(pdf_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a resume PDF.
    
    Args:
        pdf_path: Path to the resume PDF file
        
    Returns:
        Dictionary containing analysis results
    """
    if not os.path.exists(pdf_path):
        return {
            "pass": False,
            "issues": [{
                "check": "File Existence",
                "issue": f"PDF file not found: {pdf_path}",
                "severity": "error"
            }],
            "passed_checks": []
        }
    
    analyzer = StaticAnalyzer(pdf_path)
    return analyzer.analyze()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        result = analyze_resume(pdf_file)
        print(f"Analysis Result: {'PASS' if result['pass'] else 'FAIL'}")
        print(f"Issues: {len(result['issues'])}")
        print(f"Passed Checks: {len(result['passed_checks'])}")
        
        if result["issues"]:
            print("\nIssues Found:")
            for issue in result["issues"]:
                print(f"  - [{issue['severity'].upper()}] {issue['check']}: {issue['issue']}")
        
        if result["passed_checks"]:
            print("\nPassed Checks:")
            for check in result["passed_checks"]:
                print(f"  ✓ {check['check']}: {check['detail']}")
    else:
        print("Usage: python static_analyzer.py <path_to_pdf>")
