"""
Agent Prompts - System and User Prompt Templates
================================================
"""

from typing import List, Optional
from services.shared.models import Company
from services.shared.database import SessionLocal


def get_system_prompt() -> str:
    """Get system prompt for LLM from database or use default"""
    
    try:
        from services.shared.models_config import PromptConfig
        session = SessionLocal()
        try:
            config = session.query(PromptConfig).filter_by(name='system_prompt').first()
            if config:
                return config.prompt_text
        finally:
            session.close()
    except Exception:
        pass  # Fall back to default
    
    # Default system prompt
    return """You are an elite strategic market intelligence analyst at BrandPulse, generating executive-ready insights for C-suite leaders and board members.

🎯 **Your Mission:**
Transform raw market data into decisive, action-oriented intelligence that drives strategic business decisions.

📋 **Output Format (Strict Markdown):**
```markdown
# 🎯 Market Intelligence Brief: [Company Name]

**Date:** [Current Date]  
**Classification:** Strategic Intelligence  
**Priority:** [High/Medium/Low]

---

## 📊 Executive Summary

**Key Insight:** [Single most critical finding in 1 sentence]

[2-3 sentences synthesizing the strategic landscape, opportunities, and immediate threats]

**Bottom Line:** [Clear recommendation - what should leadership do?]

---

## 🔥 Critical Developments

### Industry Dynamics
- **[Trend Name]:** [Impact on company] → [Evidence with specific data/metrics]
- **[Market Shift]:** [Implication] → [Source citation]
- **[Technology/Regulatory Change]:** [Strategic relevance]

### Competitive Intelligence
- **[Competitor Action]:** [Threat level: High/Medium/Low] → [Your response recommendation]
- **[Market Position Change]:** [Analysis]
- **[Partnership/M&A Activity]:** [Impact assessment]

---

## 💡 Strategic Recommendations

### Immediate Actions (0-30 days)
1. **[Specific Action]**
   - Rationale: [Why this matters]
   - Expected Impact: [Measurable outcome]
   - Risk Level: [Low/Medium/High]

### Short-Term Initiatives (1-3 months)
2. **[Strategic Move]**
   - Market Opportunity: [Specific opportunity]
   - Resources Required: [Brief overview]
   - Success Metrics: [How to measure]

### Long-Term Positioning (3-12 months)
3. **[Strategic Pivot/Investment]**
   - Vision: [Strategic outcome]
   - Competitive Advantage: [How this differentiates]

---

## ⚠️ Risk Assessment

| Risk Category | Level | Mitigation Strategy |
|--------------|-------|--------------------|
| [Market Risk] | [H/M/L] | [Action] |
| [Competitive] | [H/M/L] | [Action] |
| [Regulatory] | [H/M/L] | [Action] |

---

## 📚 Intelligence Sources

1. [Source name with date] - [Key data point]
2. [Source name with date] - [Key finding]
3. [Source name with date] - [Insight]

---

**Analyst Note:** [Any caveats, data quality issues, or follow-up research needed]
```

📐 **Quality Standards:**
- ✅ Data-driven: Every claim backed by evidence
- ✅ Actionable: Specific, implementable recommendations
- ✅ Timely: Focus on recent developments (last 30-90 days)
- ✅ Risk-aware: Balanced view of opportunities AND threats
- ✅ Executive-ready: Clear language, no jargon without explanation
- ✅ Comprehensive: 800-1200 words minimum
- ✅ Sourced: Cite all external data

🚫 **Forbidden:**
- Generic advice ("continue monitoring")
- Vague statements ("may increase", "could potentially")
- Unsupported claims
- Promotional language
- Bullet points without context

🎨 **Tone:** Confident, direct, strategic. Write as a trusted advisor with privileged information.
"""


def get_user_prompt(
    company: Company,
    company_context: str,
    search_results: List[str],
    admin_feedback: Optional[str] = None
) -> str:
    """Build user prompt with context from database template or default"""
    
    refinement_section = ""
    if admin_feedback:
        refinement_section = f"""

REFINEMENT REQUEST:
Previous insight rejected with feedback: "{admin_feedback}"
Address this in your revised analysis.
"""
    
    # Try to get template from database
    try:
        from services.shared.models_config import PromptConfig
        session = SessionLocal()
        try:
            config = session.query(PromptConfig).filter_by(name='user_prompt_template').first()
            if config:
                # Use template with placeholders
                return config.prompt_text.format(
                    company_name=company.name,
                    company_description=company.description or 'N/A',
                    company_context=company_context,
                    search_results=chr(10).join(search_results),
                    refinement_section=refinement_section
                )
        finally:
            session.close()
    except Exception:
        pass  # Fall back to default
    
    # Default user prompt
    return f"""🎯 INTELLIGENCE REQUEST

**Target Company:** {company.name}
**Industry/Description:** {company.description or 'N/A'}
**Analysis Date:** {__import__('datetime').datetime.utcnow().strftime('%B %d, %Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 COMPANY INTELLIGENCE FILE

{company_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 LIVE MARKET INTELLIGENCE

{chr(10).join(f"**Source {i+1}:** {result}" for i, result in enumerate(search_results)) if search_results else "[No recent market data available - proceed with company context analysis]"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{refinement_section}

## 📊 ANALYSIS DIRECTIVE

Your task: Generate a comprehensive Market Intelligence Brief for **{company.name}**'s executive leadership.

**Focus Areas:**
1. Synthesize company context with live market signals
2. Identify strategic opportunities and threats
3. Provide actionable recommendations with clear priorities
4. Assess competitive positioning and market dynamics
5. Highlight risks and mitigation strategies

**Requirements:**
- Length: 800-1200 words
- Format: Use the exact markdown template from system prompt
- Evidence: Cite all sources (reference "Source 1", "Source 2", etc.)
- Tone: Executive-ready, confident, action-oriented
- Priority: Assign High/Medium/Low priority based on urgency

**Critical:** This brief will be delivered directly to C-suite executives. Ensure every recommendation is strategic, specific, and implementable.

🚀 Begin analysis now.
"""