"""
Enterprise Multi-Way Document Merge Engine
Supports 2-way, 3-way, and N-way merges with conflict detection
"""
import difflib
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter


class MergeEngine:
    """Enterprise-grade multi-way document merge engine"""
    
    def __init__(self):
        self.similarity_threshold = 0.6
    
    def merge(self, documents: List[Dict[str, Any]], strategy: str = "CONSENSUS", 
              base_version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Merge multiple documents
        
        Args:
            documents: List of {"id": str, "content": str, "name": str}
            strategy: CONSENSUS, MOST_RECENT, or MANUAL
            base_version_id: Optional base version for 3-way merge
            
        Returns:
            {
                "merged_content": str,
                "conflicts": List[Dict],
                "auto_resolved": int,
                "merge_stats": Dict
            }
        """
        if len(documents) < 2:
            return {
                "merged_content": documents[0]["content"] if documents else "", 
                "conflicts": [],
                "auto_resolved": 0,
                "merge_stats": {"total_blocks": 0, "unchanged": 0, "merged": 0}
            }
        
        # Find base if specified
        base_doc = None
        if base_version_id:
            base_doc = next((d for d in documents if d["id"] == base_version_id), None)
            if base_doc:
                documents = [d for d in documents if d["id"] != base_version_id]
        
        if len(documents) == 2 and base_doc:
            return self._three_way_merge(base_doc, documents[0], documents[1], strategy)
        elif len(documents) == 2:
            return self._two_way_merge(documents[0], documents[1], strategy)
        else:
            return self._multi_way_merge(documents, strategy, base_doc)
    
    def _two_way_merge(self, doc1: Dict, doc2: Dict, strategy: str = "MOST_RECENT") -> Dict[str, Any]:
        """Two-way merge with intelligent conflict detection"""
        lines1 = self._split_into_blocks(doc1["content"])
        lines2 = self._split_into_blocks(doc2["content"])
        
        merged_lines = []
        conflicts = []
        conflict_idx = 0
        auto_resolved = 0
        
        # In MANUAL mode, no auto-resolution - user decides everything
        allow_auto_resolve = (strategy != "MANUAL")
        
        matcher = difflib.SequenceMatcher(None, lines1, lines2, autojunk=False)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                merged_lines.extend(lines1[i1:i2])
            elif tag == 'replace':
                old_text = "\n".join(lines1[i1:i2])
                new_text = "\n".join(lines2[j1:j2])
                similarity = self._calculate_similarity(old_text, new_text)
                
                if allow_auto_resolve and similarity > 0.85:
                    merged_lines.extend(lines2[j1:j2])
                    auto_resolved += 1
                else:
                    conflicts.append({
                        "index": conflict_idx,
                        "location": f"lines {i1+1}-{i2}",
                        "type": "REPLACE",
                        "variants": [
                            {"source": doc1["name"], "content": old_text, "line_count": i2-i1},
                            {"source": doc2["name"], "content": new_text, "line_count": j2-j1}
                        ],
                        "similarity": round(similarity, 2),
                        "consensus_variant": None,
                        "analysis": self._analyze_conflict(old_text, new_text)
                    })
                    merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                    conflict_idx += 1
                    
            elif tag == 'delete':
                old_text = "\n".join(lines1[i1:i2])
                if self._is_significant_content(old_text):
                    conflicts.append({
                        "index": conflict_idx,
                        "location": f"lines {i1+1}-{i2}",
                        "type": "DELETE",
                        "variants": [
                            {"source": doc1["name"], "content": old_text, "line_count": i2-i1},
                            {"source": doc2["name"], "content": "(deleted)", "line_count": 0}
                        ],
                        "similarity": 0,
                        "consensus_variant": None,
                        "analysis": {"type": "deletion", "significance": "high"}
                    })
                    merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                    conflict_idx += 1
                elif allow_auto_resolve:
                    auto_resolved += 1
                    
            elif tag == 'insert':
                new_text = "\n".join(lines2[j1:j2])
                if self._is_significant_content(new_text):
                    if allow_auto_resolve:
                        # Auto-resolve: accept insertion
                        conflicts.append({
                            "index": conflict_idx,
                            "location": f"after line {i1}",
                            "type": "INSERT",
                            "variants": [
                                {"source": doc1["name"], "content": "(absent)", "line_count": 0},
                                {"source": doc2["name"], "content": new_text, "line_count": j2-j1}
                            ],
                            "similarity": 0,
                            "consensus_variant": 1,
                            "analysis": {"type": "addition", "significance": "medium"}
                        })
                        merged_lines.extend(lines2[j1:j2])
                    else:
                        # MANUAL mode: user must decide
                        conflicts.append({
                            "index": conflict_idx,
                            "location": f"after line {i1}",
                            "type": "INSERT",
                            "variants": [
                                {"source": doc1["name"], "content": "(absent)", "line_count": 0},
                                {"source": doc2["name"], "content": new_text, "line_count": j2-j1}
                            ],
                            "similarity": 0,
                            "consensus_variant": None,
                            "analysis": {"type": "addition", "significance": "medium"}
                        })
                        merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                        conflict_idx += 1
                else:
                    merged_lines.extend(lines2[j1:j2])
                    if allow_auto_resolve:
                        auto_resolved += 1
        
        return {
            "merged_content": "\n".join(merged_lines),
            "conflicts": conflicts,
            "auto_resolved": auto_resolved,
            "merge_stats": {
                "total_blocks": len(lines1) + len(lines2),
                "unchanged": sum(1 for tag, *_ in matcher.get_opcodes() if tag == 'equal'),
                "merged": auto_resolved,
                "conflicts": len(conflicts)
            }
        }
    
    def _three_way_merge(self, base: Dict, doc1: Dict, doc2: Dict, strategy: str = "MOST_RECENT") -> Dict[str, Any]:
        """Three-way merge using common ancestor"""
        base_lines = self._split_into_blocks(base["content"])
        lines1 = self._split_into_blocks(doc1["content"])
        lines2 = self._split_into_blocks(doc2["content"])
        
        merged_lines = []
        conflicts = []
        conflict_idx = 0
        auto_resolved = 0
        
        # In MANUAL mode, no auto-resolution
        allow_auto_resolve = (strategy != "MANUAL")
        
        matcher1 = difflib.SequenceMatcher(None, base_lines, lines1, autojunk=False)
        matcher2 = difflib.SequenceMatcher(None, base_lines, lines2, autojunk=False)
        
        changes1 = self._extract_changes(matcher1.get_opcodes(), base_lines, lines1)
        changes2 = self._extract_changes(matcher2.get_opcodes(), base_lines, lines2)
        
        i = 0
        while i < len(base_lines):
            change1 = changes1.get(i)
            change2 = changes2.get(i)
            
            if not change1 and not change2:
                merged_lines.append(base_lines[i])
                i += 1
            elif change1 and not change2:
                if allow_auto_resolve:
                    if change1["type"] == "delete":
                        i += change1["length"]
                    else:
                        merged_lines.append(change1["content"])
                        i += 1
                    auto_resolved += 1
                else:
                    # MANUAL: create conflict
                    conflicts.append({
                        "index": conflict_idx,
                        "location": f"line {i+1}",
                        "type": "THREE_WAY",
                        "variants": [
                            {"source": "Base", "content": base_lines[i], "line_count": 1},
                            {"source": doc1["name"], "content": change1.get("content", ""), "line_count": 1}
                        ],
                        "consensus_variant": None
                    })
                    merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                    conflict_idx += 1
                    i += 1
            elif change2 and not change1:
                if allow_auto_resolve:
                    if change2["type"] == "delete":
                        i += change2["length"]
                    else:
                        merged_lines.append(change2["content"])
                        i += 1
                    auto_resolved += 1
                else:
                    # MANUAL: create conflict
                    conflicts.append({
                        "index": conflict_idx,
                        "location": f"line {i+1}",
                        "type": "THREE_WAY",
                        "variants": [
                            {"source": "Base", "content": base_lines[i], "line_count": 1},
                            {"source": doc2["name"], "content": change2.get("content", ""), "line_count": 1}
                        ],
                        "consensus_variant": None
                    })
                    merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                    conflict_idx += 1
                    i += 1
            else:
                if allow_auto_resolve and change1["content"] == change2["content"]:
                    merged_lines.append(change1["content"])
                    auto_resolved += 1
                else:
                    conflicts.append({
                        "index": conflict_idx,
                        "location": f"line {i+1}",
                        "type": "THREE_WAY",
                        "variants": [
                            {"source": "Base", "content": base_lines[i], "line_count": 1},
                            {"source": doc1["name"], "content": change1["content"], "line_count": 1},
                            {"source": doc2["name"], "content": change2["content"], "line_count": 1}
                        ],
                        "similarity": self._calculate_similarity(change1["content"], change2["content"]),
                        "consensus_variant": None,
                        "analysis": self._analyze_conflict(change1["content"], change2["content"])
                    })
                    merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                    conflict_idx += 1
                i += 1
        
        return {
            "merged_content": "\n".join(merged_lines),
            "conflicts": conflicts,
            "auto_resolved": auto_resolved,
            "merge_stats": {
                "total_blocks": len(base_lines),
                "unchanged": len(base_lines) - len(changes1) - len(changes2),
                "merged": auto_resolved,
                "conflicts": len(conflicts)
            }
        }
    
    def _multi_way_merge(self, documents: List[Dict], strategy: str, 
                         base_doc: Optional[Dict] = None) -> Dict[str, Any]:
        """Multi-way merge - MOST_RECENT auto-resolves, MANUAL requires user decision"""
        all_lines = [self._split_into_blocks(doc["content"]) for doc in documents]
        
        if base_doc:
            base_lines = self._split_into_blocks(base_doc["content"])
        else:
            base_idx = max(range(len(all_lines)), key=lambda i: len(all_lines[i]))
            base_lines = all_lines[base_idx]
        
        merged_lines = []
        conflicts = []
        conflict_idx = 0
        auto_resolved = 0
        
        max_lines = max(len(lines) for lines in all_lines)
        
        for line_num in range(max_lines):
            variants = {}
            for i, lines in enumerate(all_lines):
                if line_num < len(lines):
                    line = lines[line_num]
                    if line not in variants:
                        variants[line] = []
                    variants[line].append(i)
            
            if len(variants) == 1:
                # All documents agree - no conflict
                merged_lines.append(list(variants.keys())[0])
            elif strategy == "MOST_RECENT":
                # Auto-resolve: use most recent document's version
                last_doc_lines = all_lines[-1]
                if line_num < len(last_doc_lines):
                    merged_lines.append(last_doc_lines[line_num])
                else:
                    merged_lines.append(base_lines[line_num] if line_num < len(base_lines) else "")
                auto_resolved += 1
                
            else:
                # MANUAL mode: user must decide every difference
                conflicts.append({
                    "index": conflict_idx,
                    "location": f"line {line_num + 1}",
                    "type": "MANUAL",
                    "variants": [
                        {
                            "source": documents[indices[0]]["name"],
                            "content": line,
                            "line_count": 1
                        }
                        for line, indices in variants.items()
                    ],
                    "consensus_variant": None,
                    "analysis": {"type": "manual_review_required"}
                })
                merged_lines.append(f"<<<CONFLICT_{conflict_idx}>>>")
                conflict_idx += 1
        
        return {
            "merged_content": "\n".join(merged_lines),
            "conflicts": conflicts,
            "auto_resolved": auto_resolved,
            "merge_stats": {
                "total_blocks": max_lines,
                "documents_count": len(documents),
                "merged": auto_resolved,
                "conflicts": len(conflicts)
            }
        }
    
    def apply_resolutions(self, merged_content: str, conflicts: List[Dict], 
                          resolutions: List[Dict]) -> str:
        """Apply conflict resolutions to merged content"""
        result = merged_content
        
        for resolution in resolutions:
            conflict_idx = resolution["conflict_index"]
            chosen_variant = resolution["chosen_variant_index"]
            
            conflict = next((c for c in conflicts if c["index"] == conflict_idx), None)
            if conflict and chosen_variant < len(conflict["variants"]):
                replacement = conflict["variants"][chosen_variant]["content"]
                if replacement in ["(deleted)", "(absent)"]:
                    replacement = ""
                result = result.replace(f"<<<CONFLICT_{conflict_idx}>>>", replacement)
        
        return result
    
    def preview_merge(self, documents: List[Dict], strategy: str) -> Dict[str, Any]:
        """Preview merge without saving"""
        result = self.merge(documents, strategy)
        
        result["preview"] = True
        result["estimated_conflicts"] = len(result["conflicts"])
        result["can_auto_merge"] = len(result["conflicts"]) == 0
        result["recommendation"] = self._get_merge_recommendation(result)
        
        return result
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Split text into logical blocks"""
        if not text:
            return []
        return text.splitlines()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts"""
        if not text1 or not text2:
            return 0.0
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _is_significant_content(self, text: str) -> bool:
        """Check if content is significant"""
        cleaned = re.sub(r'\s+', '', text)
        return len(cleaned) > 10
    
    def _analyze_conflict(self, text1: str, text2: str) -> Dict[str, Any]:
        """Analyze conflict to help user resolve it"""
        analysis = {"type": "unknown", "significance": "medium"}
        
        nums1 = set(re.findall(r'\d+[.,]?\d*', text1))
        nums2 = set(re.findall(r'\d+[.,]?\d*', text2))
        if nums1 != nums2:
            analysis["type"] = "numerical"
            analysis["significance"] = "high"
            analysis["old_numbers"] = list(nums1)
            analysis["new_numbers"] = list(nums2)
        
        dates1 = set(re.findall(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', text1))
        dates2 = set(re.findall(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', text2))
        if dates1 != dates2:
            analysis["type"] = "temporal"
            analysis["significance"] = "high"
        
        legal_terms = ["liability", "penalty", "fine", "obligation", "right"]
        if any(term in (text1 + text2).lower() for term in legal_terms):
            analysis["type"] = "legal"
            analysis["significance"] = "critical"
        
        return analysis
    
    def _extract_changes(self, opcodes: List, base: List[str], modified: List[str]) -> Dict[int, Dict]:
        """Extract changes from opcodes for 3-way merge"""
        changes = {}
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'replace':
                for idx in range(i1, i2):
                    offset = idx - i1
                    if j1 + offset < j2:
                        changes[idx] = {"type": "replace", "content": modified[j1 + offset], "length": 1}
            elif tag == 'delete':
                for idx in range(i1, i2):
                    changes[idx] = {"type": "delete", "content": "", "length": i2 - i1}
            elif tag == 'insert':
                if i1 > 0:
                    changes[i1 - 1] = {"type": "insert", "content": "\n".join(modified[j1:j2]), "length": j2 - j1}
        return changes
    
    def _get_merge_recommendation(self, result: Dict) -> str:
        """Get merge recommendation based on analysis"""
        conflicts = result["conflicts"]
        
        if not conflicts:
            return "Auto-merge possible without conflicts"
        
        critical = sum(1 for c in conflicts if c.get("analysis", {}).get("significance") == "critical")
        high = sum(1 for c in conflicts if c.get("analysis", {}).get("significance") == "high")
        
        if critical > 0:
            return f"Found {critical} critical conflicts - manual review required"
        elif high > 0:
            return f"Found {high} important conflicts - review recommended"
        else:
            return f"Found {len(conflicts)} conflicts to resolve"
