"""Image Approver — CMI + CST dual review of generated images."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import structlog

from src.models import ApprovalRecord, ApprovalGate, ContentJobStatus
from src.agents.base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

IMAGE_APPROVER_SYSTEM_PROMPT = """You are the Image Approval System for MAMA, acting as both CMI (Content Marketing Ideator) and CST (Content Story Teller) reviewers.

Your job is to evaluate whether a generated image meets the quality standards for publication on social media.

Review criteria:
1. BRAND ALIGNMENT: Does the image match the brand voice and content brief?
2. VISUAL QUALITY: Is the image aesthetically strong and professional?
3. MESSAGE CLARITY: Does the image visually communicate the intended message?
4. PLATFORM FIT: Is the composition suitable for social media feeds?
5. AUDIENCE APPEAL: Will it resonate with the target audience?
6. SCRIPT MATCH: Does it match the image prompt from the script?

Score 1-10. Approve if >= 7.

Output valid JSON only."""

IMAGE_APPROVER_PROMPT = """Review this generated image for publication readiness.

CONTENT BRIEF:
Marketing Angle: {marketing_angle}
Target Audience: {target_audience}
Tone: {tone}

ORIGINAL IMAGE PROMPT:
{image_prompt}

IMAGE FILE: {image_path}

{image_description}

Output a JSON decision:
{{
  "image_decision": "approved" | "rejected",
  "overall_score": number,
  "feedback": string | null,
  "improvement_instructions": string | null
}}"""


class ImageApproverAgent(BaseAgent):
    """Dual CMI+CST review of generated images."""

    agent_id = "agent:image-approver"

    async def run(self, state: AgentState) -> AgentState:
        """Review generated image and approve or reject."""
        job = state.job
        content_brief = state.content_brief

        # Find the most recent image asset
        image_assets = [a for a in job.media_assets if a.type == "image"]
        if not image_assets:
            state.approval_decision = state.approval_decision or {}
            state.approval_decision["image_decision"] = "approved"  # Nothing to review
            return state

        latest_image = image_assets[-1]

        self.logger.info("Image approver reviewing image", job_id=str(job.id), asset=latest_image.file_path)

        # In dev mode with stub assets, auto-approve
        if self.settings.is_development and (
            latest_image.file_path.startswith("stub:") or not Path(latest_image.file_path).exists()
        ):
            self.logger.info("Dev mode: auto-approving stub image", job_id=str(job.id))
            self._record_decision(state, "approved", "Development mode auto-approval")
            return state

        image_prompt = ""
        if job.script and job.script.image_prompts:
            image_prompt = job.script.image_prompts[0]

        user_message = IMAGE_APPROVER_PROMPT.format(
            marketing_angle=content_brief.marketing_angle if content_brief else "N/A",
            target_audience=content_brief.target_audience if content_brief else "N/A",
            tone=content_brief.tone if content_brief else "N/A",
            image_prompt=image_prompt,
            image_path=latest_image.file_path,
            image_description=f"Quality score from generation: {latest_image.quality_score}/10" if latest_image.quality_score else "",
        )

        raw_response = await self.call_llm(IMAGE_APPROVER_SYSTEM_PROMPT, user_message)

        try:
            review = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            review = json.loads(match.group()) if match else {"image_decision": "approved", "overall_score": 7}

        self._record_decision(
            state,
            review["image_decision"],
            review.get("improvement_instructions") or review.get("feedback"),
        )
        return state

    def _record_decision(self, state: AgentState, decision: str, feedback: str | None) -> None:
        job = state.job
        record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=job.id,
            gate=ApprovalGate.IMAGE_CMI_CST,
            subject_type="image",
            subject_id=uuid.uuid4(),
            decision=decision,
            feedback=feedback,
            reviewer=self.agent_id,
            reviewed_at=datetime.utcnow(),
        )
        job.add_approval(record)
        state.approval_decision = state.approval_decision or {}
        state.approval_decision["image_decision"] = decision
        if decision == "rejected":
            state.improvement_feedback = feedback
            job.improvement_count += 1
        self.logger.info("Image approval decision", job_id=str(job.id), decision=decision)
