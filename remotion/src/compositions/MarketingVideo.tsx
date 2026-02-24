import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {MarketingVideoProps, defaultProps} from '../types';
import {MarketingIntro} from './MarketingIntro';
import {ContentHighlight} from './ContentHighlight';
import {CallToAction} from './CallToAction';

// Scene durations in frames at 30fps
const INTRO_DURATION = 300;       // 10s
const HIGHLIGHT_DURATION = 360;   // 12s
const CTA_DURATION = 240;         // 8s

export const MarketingVideo: React.FC<MarketingVideoProps> = (rawProps) => {
  const props = {...defaultProps, ...rawProps};

  return (
    <AbsoluteFill style={{backgroundColor: '#000000'}}>
      {/* Scene 1: MarketingIntro (0–10s) */}
      <Sequence from={0} durationInFrames={INTRO_DURATION}>
        <MarketingIntro {...props} />
      </Sequence>

      {/* Scene 2: ContentHighlight (10–22s) */}
      <Sequence from={INTRO_DURATION} durationInFrames={HIGHLIGHT_DURATION}>
        <ContentHighlight {...props} />
      </Sequence>

      {/* Scene 3: CallToAction (22–30s) */}
      <Sequence
        from={INTRO_DURATION + HIGHLIGHT_DURATION}
        durationInFrames={CTA_DURATION}
      >
        <CallToAction {...props} />
      </Sequence>
    </AbsoluteFill>
  );
};

export {INTRO_DURATION, HIGHLIGHT_DURATION, CTA_DURATION};
