"""
Enterprise Risk Analyzer for Contract Documents
Multi-dimensional risk assessment with AI integration
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class RiskAnalyzer:
    """Comprehensive risk analysis for legal documents"""
    
    # Risk thresholds
    THRESHOLDS = {
        "payment_days": {"critical": 30, "major": 60},
        "penalty_percent": {"critical": 5, "major": 2},
        "liability_cap_ratio": {"critical": 2, "major": 1},
        "amount_rub": {"critical": 1000000, "major": 500000},
        "amount_usd": {"critical": 10000, "major": 5000},
        "notice_days": {"critical": 7, "major": 14},
        "deadline_days": {"critical": 14, "major": 30},
    }
    
    # Risk weights for overall score
    DIMENSION_WEIGHTS = {
        "financial": 0.3,
        "temporal": 0.2,
        "legal": 0.35,
        "operational": 0.15
    }
    
    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """Perform comprehensive risk analysis on document text"""
        risks = []
        
        # Financial risks
        risks.extend(self._analyze_financial_risks(text))
        
        # Temporal risks
        risks.extend(self._analyze_temporal_risks(text))
        
        # Legal risks
        risks.extend(self._analyze_legal_risks(text))
        
        # Operational risks
        risks.extend(self._analyze_operational_risks(text))
        
        # Compliance risks
        risks.extend(self._analyze_compliance_risks(text))
        
        # Contractual risks
        risks.extend(self._analyze_contractual_risks(text))
        
        return risks
    
    def calculate_overall_score(self, risks: List[Dict]) -> Dict[str, Any]:
        """Calculate overall risk score and level"""
        if not risks:
            return {"score": 0, "level": "GREEN", "trend": "stable"}
        
        # Calculate weighted score by dimension
        dimension_scores = {}
        for risk in risks:
            dim = risk.get("dimension", "other")
            if dim not in dimension_scores:
                dimension_scores[dim] = []
            dimension_scores[dim].append(risk["score"])
        
        # Average per dimension
        weighted_sum = 0
        total_weight = 0
        for dim, scores in dimension_scores.items():
            avg_score = sum(scores) / len(scores)
            weight = self.DIMENSION_WEIGHTS.get(dim, 0.1)
            weighted_sum += avg_score * weight
            total_weight += weight
        
        overall_score = int(weighted_sum / total_weight) if total_weight > 0 else 0
        
        # Determine level
        if overall_score <= 30:
            level = "GREEN"
        elif overall_score <= 70:
            level = "YELLOW"
        else:
            level = "RED"
        
        return {
            "score": overall_score,
            "level": level,
            "dimension_breakdown": {dim: int(sum(s)/len(s)) for dim, s in dimension_scores.items()},
            "risk_count": {"total": len(risks), "red": sum(1 for r in risks if r["level"] == "RED"),
                          "yellow": sum(1 for r in risks if r["level"] == "YELLOW"),
                          "green": sum(1 for r in risks if r["level"] == "GREEN")}
        }
    
    def compare_risks(self, risks1: List[Dict], risks2: List[Dict]) -> Dict[str, Any]:
        """Compare risks between two document versions"""
        score1 = self.calculate_overall_score(risks1)
        score2 = self.calculate_overall_score(risks2)
        
        score_change = score2["score"] - score1["score"]
        
        # Find new, resolved, and changed risks
        types1 = {r["type"] for r in risks1}
        types2 = {r["type"] for r in risks2}
        
        new_types = types2 - types1
        resolved_types = types1 - types2
        
        return {
            "score_before": score1["score"],
            "score_after": score2["score"],
            "score_change": score_change,
            "level_before": score1["level"],
            "level_after": score2["level"],
            "trend": "increased" if score_change > 10 else ("decreased" if score_change < -10 else "stable"),
            "new_risks": [r for r in risks2 if r["type"] in new_types],
            "resolved_risks": [r for r in risks1 if r["type"] in resolved_types],
            "risk_count_change": len(risks2) - len(risks1)
        }
    
    def _analyze_financial_risks(self, text: str) -> List[Dict]:
        """Analyze financial risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for large amounts (RUB)
        amount_pattern_rub = r'(\d[\d\s]*[\.,]?\d*)\s*(рубл|руб|RUB|₽)'
        matches = re.findall(amount_pattern_rub, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match[0].replace(' ', '').replace(',', '.'))
                if amount > self.THRESHOLDS["amount_rub"]["critical"]:
                    risks.append(self._create_risk(
                        "financial", "large_amount_rub", 75, "RED",
                        f"Large amount: {amount:,.0f} RUB",
                        "High amount increases financial exposure",
                        "Consider payment schedule or guarantees"
                    ))
                elif amount > self.THRESHOLDS["amount_rub"]["major"]:
                    risks.append(self._create_risk(
                        "financial", "significant_amount_rub", 50, "YELLOW",
                        f"Significant amount: {amount:,.0f} RUB",
                        "Amount requires attention",
                        "Review payment terms"
                    ))
            except ValueError:
                pass
        
        # Check for USD/EUR amounts
        amount_pattern_fx = r'(\d[\d\s]*[\.,]?\d*)\s*(USD|EUR|\$|€)'
        fx_matches = re.findall(amount_pattern_fx, text, re.IGNORECASE)
        for match in fx_matches:
            try:
                amount = float(match[0].replace(' ', '').replace(',', '.'))
                if amount > self.THRESHOLDS["amount_usd"]["critical"]:
                    risks.append(self._create_risk(
                        "financial", "foreign_currency_exposure", 70, "RED",
                        f"Foreign currency amount: {amount:,.0f} {match[1]}",
                        "Currency risk exposure without hedge",
                        "Consider currency hedging or RUB settlement"
                    ))
            except ValueError:
                pass
        
        # Check for penalties
        penalty_patterns = [
            r'(?:штраф|неустойка|пеня)[^\d]*(\d+[\.,]?\d*)\s*%',
            r'(\d+[\.,]?\d*)\s*%\s*(?:за каждый день|в день|per day)',
        ]
        for pattern in penalty_patterns:
            penalty_matches = re.findall(pattern, text, re.IGNORECASE)
            for match in penalty_matches:
                try:
                    pct = float(match.replace(',', '.'))
                    if pct > self.THRESHOLDS["penalty_percent"]["critical"]:
                        risks.append(self._create_risk(
                            "financial", "high_penalty_rate", 85, "RED",
                            f"High penalty rate: {pct}%",
                            "Penalty can significantly increase costs",
                            "Negotiate lower penalty rate or cap"
                        ))
                    elif pct > self.THRESHOLDS["penalty_percent"]["major"]:
                        risks.append(self._create_risk(
                            "financial", "moderate_penalty_rate", 55, "YELLOW",
                            f"Moderate penalty rate: {pct}%",
                            "Penalty rate above market average",
                            "Consider negotiating"
                        ))
                except ValueError:
                    pass
        
        # Check for advance payment requirements
        if re.search(r'(предоплат|аванс|prepay)', text_lower):
            advance_match = re.search(r'(предоплат|аванс)[^\d]*(\d+)\s*%', text, re.IGNORECASE)
            if advance_match:
                try:
                    pct = int(advance_match.group(2))
                    if pct > 50:
                        risks.append(self._create_risk(
                            "financial", "high_advance_payment", 60, "YELLOW",
                            f"High advance payment: {pct}%",
                            "Large advance increases counterparty risk",
                            "Request bank guarantee or reduce advance"
                        ))
                except ValueError:
                    pass
        
        # Check for no payment cap on penalties
        if re.search(r'(штраф|неустойк|пен)', text_lower):
            if not re.search(r'(не более|не превышает|максимум|cap|limit)', text_lower):
                risks.append(self._create_risk(
                    "financial", "uncapped_penalties", 75, "RED",
                    "Penalties without cap",
                    "Unlimited penalties can exceed contract value",
                    "Add penalty cap (e.g., 10% of contract value)"
                ))
        
        return risks
    
    def _analyze_temporal_risks(self, text: str) -> List[Dict]:
        """Analyze temporal/deadline risks"""
        risks = []
        text_lower = text.lower()
        
        # Check payment days
        days_patterns = [
            r'(?:оплата|платеж|payment)[^\d]*(\d+)\s*(?:календарных|рабочих|business)?\s*дн',
            r'(\d+)\s*(?:календарных|рабочих)?\s*дн[яейь].*(?:оплат|платеж)',
        ]
        for pattern in days_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    days = int(match)
                    if days < self.THRESHOLDS["payment_days"]["critical"]:
                        risks.append(self._create_risk(
                            "temporal", "short_payment_term", 70, "RED",
                            f"Short payment term: {days} days",
                            "Short payment term creates cash flow pressure",
                            "Negotiate longer payment term (60-90 days)"
                        ))
                    elif days < self.THRESHOLDS["payment_days"]["major"]:
                        risks.append(self._create_risk(
                            "temporal", "tight_payment_term", 45, "YELLOW",
                            f"Tight payment term: {days} days",
                            "Payment term below standard",
                            "Consider negotiating"
                        ))
                except ValueError:
                    pass
        
        # Check for tight deadlines
        deadline_pattern = r'(?:срок|deadline|выполнен|deliver)[^\d]*(\d+)\s*(?:календарных|рабочих)?\s*дн'
        deadline_matches = re.findall(deadline_pattern, text, re.IGNORECASE)
        for match in deadline_matches:
            try:
                days = int(match)
                if days < self.THRESHOLDS["deadline_days"]["critical"]:
                    risks.append(self._create_risk(
                        "temporal", "tight_deadline", 65, "YELLOW",
                        f"Tight deadline: {days} days",
                        "Short timeline increases delivery risk",
                        "Assess feasibility and add buffer"
                    ))
            except ValueError:
                pass
        
        # Check notice period
        notice_pattern = r'(?:уведомлен|извещен|notice)[^\d]*(\d+)\s*(?:календарных|рабочих)?\s*дн'
        notice_matches = re.findall(notice_pattern, text, re.IGNORECASE)
        for match in notice_matches:
            try:
                days = int(match)
                if days < self.THRESHOLDS["notice_days"]["critical"]:
                    risks.append(self._create_risk(
                        "temporal", "short_notice_period", 55, "YELLOW",
                        f"Short notice period: {days} days",
                        "Short notice limits response time",
                        "Negotiate longer notice period"
                    ))
            except ValueError:
                pass
        
        # Check for auto-renewal without opt-out
        if re.search(r'(автоматическ|automatic).*(продлен|renew|пролонг)', text_lower):
            if not re.search(r'(отказ|opt.?out|письменн.*уведомлен)', text_lower):
                risks.append(self._create_risk(
                    "temporal", "auto_renewal_no_optout", 50, "YELLOW",
                    "Auto-renewal without clear opt-out",
                    "May result in unwanted contract extension",
                    "Add clear opt-out mechanism"
                ))
        
        return risks
    
    def _analyze_legal_risks(self, text: str) -> List[Dict]:
        """Analyze legal risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for unlimited liability
        if 'ответственност' in text_lower or 'liability' in text_lower:
            if not re.search(r'(ограничен|limit|cap|не более|не превышает)', text_lower):
                risks.append(self._create_risk(
                    "legal", "unlimited_liability", 90, "RED",
                    "No liability limitation",
                    "Unlimited liability creates significant legal exposure",
                    "Add liability cap (e.g., contract value)"
                ))
        
        # Check for indemnification
        if re.search(r'(индемниф|indemnif|возмещ.*убытк)', text_lower):
            if not re.search(r'(взаимн|mutual|обоюдн)', text_lower):
                risks.append(self._create_risk(
                    "legal", "one_sided_indemnification", 70, "RED",
                    "One-sided indemnification",
                    "Asymmetric indemnification increases risk",
                    "Negotiate mutual indemnification"
                ))
        
        # Check for arbitration clause
        if not re.search(r'(арбитраж|arbitrat|третейск)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_arbitration", 40, "YELLOW",
                "No arbitration clause",
                "Court proceedings may be more costly",
                "Consider adding arbitration clause"
            ))
        
        # Check for foreign governing law
        foreign_law_patterns = [
            r'право\s+(англии|сша|германии|великобритании|england|usa|germany)',
            r'(english|american|german)\s+law',
            r'governed by.*law of\s+(england|usa|germany)',
        ]
        for pattern in foreign_law_patterns:
            if re.search(pattern, text_lower):
                risks.append(self._create_risk(
                    "legal", "foreign_governing_law", 65, "YELLOW",
                    "Foreign governing law",
                    "Foreign law increases complexity and costs",
                    "Consider Russian law or neutral jurisdiction"
                ))
                break
        
        # Check for IP rights
        if re.search(r'(интеллектуальн.*собственност|intellectual.*property|IP)', text, re.IGNORECASE):
            if not re.search(r'(принадлежат|переходят|остаются|ownership|belongs|transfer)', text_lower):
                risks.append(self._create_risk(
                    "legal", "unclear_ip_rights", 55, "YELLOW",
                    "Unclear IP ownership",
                    "Ambiguous IP rights may lead to disputes",
                    "Clarify IP ownership explicitly"
                ))
        
        # Check for non-compete
        if re.search(r'(неконкуренц|non.?compete|запрет.*конкур)', text_lower):
            duration_match = re.search(r'(\d+)\s*(год|лет|year)', text_lower)
            if duration_match:
                years = int(duration_match.group(1))
                if years > 2:
                    risks.append(self._create_risk(
                        "legal", "long_non_compete", 60, "YELLOW",
                        f"Long non-compete period: {years} years",
                        "Extended non-compete limits business flexibility",
                        "Negotiate shorter period or narrower scope"
                    ))
        
        # Check for termination rights
        if not re.search(r'(расторж|terminat|прекращ)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_termination_clause", 75, "RED",
                "No termination clause",
                "Unable to exit contract may trap in unfavorable terms",
                "Add termination for convenience with notice"
            ))
        
        return risks
    
    def _analyze_operational_risks(self, text: str) -> List[Dict]:
        """Analyze operational risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for insurance requirements
        if re.search(r'(страхован|insurance)', text_lower):
            if not re.search(r'(страхов|insurance).*(\d+|сумм|amount)', text_lower):
                risks.append(self._create_risk(
                    "operational", "vague_insurance", 35, "GREEN",
                    "Insurance requirement without specifics",
                    "Unclear insurance requirements",
                    "Specify insurance type and amount"
                ))
        
        # Check for force majeure
        if not re.search(r'(форс.?мажор|force.?majeure|непреодолим.*сил)', text_lower):
            risks.append(self._create_risk(
                "operational", "no_force_majeure", 50, "YELLOW",
                "No force majeure clause",
                "No protection from unforeseeable events",
                "Add comprehensive force majeure clause"
            ))
        
        # Check for SLA requirements
        if re.search(r'(SLA|уровень.*обслуживания|service.*level)', text, re.IGNORECASE):
            if not re.search(r'\d+\s*%|\d+\s*час|\d+\s*hour', text):
                risks.append(self._create_risk(
                    "operational", "vague_sla", 45, "YELLOW",
                    "SLA without specific metrics",
                    "Vague SLA may lead to disputes",
                    "Define specific uptime/response metrics"
                ))
        
        # Check for audit rights
        if not re.search(r'(аудит|audit|проверк.*документ)', text_lower):
            risks.append(self._create_risk(
                "operational", "no_audit_rights", 40, "YELLOW",
                "No audit rights",
                "Unable to verify counterparty compliance",
                "Add audit rights clause"
            ))
        
        # Check for subcontracting
        if re.search(r'(субподряд|subcontract|привлечен.*третьих)', text_lower):
            if not re.search(r'(согласован|approval|письменн.*согласи)', text_lower):
                risks.append(self._create_risk(
                    "operational", "uncontrolled_subcontracting", 50, "YELLOW",
                    "Subcontracting without approval requirement",
                    "Quality may suffer with unknown subcontractors",
                    "Require written approval for subcontracting"
                ))
        
        return risks
    
    def _analyze_compliance_risks(self, text: str) -> List[Dict]:
        """Analyze compliance and regulatory risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for personal data handling
        if re.search(r'(персональн.*данн|personal.*data|ПДн|PII)', text, re.IGNORECASE):
            if not re.search(r'(152.?ФЗ|GDPR|защит.*данн|data.*protection)', text_lower):
                risks.append(self._create_risk(
                    "legal", "no_data_protection", 70, "RED",
                    "Personal data without protection clause",
                    "Data breach may result in regulatory penalties",
                    "Add data protection compliance clause"
                ))
        
        # Check for anti-corruption
        if not re.search(r'(антикоррупц|anti.?corrupt|anti.?brib|взятк)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_anti_corruption", 45, "YELLOW",
                "No anti-corruption clause",
                "Missing compliance with anti-corruption laws",
                "Add anti-corruption representations"
            ))
        
        # Check for sanctions
        if not re.search(r'(санкци|sanction)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_sanctions_clause", 40, "YELLOW",
                "No sanctions compliance clause",
                "Potential sanctions violation risk",
                "Add sanctions compliance clause"
            ))
        
        return risks
    
    def _analyze_contractual_risks(self, text: str) -> List[Dict]:
        """Analyze general contractual risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for assignment restrictions
        if not re.search(r'(уступ|assign|передач.*прав)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_assignment_restriction", 35, "GREEN",
                "No assignment restriction",
                "Contract may be assigned to unknown party",
                "Add assignment restriction clause"
            ))
        
        # Check for confidentiality
        if not re.search(r'(конфиденциальн|confidential|NDA|неразглашен)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_confidentiality", 50, "YELLOW",
                "No confidentiality clause",
                "Sensitive information may be disclosed",
                "Add confidentiality obligations"
            ))
        
        # Check for dispute resolution
        if not re.search(r'(спор|dispute|разногласи)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_dispute_resolution", 45, "YELLOW",
                "No dispute resolution mechanism",
                "Unclear how to resolve disagreements",
                "Add dispute resolution procedure"
            ))
        
        # Check for entire agreement clause
        if not re.search(r'(полн.*соглашен|entire.*agreement|исчерпывающ)', text_lower):
            risks.append(self._create_risk(
                "legal", "no_entire_agreement", 30, "GREEN",
                "No entire agreement clause",
                "Prior agreements may still apply",
                "Add entire agreement clause"
            ))
        
        return risks
    
    def _create_risk(self, dimension: str, risk_type: str, score: int, level: str,
                     description: str, business_context: str, recommendation: str) -> Dict[str, Any]:
        """Create a standardized risk object"""
        return {
            "dimension": dimension,
            "type": risk_type,
            "score": score,
            "level": level,
            "description": description,
            "business_context": business_context,
            "recommendation": recommendation
        }
