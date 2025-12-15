"""
Settings Page
============
Configure LLM prompts and system settings
"""

import streamlit as st
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.shared.database import SessionLocal
from services.shared.models_config import PromptConfig
from services.dashboard.utils.auth import check_authentication

# Default prompts (matching prompts.py)
DEFAULT_SYSTEM_PROMPT = """You are an elite strategic market intelligence analyst at BrandPulse, generating executive-ready insights for C-suite leaders and board members.

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

DEFAULT_USER_TEMPLATE = """🎯 INTELLIGENCE REQUEST

**Target Company:** {company_name}
**Industry/Description:** {company_description}
**Analysis Date:** {current_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 COMPANY INTELLIGENCE FILE

{company_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 LIVE MARKET INTELLIGENCE

{search_results}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{refinement_section}

## 📊 ANALYSIS DIRECTIVE

Your task: Generate a comprehensive Market Intelligence Brief for **{company_name}**'s executive leadership.

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


def show_settings_page():
    """Display settings and configuration"""
    
    if not check_authentication():
        st.error("🔒 Access Denied. Please login first.")
        st.stop()
    
    st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1>Settings</h1>
            <p style='color: #64748b; font-size: 1rem;'>
                Configure LLM prompts and system settings
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    session = SessionLocal()
    
    try:
        # Get or create prompts
        system_prompt_config = session.query(PromptConfig).filter_by(name="system_prompt").first()
        user_template_config = session.query(PromptConfig).filter_by(name="user_prompt_template").first()
        
        if not system_prompt_config:
            system_prompt_config = PromptConfig(
                name="system_prompt",
                prompt_text=DEFAULT_SYSTEM_PROMPT,
                description="System prompt for the AI agent"
            )
            session.add(system_prompt_config)
            session.commit()
        
        if not user_template_config:
            user_template_config = PromptConfig(
                name="user_prompt_template",
                prompt_text=DEFAULT_USER_TEMPLATE,
                description="Template for processing company data"
            )
            session.add(user_template_config)
            session.commit()
        
        # System Prompt
        st.markdown("<h2>🤖 System Prompt</h2>", unsafe_allow_html=True)
        st.markdown("""<p style='color: #64748b; margin-bottom: 1rem;'>
            Defines the AI agent's role, output format, and quality standards. 
            This is the foundation of every insight generated.
        </p>""", unsafe_allow_html=True)
        
        system_prompt = st.text_area(
            "System Prompt",
            value=system_prompt_config.prompt_text,
            height=400,
            label_visibility="collapsed",
            help="This prompt defines how the AI agent behaves and formats insights"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # User Template
        st.markdown("<h2>📝 User Prompt Template</h2>", unsafe_allow_html=True)
        st.markdown("""<p style='color: #64748b; margin-bottom: 1rem;'>
            Template for processing company data. Available placeholders:<br>
            <code>{company_name}</code>, <code>{company_description}</code>, 
            <code>{company_context}</code>, <code>{search_results}</code>, 
            <code>{refinement_section}</code>
        </p>""", unsafe_allow_html=True)
        
        user_template = st.text_area(
            "User Template",
            value=user_template_config.prompt_text,
            height=350,
            label_visibility="collapsed",
            help="Template with placeholders for company-specific data"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Save/Reset buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            if st.button("💾 Save", type="primary", use_container_width=True):
                try:
                    system_prompt_config.prompt_text = system_prompt
                    user_template_config.prompt_text = user_template
                    session.commit()
                    st.toast("✅ Settings saved successfully!", icon="✅")
                    st.success("✅ **Settings Saved!** Changes will apply to next insight generation.")
                    # Don't rerun immediately - let user see the confirmation
                except Exception as e:
                    st.toast(f"❌ Save failed: {str(e)}", icon="❌")
                    st.error(f"❌ **Error saving settings:** {e}")
        
        with col2:
            if st.button("🔄 Reset", use_container_width=True):
                try:
                    system_prompt_config.prompt_text = DEFAULT_SYSTEM_PROMPT
                    user_template_config.prompt_text = DEFAULT_USER_TEMPLATE
                    session.commit()
                    st.toast("🔄 Reset to defaults!", icon="🔄")
                    st.success("✅ **Reset Complete!** Prompts restored to defaults.")
                    st.rerun()
                except Exception as e:
                    st.toast(f"❌ Reset failed: {str(e)}", icon="❌")
                    st.error(f"❌ **Error resetting settings:** {e}")
        
        with col3:
            st.markdown("<div style='padding-top: 0.5rem; color: #64748b; font-size: 0.9rem;'>Last updated: {}</div>".format(
                system_prompt_config.updated_at.strftime('%Y-%m-%d %H:%M') if hasattr(system_prompt_config, 'updated_at') and system_prompt_config.updated_at else 'Never'
            ), unsafe_allow_html=True)
        
        # Info box
        st.info("""💡 **Tip:** After saving, new insights will use the updated prompts. 
        Existing insights remain unchanged. Test your prompts with a new generation!""")
    
    finally:
        session.close()
