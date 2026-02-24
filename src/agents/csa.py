"""CSA — Content Script Approver."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

import structlog

from src.models import ApprovalRecord, ApprovalGate, ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

CSA_SYSTEM_PROMPT = """You are CSA (Content Script Approver), the senior editorial director and quality gatekeeper for a world-class marketing agency serving financial institutions, energy companies, and infrastructure brands.

Your role is to ensure ONLY exceptional content reaches the expensive media generation step. You are a tough but fair critic. Your standard: would this content make a CMO of a top financial services firm proud to post it?

SCORING RUBRIC — use these anchors exactly:

1. HOOK STRENGTH (weight: 25%)
   - 9-10: Instantly stops scrolling. Pattern interrupt, bold contrarian claim, or open loop that creates irresistible curiosity. First 7 words demand attention.
   - 7-8: Solid hook, clearly above average. Specific and relevant. Slightly predictable but still compelling.
   - 5-6: Generic opening. Could apply to any brand. "Did you know..." or "We are excited to announce..." style.
   - 1-4: Weak, boring, or completely off-brand. No engagement value.

2. MESSAGE CLARITY (weight: 20%)
   - 9-10: Every key message is quotable, passes the "So what?" test, and builds logically toward the CTA.
   - 7-8: Messages are clear and relevant. Minor redundancy or slight loss of focus in one message.
   - 5-6: Messages present but vague, generic, or could apply to any competitor brand.
   - 1-4: Confusing, contradictory, or key messages from the brief are missing.

3. CALL TO ACTION (weight: 20%)
   - 9-10: Specific action + specific value proposition. "Download our 3-page fund overview — see the 4 infrastructure assets generating above-market returns" beats "Contact us."
   - 7-8: Clear CTA with reasonable specificity. Action and benefit both present.
   - 5-6: Generic CTA. "Learn more", "Contact us", "Visit our website" with no benefit stated.
   - 1-4: No CTA, buried CTA, or CTA that contradicts the content.

4. BRAND ALIGNMENT (weight: 15%)
   - 9-10: Voice, tone, and language are perfectly consistent with brand brief. Specialist industry vocabulary used correctly and confidently.
   - 7-8: Mostly on-brand. One or two word choices feel slightly generic or off-tone.
   - 5-6: Partially on-brand but includes generic marketing language that any brand could use.
   - 1-4: Off-brand. Wrong tone, wrong vocabulary, or content that conflicts with stated brand values.

5. AUDIENCE FIT (weight: 10%)
   - 9-10: Content speaks directly to the specified audience's pain points, desires, and language. Audience will feel "this was written for me."
   - 7-8: Good audience fit with minor generalisations.
   - 5-6: Tries to appeal to everyone — too broad for the specified audience.
   - 1-4: Wrong audience, wrong sophistication level, or tone mismatch.

6. PLATFORM SUITABILITY (weight: 10%)
   - 9-10: Each platform variant uses the correct format, length, tone, and native features for that platform.
   - 7-8: Platforms covered with minor format issues (slightly too long for one platform).
   - 5-6: Generic content that hasn't been properly adapted for each platform's requirements.
   - 1-4: Same content copy-pasted across all platforms, or missing platform variants entirely.

For IMAGE SCRIPTS, also score:
7. IMAGE PROMPT QUALITY (bonus, affects overall score)
   - 9-10: Each prompt is 100+ words, cinematic, photorealistic directives present, specific settings, professional lighting spec, no generic anti-patterns.
   - 7-8: Good prompts but slightly generic in one area.
   - 5-6: Short prompts (<50 words), vague descriptions, generic "office" or "businessman" settings.
   - 1-4: One-line prompts, no quality directives, completely unusable for premium image generation.

For VIDEO SCRIPTS, also score:
7. FRAME COHERENCE & CINEMATIC QUALITY (bonus, affects overall score)
   - 9-10: Each frame is 50+ words, specifies camera movement, lighting, colour mood, and specific background. Frames build a coherent visual story.
   - 7-8: Good scenes, minor gaps in visual specificity.
   - 5-6: Short, generic scene descriptions that could produce any generic video.
   - 1-4: One-line scenes with no visual direction.

APPROVAL THRESHOLD:
- APPROVE if weighted overall score >= 7.5 AND no individual criterion (1-6) scores below 6
- REJECT if overall score < 7.5 OR any criterion (1-6) scores below 6
- REJECTION FEEDBACK must be: specific (quote the exact line that failed), actionable (tell exactly what to rewrite), and constructive (provide a rewrite example where possible)

Output valid JSON only."""

CSA_USER_PROMPT_TEMPLATE = """Review the following {script_type} against publication standards for a world-class financial/energy brand.

BRAND CONTEXT & CONTENT BRIEF:
{brief_json}

SCRIPT TO REVIEW:
{script_content}

{extended_script_section}

{video_frames_section}

Score each criterion using the anchored rubric. Calculate weighted overall score:
- Hook Strength: 25%
- Message Clarity: 20%  
- Call to Action: 20%
- Brand Alignment: 15%
- Audience Fit: 10%
- Platform Suitability: 10%

Output a JSON review decision:

{{
  "decision": "approved" | "rejected",
  "overall_score": number,        // Weighted average: 0.25*hook + 0.20*message + 0.20*cta + 0.15*brand + 0.10*audience + 0.10*platform
  "criteria_scores": {{
    "hook_strength": number,       // 1-10 with anchor reasoning
    "message_clarity": number,
    "call_to_action": number,
    "brand_alignment": number,
    "audience_fit": number,
    "platform_suitability": number,
    "content_quality": number      // Image prompt quality OR frame cinematic quality (1-10)
  }},
  "score_rationale": {{           // One sentence per criterion explaining the score
    "hook_strength": string,
    "message_clarity": string,
    "call_to_action": string,
    "brand_alignment": string,
    "audience_fit": string,
    "platform_suitability": string,
    "content_quality": string
  }},
  "strengths": [string],          // 2-3 specific things done well (quote the actual text)
  "rejection_reasons": [string] | null,  // Each reason: quote the failing line + explain why it fails
  "improvement_feedback": string | null, // Structured as: WHAT failed → WHY it fails → HOW to fix it (with rewrite example)
  "approval_notes": string | null,       // For approved scripts: what makes this publication-ready
  "publish_confidence": "high" | "medium" | "low"  // Predicted performance if published
}}"""


class CSAAgent(BaseAgent):
    """Content Script Approver — reviews and approves/rejects scripts."""

    agent_id = "agent:csa"

    async def run(self, state: AgentState) -> AgentState:
        """Review the current script and decide approve/reject."""
        job = state.job
        script = state.script
        content_brief = state.content_brief

        if not script or not content_brief:
            state.error = "CSA requires script and content_brief"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info(
            "CSA reviewing script",
            job_id=str(job.id),
            script_type=script.type,
            version=script.version,
        )

        # Build extended script section from metadata
        extended_script_section = ""
        extended_data = (
            job.metadata.get("cst_script_extended", {})
            or job.metadata.get("vst_script_extended", {})
        )
        if extended_data:
            lines = ["EXTENDED SCRIPT METADATA:"]
            for key in ("hook", "hook_type", "narrative", "image_style_notes",
                        "tone", "pacing", "visual_direction", "platform_notes"):
                if key in extended_data:
                    label = key.replace("_", " ").title()
                    lines.append(f"  {label}: {extended_data[key]}")
            # Catch any remaining keys not in the explicit list
            handled = {"hook", "hook_type", "narrative", "image_style_notes",
                       "tone", "pacing", "visual_direction", "platform_notes"}
            for key, value in extended_data.items():
                if key not in handled:
                    label = key.replace("_", " ").title()
                    lines.append(f"  {label}: {value}")
            extended_script_section = "\n".join(lines)

        video_frames_section = ""
        if script.video_frames:
            frames_text = "\n".join([
                f"Frame {f.frame_number} ({f.duration_seconds}s): {f.scene_description} | Audio: {f.audio_cue}"
                for f in script.video_frames
            ])
            video_frames_section = f"\nVIDEO FRAMES:\n{frames_text}"

        brief_dict = content_brief.model_dump(mode="json")
        user_message = CSA_USER_PROMPT_TEMPLATE.format(
            script_type="image script" if script.type == "image_script" else "video script",
            brief_json=json.dumps(brief_dict, indent=2),
            script_content=script.content,
            extended_script_section=extended_script_section,
            video_frames_section=video_frames_section,
        )

        raw_response = await self.call_llm(
            CSA_SYSTEM_PROMPT, user_message, max_tokens=6000
        )

        try:
            review = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                review = json.loads(match.group())
            else:
                # Default to rejection on parse error
                review = {
                    "decision": "rejected",
                    "overall_score": 0,
                    "improvement_feedback": "CSA could not parse script. Please regenerate.",
                }

        # Validate and log weighted score calculation
        criteria = review.get("criteria_scores", {})
        hook = criteria.get("hook_strength", 0)
        msg = criteria.get("message_clarity", 0)
        cta = criteria.get("call_to_action", 0)
        brand = criteria.get("brand_alignment", 0)
        audience = criteria.get("audience_fit", 0)
        platform = criteria.get("platform_suitability", 0)
        weighted = (
            0.25 * hook
            + 0.20 * msg
            + 0.20 * cta
            + 0.15 * brand
            + 0.10 * audience
            + 0.10 * platform
        )
        self.logger.info(
            "CSA weighted score validation",
            job_id=str(job.id),
            hook=hook,
            message_clarity=msg,
            cta=cta,
            brand_alignment=brand,
            audience_fit=audience,
            platform_suitability=platform,
            weighted_calculated=round(weighted, 2),
            llm_reported=review.get("overall_score"),
        )

        # Check approval threshold: score >= 7.5 AND no core criterion below 6
        core_scores = [hook, msg, cta, brand, audience, platform]
        min_core_score = min(core_scores) if core_scores else 0
        overall_score = review.get("overall_score", 0)
        passes_threshold = overall_score >= 7.5 and min_core_score >= 6

        # Override decision based on threshold validation
        if passes_threshold and review.get("decision") != "approved":
            self.logger.warning(
                "CSA overriding LLM decision to approved based on threshold",
                job_id=str(job.id),
                overall_score=overall_score,
                min_core_score=min_core_score,
            )
            review["decision"] = "approved"
        elif not passes_threshold and review.get("decision") == "approved":
            self.logger.warning(
                "CSA overriding LLM decision to rejected based on threshold",
                job_id=str(job.id),
                overall_score=overall_score,
                min_core_score=min_core_score,
            )
            review["decision"] = "rejected"

        approval_record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=job.id,
            gate=ApprovalGate.SCRIPT_CSA,
            subject_type="script",
            subject_id=uuid.uuid4(),  # Would be script ID in production
            decision=review["decision"],
            feedback=json.dumps({
                "improvement_feedback": review.get("improvement_feedback"),
                "score_rationale": review.get("score_rationale"),
                "publish_confidence": review.get("publish_confidence"),
            }),
            reviewer=self.agent_id,
            reviewed_at=datetime.utcnow(),
        )

        job.add_approval(approval_record)
        state.approval_decision = review

        if review["decision"] == "approved":
            job.update_status(ContentJobStatus.APPROVED)
            state.improvement_feedback = None
            self.logger.info(
                "CSA approved script",
                job_id=str(job.id),
                score=review.get("overall_score"),
                publish_confidence=review.get("publish_confidence"),
            )
        else:
            job.update_status(ContentJobStatus.REJECTED)
            state.improvement_feedback = review.get("improvement_feedback", "Please improve the script.")
            job.improvement_count += 1
            self.logger.info(
                "CSA rejected script",
                job_id=str(job.id),
                score=review.get("overall_score"),
                reasons=review.get("rejection_reasons", []),
                min_core_score=min_core_score,
            )

        state.messages.append({
            "agent": self.agent_id,
            "action": f"script_{review['decision']}",
            "score": review.get("overall_score"),
            "publish_confidence": review.get("publish_confidence"),
        })
        return state
