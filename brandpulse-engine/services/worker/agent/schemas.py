"""
Pydantic Output Schemas
=======================
Structured output models for LLM calls using with_structured_output().
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ContentIdea(BaseModel):
    """A single structured content idea."""
    hook: str = Field(description="Opening line — the first sentence that grabs attention")
    body: str = Field(description="2-3 sentences expanding on the hook with substance")
    cta: str = Field(description="Call to action — what should the reader do or think?")
    platform: Literal["linkedin", "instagram", "twitter"] = Field(
        description="Best platform for this idea"
    )
    implication_type: Literal["product", "audience", "hiring", "industry"] = Field(
        description="What angle this idea explores"
    )

    @property
    def full_content(self) -> str:
        """Combine hook, body, and CTA into publishable post."""
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}"


class IdeaBatch(BaseModel):
    """Batch of 3-5 content ideas generated in a single LLM call."""
    ideas: List[ContentIdea] = Field(
        description="List of 3-5 distinct content ideas, each exploring a different implication"
    )


# ---------------------------------------------------------------------------
# Phase 2 Schemas
# ---------------------------------------------------------------------------

class CompanyProfileSchema(BaseModel):
    """Structured company profile extracted from PDF text."""
    space: str = Field(description="Industry or market the company operates in")
    audience: str = Field(description="Primary target audience (who buys/uses their product)")
    content_fit: str = Field(
        description="Comma-separated content topics that resonate with their brand (e.g. 'AI tools, remote work, startup culture')"
    )
    brand_voice: str = Field(
        description="Communication tone (e.g. 'conversational, data-driven, bold, technical')"
    )
    key_differentiators: str = Field(
        description="1-2 sentences: what makes this company genuinely different"
    )
    region: str = Field(
        default="India",
        description="Country or region the company primarily operates in (e.g. 'India', 'US', 'UK')"
    )


class AngleSelection(BaseModel):
    """Chosen content angle for this run."""
    category: str = Field(description="The angle category from the taxonomy")
    is_wildcard: bool = Field(
        default=False,
        description="True if this is a creative angle outside the standard taxonomy"
    )
    sub_angle: str = Field(description="Specific angle within the category")
    reasoning: str = Field(description="Why this angle was chosen given past history")


class SearchQuery(BaseModel):
    """Search query shaped by company profile and chosen angle."""
    query: str = Field(description="The main search query to use")
    backup_query: Optional[str] = Field(
        default=None,
        description="Optional backup query if the main one returns no results"
    )


# ---------------------------------------------------------------------------
# Phase 3 Schemas
# ---------------------------------------------------------------------------

class Signal(BaseModel):
    """Extracted market signal from search results."""
    signal_description: str = Field(
        description="What is the specific signal found in the search results?"
    )
    specificity_proof: str = Field(
        description="Exact quote or data point from results that proves this is specific, not generic"
    )
    recency: str = Field(
        description="How recent is this signal? (e.g. 'Published 3 days ago', 'From Q1 2024 report')"
    )
    source: str = Field(
        description="Source name or URL where this signal was found"
    )
    why_it_matters: str = Field(
        description="Why this signal is relevant for content creation for this company"
    )
    strength: Literal["strong", "weak"] = Field(
        description="'strong' if signal passes all 3 tests (Specific + Recent + Verifiable), 'weak' otherwise"
    )


# ---------------------------------------------------------------------------
# Phase 4 Schemas
# ---------------------------------------------------------------------------

class IdeaEvaluation(BaseModel):
    """Evaluation of a single generated idea."""
    idea_index: int = Field(description="The index of the idea in the original batch")
    passed: bool = Field(description="True if the idea passes all 4 validation criteria")
    failed_criteria: List[str] = Field(
        description="List of criteria that failed: relevance, actionability, uniqueness, signal-grounding"
    )
    reason: str = Field(description="Explanation of why it passed or failed")
    action: Literal["pass", "tweak", "fail"] = Field(
        description="'pass' if ready, 'tweak' if salvageable with refinement, 'fail' if completely useless"
    )


class ValidationBatch(BaseModel):
    """Batch evaluation of all generated ideas."""
    evaluations: List[IdeaEvaluation]
