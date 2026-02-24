import {registerRoot, Composition} from 'remotion';
import React from 'react';
import {MarketingVideo, INTRO_DURATION, HIGHLIGHT_DURATION, CTA_DURATION} from './compositions/MarketingVideo';
import {MarketingIntro} from './compositions/MarketingIntro';
import {ContentHighlight} from './compositions/ContentHighlight';
import {CallToAction} from './compositions/CallToAction';
import {defaultProps, MarketingVideoProps} from './types';

const TOTAL_FRAMES = INTRO_DURATION + HIGHLIGHT_DURATION + CTA_DURATION; // 900 frames = 30s
const FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;

const Root: React.FC = () => {
  return (
    <>
      {/* Full 30-second marketing video (all 3 scenes sequenced) */}
      <Composition
        id="MarketingVideo"
        component={MarketingVideo}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={defaultProps}
      />

      {/* Scene 1 standalone: Animated intro/headline */}
      <Composition
        id="MarketingIntro"
        component={MarketingIntro}
        durationInFrames={INTRO_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={defaultProps}
      />

      {/* Scene 2 standalone: Product/service showcase */}
      <Composition
        id="ContentHighlight"
        component={ContentHighlight}
        durationInFrames={HIGHLIGHT_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={defaultProps}
      />

      {/* Scene 3 standalone: Call to action */}
      <Composition
        id="CallToAction"
        component={CallToAction}
        durationInFrames={CTA_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={defaultProps}
      />
    </>
  );
};

registerRoot(Root);

// Re-export everything for external use
export {MarketingVideo} from './compositions/MarketingVideo';
export {MarketingIntro} from './compositions/MarketingIntro';
export {ContentHighlight} from './compositions/ContentHighlight';
export {CallToAction} from './compositions/CallToAction';
export type {MarketingVideoProps} from './types';
export {defaultProps} from './types';
