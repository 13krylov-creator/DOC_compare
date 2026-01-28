"""
Enterprise Document Comparison Engine
Multi-mode comparison with AI integration
"""
import difflib
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional


class DiffEngine:
    """Enterprise-grade diff engine with multiple comparison modes"""
    
    def __init__(self):
        self.mode = "line-by-line"
        self.show_full = True  # Show full document by default
    
    def compare(self, text1: str, text2: str, mode: str = "line-by-line", show_full: bool = True) -> Dict[str, Any]:
        """Main comparison entry point - dispatches to mode-specific methods"""
        self.mode = mode
        self.show_full = show_full
        
        if mode == "line-by-line":
            return self._line_by_line_diff(text1, text2)
        elif mode == "semantic":
            return self._semantic_diff(text1, text2)
        else:
            return self._line_by_line_diff(text1, text2)
    
    # ==================== MODE: LINE-BY-LINE ====================
    def _line_by_line_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Classic line-by-line diff with character highlighting"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        changes = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            if tag == 'replace':
                for idx in range(max(i2 - i1, j2 - j1)):
                    old_line = lines1[i1 + idx] if i1 + idx < i2 else ""
                    new_line = lines2[j1 + idx] if j1 + idx < j2 else ""
                    
                    if old_line and new_line:
                        inline_diff = self._compute_inline_diff(old_line, new_line)
                        changes.append(self._make_change(
                            "MODIFIED", old_line, new_line, 
                            f"строка {i1 + idx + 1}",
                            inline_diff
                        ))
                    elif old_line:
                        changes.append(self._make_change("DELETED", old_line, None, f"строка {i1 + idx + 1}"))
                    elif new_line:
                        changes.append(self._make_change("ADDED", None, new_line, f"строка {j1 + idx + 1}"))
            
            elif tag == 'delete':
                for idx in range(i1, i2):
                    if lines1[idx].strip():
                        changes.append(self._make_change("DELETED", lines1[idx], None, f"строка {idx + 1}"))
            
            elif tag == 'insert':
                for idx in range(j1, j2):
                    if lines2[idx].strip():
                        changes.append(self._make_change("ADDED", None, lines2[idx], f"строка {idx + 1}"))
        
        result = self._build_result(changes, text1, text2)
        result["diff_lines"] = self._build_side_by_side(lines1, lines2)
        result["mode_info"] = {
            "name": "Построчный",
            "description": "Классический diff — сравнение строка за строкой"
        }
        return result
    
    # ==================== MODE: SEMANTIC ====================
    def _semantic_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Semantic analysis - groups related changes, identifies meaning shifts"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # First, get line-level changes
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        raw_changes = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            if tag == 'replace':
                for idx in range(max(i2 - i1, j2 - j1)):
                    old_line = lines1[i1 + idx] if i1 + idx < i2 else ""
                    new_line = lines2[j1 + idx] if j1 + idx < j2 else ""
                    if old_line or new_line:
                        raw_changes.append((old_line, new_line, i1 + idx))
            elif tag == 'delete':
                for idx in range(i1, i2):
                    raw_changes.append((lines1[idx], "", idx))
            elif tag == 'insert':
                for idx in range(j1, j2):
                    raw_changes.append(("", lines2[idx], idx))
        
        # Semantic grouping - combine related changes
        changes = []
        for old, new, line_num in raw_changes:
            if not old.strip() and not new.strip():
                continue
            
            # Semantic classification
            semantic_type = self._classify_semantic_change(old, new)
            meaning_shift = self._detect_meaning_shift(old, new)
            
            change = self._make_change(
                "MODIFIED" if old and new else ("DELETED" if old else "ADDED"),
                old or None, new or None, f"строка {line_num + 1}"
            )
            change["semantic_type"] = semantic_type
            change["meaning_shift"] = meaning_shift
            change["ai_summary"] = self._generate_semantic_summary(old, new, semantic_type)
            
            # Boost severity for semantic changes
            if meaning_shift:
                change["severity"] = "CRITICAL" if "критич" in meaning_shift.lower() else "MAJOR"
            
            changes.append(change)
        
        result = self._build_result(changes, text1, text2)
        result["diff_lines"] = self._build_side_by_side(lines1, lines2)
        result["mode_info"] = {
            "name": "Семантический",
            "description": "Анализ смысловых изменений — выявляет изменения значения"
        }
        return result
    
    # ==================== MODE: IMPACT ====================
    def _impact_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Financial/business impact analysis - focuses on numbers and obligations"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        changes = []
        financial_impact = []
        
        # Extract all numbers from both documents
        numbers1 = self._extract_all_numbers(text1)
        numbers2 = self._extract_all_numbers(text2)
        
        # Find number changes
        all_contexts = set(numbers1.keys()) | set(numbers2.keys())
        for context in all_contexts:
            old_val = numbers1.get(context)
            new_val = numbers2.get(context)
            
            if old_val != new_val:
                if old_val and new_val:
                    change_pct = ((new_val - old_val) / old_val * 100) if old_val else 0
                    direction = "увеличение" if change_pct > 0 else "уменьшение"
                else:
                    change_pct = 100 if new_val else -100
                    direction = "добавлено" if new_val else "удалено"
                
                severity = "CRITICAL" if abs(change_pct) > 20 else ("MAJOR" if abs(change_pct) > 5 else "MINOR")
                
                financial_impact.append({
                    "parameter": context,
                    "original": old_val,
                    "new": new_val,
                    "change_percent": round(change_pct, 1),
                    "direction": direction
                })
                
                changes.append({
                    "id": f"change_{uuid.uuid4().hex[:8]}",
                    "type": "MODIFIED",
                    "classification": "FINANCIAL_CHANGE",
                    "severity": severity,
                    "location": context,
                    "original_text": f"{old_val}" if old_val else "—",
                    "new_text": f"{new_val}" if new_val else "—",
                    "ai_summary": f"💰 {direction.capitalize()}: {old_val or 0} → {new_val or 0} ({change_pct:+.1f}%)",
                    "impact_score": min(100, int(abs(change_pct) * 2)),
                    "business_context": f"Финансовое изменение на {abs(change_pct):.1f}%"
                })
        
        # Also get regular line changes
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for idx in range(max(i2 - i1, j2 - j1)):
                    old_line = lines1[i1 + idx] if i1 + idx < i2 else ""
                    new_line = lines2[j1 + idx] if j1 + idx < j2 else ""
                    if old_line and new_line and self._has_numbers(old_line + new_line):
                        inline = self._compute_inline_diff(old_line, new_line)
                        changes.append(self._make_change("MODIFIED", old_line, new_line, f"строка {i1+idx+1}", inline))
        
        result = self._build_result(changes, text1, text2)
        result["diff_lines"] = self._build_side_by_side(lines1, lines2)
        result["financial_impact"] = financial_impact
        result["mode_info"] = {
            "name": "Влияние",
            "description": "Анализ финансового влияния — фокус на суммах и обязательствах"
        }
        return result
    
    # ==================== MODE: CLAUSE ====================
    def _clause_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Clause-by-clause analysis - groups changes by document sections"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # Extract clauses from both documents
        clauses1 = self._extract_clauses(text1)
        clauses2 = self._extract_clauses(text2)
        
        changes = []
        all_clause_types = set(clauses1.keys()) | set(clauses2.keys())
        
        for clause_type in all_clause_types:
            c1_lines = clauses1.get(clause_type, [])
            c2_lines = clauses2.get(clause_type, [])
            
            if not c1_lines and c2_lines:
                changes.append({
                    "id": f"change_{uuid.uuid4().hex[:8]}",
                    "type": "ADDED",
                    "classification": "CLAUSE_ADDED",
                    "severity": "MAJOR",
                    "location": clause_type,
                    "clause_type": clause_type,
                    "original_text": None,
                    "new_text": "\n".join(c2_lines)[:300],
                    "ai_summary": f"📋 Добавлен раздел: {clause_type}",
                    "impact_score": 70
                })
            elif c1_lines and not c2_lines:
                changes.append({
                    "id": f"change_{uuid.uuid4().hex[:8]}",
                    "type": "DELETED",
                    "classification": "CLAUSE_DELETED",
                    "severity": "CRITICAL",
                    "location": clause_type,
                    "clause_type": clause_type,
                    "original_text": "\n".join(c1_lines)[:300],
                    "new_text": None,
                    "ai_summary": f"📋 Удалён раздел: {clause_type}",
                    "impact_score": 85
                })
            elif c1_lines != c2_lines:
                # Compare clause contents
                c1_text = "\n".join(c1_lines)
                c2_text = "\n".join(c2_lines)
                ratio = difflib.SequenceMatcher(None, c1_text, c2_text).ratio()
                severity = "MINOR" if ratio > 0.9 else ("MAJOR" if ratio > 0.7 else "CRITICAL")
                
                changes.append({
                    "id": f"change_{uuid.uuid4().hex[:8]}",
                    "type": "MODIFIED",
                    "classification": "CLAUSE_MODIFIED",
                    "severity": severity,
                    "location": clause_type,
                    "clause_type": clause_type,
                    "original_text": c1_text[:300],
                    "new_text": c2_text[:300],
                    "ai_summary": f"📋 Изменён раздел: {clause_type} (схожесть: {ratio*100:.0f}%)",
                    "impact_score": int((1 - ratio) * 100)
                })
        
        result = self._build_result(changes, text1, text2)
        result["diff_lines"] = self._build_side_by_side(lines1, lines2)
        result["mode_info"] = {
            "name": "По пунктам",
            "description": "Анализ по разделам — группировка изменений по пунктам договора"
        }
        return result
    
    # ==================== MODE: LEGAL ====================
    def _legal_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Legal analysis - focuses on legal terms and risks"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # Get base line changes
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        changes = []
        
        legal_keywords = {
            "ответственност": ("LIABILITY", "Изменение ответственности", "CRITICAL"),
            "штраф": ("PENALTY", "Изменение штрафных санкций", "CRITICAL"),
            "неустойк": ("PENALTY", "Изменение неустойки", "CRITICAL"),
            "обязательств": ("OBLIGATION", "Изменение обязательств", "MAJOR"),
            "право": ("RIGHT", "Изменение прав", "MAJOR"),
            "расторж": ("TERMINATION", "Условия расторжения", "CRITICAL"),
            "гарант": ("WARRANTY", "Гарантийные условия", "MAJOR"),
            "конфиденциальн": ("CONFIDENTIALITY", "Конфиденциальность", "MAJOR"),
            "форс-мажор": ("FORCE_MAJEURE", "Форс-мажор", "MAJOR"),
        }
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            if tag in ('replace', 'delete', 'insert'):
                for idx in range(max(i2 - i1 if tag != 'insert' else 0, j2 - j1 if tag != 'delete' else 0)):
                    old_line = lines1[i1 + idx] if tag != 'insert' and i1 + idx < i2 else ""
                    new_line = lines2[j1 + idx] if tag != 'delete' and j1 + idx < j2 else ""
                    
                    if not old_line.strip() and not new_line.strip():
                        continue
                    
                    combined = (old_line + " " + new_line).lower()
                    
                    # Find legal classification
                    legal_type = "GENERAL"
                    legal_desc = "Общее изменение"
                    severity = "MINOR"
                    risk_level = "LOW"
                    
                    for keyword, (ltype, ldesc, sev) in legal_keywords.items():
                        if keyword in combined:
                            legal_type = ltype
                            legal_desc = ldesc
                            severity = sev
                            risk_level = "HIGH" if sev == "CRITICAL" else "MEDIUM"
                            break
                    
                    change = self._make_change(
                        "MODIFIED" if old_line and new_line else ("DELETED" if old_line else "ADDED"),
                        old_line or None, new_line or None, f"строка {i1 + idx + 1}"
                    )
                    change["legal_type"] = legal_type
                    change["severity"] = severity
                    change["legal_risk"] = {
                        "level": risk_level,
                        "description": legal_desc,
                        "recommendation": "Требуется юридическая проверка" if risk_level == "HIGH" else None
                    }
                    change["ai_summary"] = f"⚖️ {legal_desc}"
                    
                    if old_line and new_line:
                        change["original_html"] = self._compute_inline_diff(old_line, new_line)["left_html"]
                        change["new_html"] = self._compute_inline_diff(old_line, new_line)["right_html"]
                    
                    changes.append(change)
        
        result = self._build_result(changes, text1, text2)
        result["diff_lines"] = self._build_side_by_side(lines1, lines2)
        result["mode_info"] = {
            "name": "Юридический",
            "description": "Правовой анализ — фокус на юридических терминах и рисках"
        }
        return result
    
    # ==================== MODE: TIMELINE ====================
    def _timeline_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Timeline view - focuses on version changes summary"""
        # Use line-by-line as base
        result = self._line_by_line_diff(text1, text2)
        
        # Add timeline summary
        key_changes = []
        for c in result["changes"][:5]:
            if c.get("ai_summary"):
                key_changes.append(c["ai_summary"])
        
        result["timeline_summary"] = {
            "version": "2.0",
            "key_changes": key_changes,
            "risk_level": "RED" if result["summary"]["critical_changes"] > 0 else (
                "YELLOW" if result["summary"]["major_changes"] > 0 else "GREEN"
            ),
            "recommendation": self._generate_timeline_recommendation(result["summary"])
        }
        result["mode_info"] = {
            "name": "История",
            "description": "Обзор версий — ключевые изменения между версиями"
        }
        return result
    
    # ==================== HELPER METHODS ====================
    def _make_change(self, change_type: str, old_text: Optional[str], new_text: Optional[str], 
                     location: str, inline_diff: Optional[Dict] = None) -> Dict:
        """Create a change object"""
        severity = self._calculate_severity(old_text or "", new_text or "")
        classification = self._classify_change(old_text or "", new_text or "")
        
        change = {
            "id": f"change_{uuid.uuid4().hex[:8]}",
            "type": change_type,
            "classification": classification,
            "severity": severity,
            "location": location,
            "original_text": old_text,
            "new_text": new_text,
            "ai_summary": self._generate_summary(old_text, new_text, classification),
            "impact_score": self._calculate_impact(old_text or "", new_text or ""),
        }
        
        if inline_diff:
            change["original_html"] = inline_diff["left_html"]
            change["new_html"] = inline_diff["right_html"]
        
        return change
    
    def _compute_inline_diff(self, old_line: str, new_line: str) -> Dict[str, str]:
        """Compute word-level inline diff"""
        old_words = self._tokenize(old_line)
        new_words = self._tokenize(new_line)
        
        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        left_html = []
        right_html = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            old_part = ''.join(old_words[i1:i2])
            new_part = ''.join(new_words[j1:j2])
            
            if tag == 'equal':
                left_html.append(self._escape(old_part))
                right_html.append(self._escape(new_part))
            elif tag == 'replace':
                left_html.append(f'<mark class="diff-del">{self._escape(old_part)}</mark>')
                right_html.append(f'<mark class="diff-add">{self._escape(new_part)}</mark>')
            elif tag == 'delete':
                left_html.append(f'<mark class="diff-del">{self._escape(old_part)}</mark>')
            elif tag == 'insert':
                right_html.append(f'<mark class="diff-add">{self._escape(new_part)}</mark>')
        
        return {"left_html": ''.join(left_html), "right_html": ''.join(right_html)}
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text preserving numbers and words"""
        return re.findall(r'\d+[.,]?\d*|\w+|[^\w\s]+|\s+', text, re.UNICODE)
    
    def _build_side_by_side(self, lines1: List[str], lines2: List[str]) -> Dict[str, List]:
        """Build side-by-side diff structure with proper alignment (ComparePlus style).
        
        Algorithm:
        1. Find all matching (similar) lines between documents using LCS
        2. These matches become "anchors" - they must appear opposite each other
        3. Lines between anchors that don't match become additions/deletions with empty placeholders
        
        Key principle: Similar lines ALWAYS appear at the same row, opposite each other.
        """
        print("=" * 50)
        print("NEW DIFF ALGORITHM v2 RUNNING!")
        print(f"Lines1: {len(lines1)}, Lines2: {len(lines2)}")
        print("=" * 50)
        
        left, right = [], []
        
        # Step 1: Find matching line pairs using longest common subsequence approach
        # A line "matches" if it's identical or very similar (>60%)
        matches = self._find_line_matches(lines1, lines2)
        print(f"Found {len(matches)} matches")
        # Show matches around problematic area (lines 7-15) with similarity
        for m in matches:
            if 7 <= m[0] <= 15 or 7 <= m[1] <= 15:
                sim = difflib.SequenceMatcher(None, lines1[m[0]], lines2[m[1]]).ratio()
                print(f"  Match: line1[{m[0]}] <-> line2[{m[1]}] (sim={sim:.2f})")
                print(f"    Left:  '{lines1[m[0]][:60]}'")
                print(f"    Right: '{lines2[m[1]][:60]}'")
        
        # Step 2: Build aligned output
        left_num, right_num = 1, 1
        i, j = 0, 0  # Pointers into lines1 and lines2
        
        for (left_idx, right_idx) in matches:
            # Output all unmatched lines from left (deleted) before this match
            while i < left_idx:
                left.append({
                    "num": left_num,
                    "type": "deleted",
                    "text": lines1[i],
                    "html": f'<mark class="diff-del">{self._escape(lines1[i])}</mark>'
                })
                right.append({
                    "num": "",
                    "type": "empty",
                    "text": "",
                    "html": ""
                })
                left_num += 1
                i += 1
            
            # Output all unmatched lines from right (added) before this match
            while j < right_idx:
                left.append({
                    "num": "",
                    "type": "empty",
                    "text": "",
                    "html": ""
                })
                right.append({
                    "num": right_num,
                    "type": "added",
                    "text": lines2[j],
                    "html": f'<mark class="diff-add">{self._escape(lines2[j])}</mark>'
                })
                right_num += 1
                j += 1
            
            # Output the matched pair
            line1 = lines1[left_idx]
            line2 = lines2[right_idx]
            
            if line1 == line2:
                # Identical lines
                if self.show_full:
                    left.append({
                        "num": left_num,
                        "type": "unchanged",
                        "text": line1,
                        "html": self._escape(line1)
                    })
                    right.append({
                        "num": right_num,
                        "type": "unchanged",
                        "text": line2,
                        "html": self._escape(line2)
                    })
                    left_num += 1
                    right_num += 1
            else:
                # Similar but not identical - show as modified with inline diff
                inline = self._compute_inline_diff(line1, line2)
                left.append({
                    "num": left_num,
                    "type": "modified",
                    "text": line1,
                    "html": inline["left_html"]
                })
                right.append({
                    "num": right_num,
                    "type": "modified",
                    "text": line2,
                    "html": inline["right_html"]
                })
                left_num += 1
                right_num += 1
            
            # Move pointers past the matched lines
            i = left_idx + 1
            j = right_idx + 1
        
        # Output remaining unmatched lines from left (deleted)
        while i < len(lines1):
            left.append({
                "num": left_num,
                "type": "deleted",
                "text": lines1[i],
                "html": f'<mark class="diff-del">{self._escape(lines1[i])}</mark>'
            })
            right.append({
                "num": "",
                "type": "empty",
                "text": "",
                "html": ""
            })
            left_num += 1
            i += 1
        
        # Output remaining unmatched lines from right (added)
        while j < len(lines2):
            left.append({
                "num": "",
                "type": "empty",
                "text": "",
                "html": ""
            })
            right.append({
                "num": right_num,
                "type": "added",
                "text": lines2[j],
                "html": f'<mark class="diff-add">{self._escape(lines2[j])}</mark>'
            })
            right_num += 1
            j += 1
        
        return {"left": left, "right": right}
    
    def _find_line_matches(self, lines1: List[str], lines2: List[str]) -> List[Tuple[int, int]]:
        """Find matching lines between two documents using LCS (Longest Common Subsequence).
        
        Returns list of (idx1, idx2) pairs where lines1[idx1] matches lines2[idx2].
        Matches are ordered and non-crossing (if (a,b) and (c,d) are matches and a<c, then b<d).
        
        A line "matches" if:
        - It's identical, OR
        - Similarity ratio >= 0.7 (70%) - high threshold to avoid false matches
        """
        n1, n2 = len(lines1), len(lines2)
        if n1 == 0 or n2 == 0:
            return []
        
        THRESHOLD = 0.7  # High threshold - only match truly similar lines
        
        # Build similarity matrix: sim[i][j] = similarity score or 0 if below threshold
        sim_matrix = []
        for i, line1 in enumerate(lines1):
            row = []
            for j, line2 in enumerate(lines2):
                if line1 == line2:
                    row.append(2.0)  # Bonus for exact match
                elif line1.strip() and line2.strip():
                    sim = difflib.SequenceMatcher(None, line1, line2).ratio()
                    if sim >= THRESHOLD:
                        row.append(sim)
                    else:
                        row.append(0)
                else:
                    # Empty line matches empty line
                    if not line1.strip() and not line2.strip():
                        row.append(1.5)
                    else:
                        row.append(0)
            sim_matrix.append(row)
        
        # Use dynamic programming to find optimal alignment (LCS with weights)
        # dp[i][j] = best score for aligning lines1[:i] with lines2[:j]
        # We want to maximize total similarity while maintaining order
        
        dp = [[0.0] * (n2 + 1) for _ in range(n1 + 1)]
        parent = [[None] * (n2 + 1) for _ in range(n1 + 1)]
        
        for i in range(1, n1 + 1):
            for j in range(1, n2 + 1):
                # Option 1: Skip line from lines1 (deletion) - small penalty
                skip1_score = dp[i-1][j] - 0.01
                if skip1_score > dp[i][j]:
                    dp[i][j] = skip1_score
                    parent[i][j] = (i-1, j, 'skip1')
                
                # Option 2: Skip line from lines2 (addition) - small penalty
                skip2_score = dp[i][j-1] - 0.01
                if skip2_score > dp[i][j]:
                    dp[i][j] = skip2_score
                    parent[i][j] = (i, j-1, 'skip2')
                
                # Option 3: Match lines i-1 and j-1 (if similar enough)
                sim = sim_matrix[i-1][j-1]
                if sim > 0:
                    score = dp[i-1][j-1] + sim
                    if score > dp[i][j]:
                        dp[i][j] = score
                        parent[i][j] = (i-1, j-1, 'match')
        
        # Backtrack to find the matches
        matches = []
        i, j = n1, n2
        while i > 0 and j > 0:
            if parent[i][j] is None:
                break
            pi, pj, action = parent[i][j]
            if action == 'match':
                matches.append((i-1, j-1))
            i, j = pi, pj
        
        matches.reverse()
        return matches
    
    def _classify_change(self, old: str, new: str) -> str:
        """Classify change type"""
        old_nums = re.findall(r'\d+[.,]?\d*', old)
        new_nums = re.findall(r'\d+[.,]?\d*', new)
        if old_nums != new_nums:
            return "NUMERICAL_CHANGE"
        if re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', old + new):
            return "TEMPORAL_CHANGE"
        return "TEXT_CHANGE"
    
    def _classify_semantic_change(self, old: str, new: str) -> str:
        """Classify semantic change"""
        combined = (old + new).lower()
        if any(kw in combined for kw in ["сумм", "рубл", "платеж", "цен"]):
            return "FINANCIAL"
        if any(kw in combined for kw in ["срок", "дат", "период"]):
            return "TEMPORAL"
        if any(kw in combined for kw in ["ответственност", "штраф", "обязательств"]):
            return "LEGAL"
        return "GENERAL"
    
    def _detect_meaning_shift(self, old: str, new: str) -> Optional[str]:
        """Detect if meaning has shifted"""
        old_nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+[.,]?\d*', old) if n]
        new_nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+[.,]?\d*', new) if n]
        
        if old_nums and new_nums and old_nums != new_nums:
            diff = new_nums[0] - old_nums[0] if old_nums and new_nums else 0
            if abs(diff) > 0:
                return f"Числовое значение изменилось: {old_nums[0]} → {new_nums[0]}"
        return None
    
    def _calculate_severity(self, old: str, new: str) -> str:
        """Calculate severity"""
        combined = (old + new).lower()
        
        # Number changes
        old_nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+[.,]?\d*', old) if n]
        new_nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+[.,]?\d*', new) if n]
        if old_nums and new_nums and old_nums != new_nums:
            return "CRITICAL" if abs(new_nums[0] - old_nums[0]) / max(old_nums[0], 1) > 0.1 else "MAJOR"
        
        critical_kw = ["ответственност", "штраф", "неустойк", "расторж"]
        if any(kw in combined for kw in critical_kw):
            return "CRITICAL"
        
        major_kw = ["сумм", "рубл", "платеж", "срок"]
        if any(kw in combined for kw in major_kw):
            return "MAJOR"
        
        return "MINOR"
    
    def _calculate_impact(self, old: str, new: str) -> int:
        """Calculate impact score"""
        score = 20
        numbers = re.findall(r'\d+', old + new)
        if numbers:
            max_num = max(int(n) for n in numbers if n.isdigit() and len(n) < 10)
            if max_num > 10000:
                score += 40
            elif max_num > 1000:
                score += 25
        return min(100, score)
    
    def _generate_summary(self, old: str, new: str, classification: str) -> str:
        """Generate summary"""
        old_nums = re.findall(r'\d+[.,]?\d*', old or "")
        new_nums = re.findall(r'\d+[.,]?\d*', new or "")
        
        if classification == "NUMERICAL_CHANGE" and old_nums and new_nums:
            return f"Изменено: {old_nums[0]} → {new_nums[0]}"
        if old and not new:
            return f"Удалено: {old[:50]}..."
        if new and not old:
            return f"Добавлено: {new[:50]}..."
        return "Изменён текст"
    
    def _generate_semantic_summary(self, old: str, new: str, semantic_type: str) -> str:
        """Generate semantic summary"""
        summaries = {
            "FINANCIAL": "💰 Изменение финансовых условий",
            "TEMPORAL": "📅 Изменение сроков или дат",
            "LEGAL": "⚖️ Изменение правовых условий",
            "GENERAL": "📝 Изменение текста"
        }
        return summaries.get(semantic_type, "Изменение")
    
    def _generate_timeline_recommendation(self, summary: Dict) -> str:
        """Generate recommendation for timeline"""
        if summary["critical_changes"] > 0:
            return "⚠️ Обнаружены критические изменения — требуется детальная проверка"
        if summary["major_changes"] > 0:
            return "⚡ Обнаружены важные изменения — рекомендуется проверка"
        return "✅ Изменения незначительные"
    
    def _extract_all_numbers(self, text: str) -> Dict[str, float]:
        """Extract numbers with context"""
        numbers = {}
        patterns = [
            (r'(\d+[.,]?\d*)\s*(рубл|руб|₽)', 'сумма'),
            (r'сумм[а-я]*\s*[:\-]?\s*(\d+[.,]?\d*)', 'сумма'),
            (r'(\d+)\s*(дн[ейя]|месяц|лет)', 'срок'),
            (r'(\d+[.,]?\d*)\s*%', 'процент'),
        ]
        for pattern, ctx in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    val = float(match.group(1).replace(',', '.'))
                    key = f"{ctx}_{match.start()}"
                    numbers[key] = val
                except:
                    pass
        return numbers
    
    def _has_numbers(self, text: str) -> bool:
        """Check if text has numbers"""
        return bool(re.search(r'\d+', text))
    
    def _extract_clauses(self, text: str) -> Dict[str, List[str]]:
        """Extract clauses from document"""
        clauses = {}
        current_clause = "Общие положения"
        current_lines = []
        
        clause_patterns = [
            (r'^\s*\d+\.\s*(.+)', 'numbered'),
            (r'^(платеж|оплат|сумм)', 'ПЛАТЕЖИ'),
            (r'^(срок|дат|период)', 'СРОКИ'),
            (r'^(ответственност)', 'ОТВЕТСТВЕННОСТЬ'),
            (r'^(гарант)', 'ГАРАНТИИ'),
        ]
        
        for line in text.splitlines():
            line_lower = line.lower().strip()
            
            # Check for clause headers
            for pattern, clause_type in clause_patterns:
                if re.match(pattern, line_lower):
                    if current_lines:
                        clauses[current_clause] = current_lines
                    current_clause = clause_type if clause_type != 'numbered' else line[:50]
                    current_lines = []
                    break
            
            if line.strip():
                current_lines.append(line)
        
        if current_lines:
            clauses[current_clause] = current_lines
        
        return clauses
    
    def _escape(self, text: str) -> str:
        """Escape HTML"""
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    
    def _build_result(self, changes: List[Dict], text1: str, text2: str) -> Dict[str, Any]:
        """Build result"""
        critical = sum(1 for c in changes if c.get("severity") == "CRITICAL")
        major = sum(1 for c in changes if c.get("severity") == "MAJOR")
        minor = sum(1 for c in changes if c.get("severity") == "MINOR")
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        
        return {
            "summary": {
                "total_changes": len(changes),
                "critical_changes": critical,
                "major_changes": major,
                "minor_changes": minor,
                "similarity_score": round(similarity, 3)
            },
            "changes": changes,
            "financial_impact": []
        }
