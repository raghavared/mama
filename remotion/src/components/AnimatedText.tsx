import React from 'react';
import {useCurrentFrame, interpolate, spring} from 'remotion';

interface AnimatedTextProps {
  text: string;
  style?: React.CSSProperties;
  delay?: number;
  animation?: 'fadeUp' | 'charReveal' | 'slideIn' | 'typewriter' | 'scaleIn';
  fps?: number;
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  style = {},
  delay = 0,
  animation = 'fadeUp',
  fps = 30,
}) => {
  const frame = useCurrentFrame();
  const adjustedFrame = Math.max(0, frame - delay);

  if (animation === 'charReveal') {
    return (
      <CharReveal
        text={text}
        style={style}
        frame={adjustedFrame}
        fps={fps}
      />
    );
  }

  if (animation === 'typewriter') {
    return (
      <TypewriterText
        text={text}
        style={style}
        frame={adjustedFrame}
        fps={fps}
      />
    );
  }

  if (animation === 'slideIn') {
    const opacity = interpolate(adjustedFrame, [0, 20], [0, 1], {
      extrapolateRight: 'clamp',
      extrapolateLeft: 'clamp',
    });
    const translateX = interpolate(adjustedFrame, [0, 25], [-80, 0], {
      extrapolateRight: 'clamp',
      extrapolateLeft: 'clamp',
    });
    return (
      <div style={{...style, opacity, transform: `translateX(${translateX}px)`}}>
        {text}
      </div>
    );
  }

  if (animation === 'scaleIn') {
    const scale = spring({
      frame: adjustedFrame,
      fps,
      from: 0,
      to: 1,
      config: {damping: 14, stiffness: 200},
    });
    const opacity = interpolate(adjustedFrame, [0, 10], [0, 1], {
      extrapolateRight: 'clamp',
      extrapolateLeft: 'clamp',
    });
    return (
      <div
        style={{
          ...style,
          opacity,
          transform: `scale(${scale})`,
          display: 'inline-block',
        }}
      >
        {text}
      </div>
    );
  }

  // Default: fadeUp
  const opacity = interpolate(adjustedFrame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });
  const translateY = interpolate(adjustedFrame, [0, 25], [40, 0], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  return (
    <div
      style={{
        ...style,
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      {text}
    </div>
  );
};

const CharReveal: React.FC<{
  text: string;
  style: React.CSSProperties;
  frame: number;
  fps: number;
}> = ({text, style, frame}) => {
  const charsPerFrame = 1.5;
  const visibleChars = Math.floor(frame * charsPerFrame);

  return (
    <div style={style}>
      {text.split('').map((char, i) => {
        const charOpacity = interpolate(
          visibleChars - i,
          [0, 3],
          [0, 1],
          {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
        );
        const charY = interpolate(
          visibleChars - i,
          [0, 5],
          [15, 0],
          {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
        );
        return (
          <span
            key={i}
            style={{
              opacity: charOpacity,
              display: 'inline-block',
              transform: `translateY(${charY}px)`,
              whiteSpace: char === ' ' ? 'pre' : 'normal',
            }}
          >
            {char}
          </span>
        );
      })}
    </div>
  );
};

const TypewriterText: React.FC<{
  text: string;
  style: React.CSSProperties;
  frame: number;
  fps: number;
}> = ({text, style, frame, fps}) => {
  const charsPerSecond = 20;
  const visibleChars = Math.floor((frame / fps) * charsPerSecond);
  const displayText = text.slice(0, visibleChars);
  const showCursor = frame < (text.length / charsPerSecond) * fps + fps;

  return (
    <div style={style}>
      {displayText}
      {showCursor && (
        <span
          style={{
            opacity: Math.floor(frame / 15) % 2 === 0 ? 1 : 0,
            borderRight: '3px solid currentColor',
            marginLeft: 2,
          }}
        />
      )}
    </div>
  );
};
