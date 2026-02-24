import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import {MarketingVideoProps, defaultProps} from '../types';
import {GradientBackground} from '../components/GradientBackground';
import {AnimatedText} from '../components/AnimatedText';
import {FloatingShapes} from '../components/FloatingShapes';

export const ContentHighlight: React.FC<MarketingVideoProps> = (rawProps) => {
  const props = {...defaultProps, ...rawProps};
  const {
    title,
    bodyText,
    brandColor,
    accentColor,
    backgroundType,
    bulletPoints,
  } = props;

  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Fade in / fade out
  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });
  const fadeOut = interpolate(frame, [fps * 11, fps * 12], [1, 0], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });
  const opacity = fadeIn * fadeOut;

  // Progress bar
  const progressWidth = interpolate(frame, [0, fps * 12], [0, 100], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  // Card slide in
  const cardX = spring({
    frame,
    fps,
    from: -100,
    to: 0,
    config: {damping: 20, stiffness: 150},
  });

  const bullets = bulletPoints || defaultProps.bulletPoints;

  return (
    <AbsoluteFill style={{overflow: 'hidden', opacity}}>
      {/* Background — slightly different shade */}
      <GradientBackground
        brandColor={brandColor}
        accentColor={accentColor}
        backgroundType="gradient"
        animated
      />

      <FloatingShapes
        brandColor={brandColor}
        accentColor={accentColor}
        count={5}
      />

      {/* Dark card overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.3)',
        }}
      />

      {/* Section label */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          left: 60,
          right: 60,
          opacity: interpolate(frame, [5, 25], [0, 1], {
            extrapolateRight: 'clamp',
            extrapolateLeft: 'clamp',
          }),
          transform: `translateY(${interpolate(frame, [5, 25], [-20, 0], {
            extrapolateRight: 'clamp',
            extrapolateLeft: 'clamp',
          })}px)`,
        }}
      >
        <div
          style={{
            display: 'inline-block',
            background: `linear-gradient(135deg, ${brandColor}33, ${accentColor}22)`,
            border: `1px solid ${accentColor}66`,
            borderRadius: 30,
            padding: '8px 24px',
            fontFamily: 'Arial, sans-serif',
            fontSize: 22,
            fontWeight: 700,
            color: accentColor,
            letterSpacing: 3,
            textTransform: 'uppercase' as const,
          }}
        >
          KEY HIGHLIGHTS
        </div>
      </div>

      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 160,
          left: 60,
          right: 60,
        }}
      >
        <AnimatedText
          text={title}
          delay={10}
          animation="slideIn"
          fps={fps}
          style={{
            fontFamily: 'Arial Black, sans-serif',
            fontSize: 62,
            fontWeight: 900,
            color: '#ffffff',
            lineHeight: 1.15,
            textShadow: `0 2px 20px ${brandColor}88`,
          }}
        />
      </div>

      {/* Main content card */}
      <div
        style={{
          position: 'absolute',
          top: 340,
          left: 40,
          right: 40,
          background: 'rgba(255,255,255,0.06)',
          backdropFilter: 'blur(10px)',
          borderRadius: 24,
          border: '1px solid rgba(255,255,255,0.12)',
          padding: 48,
          transform: `translateX(${cardX}px)`,
          boxShadow: `0 20px 60px rgba(0,0,0,0.3), 0 0 40px ${brandColor}22`,
        }}
      >
        {/* Body text with typewriter */}
        <AnimatedText
          text={bodyText || defaultProps.bodyText}
          delay={20}
          animation="typewriter"
          fps={fps}
          style={{
            fontFamily: 'Arial, sans-serif',
            fontSize: 32,
            fontWeight: 300,
            color: 'rgba(255,255,255,0.85)',
            lineHeight: 1.6,
            marginBottom: 48,
            letterSpacing: 0.5,
          }}
        />

        {/* Divider */}
        <div
          style={{
            width: interpolate(frame, [30, 60], [0, '100%' as unknown as number], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            }),
            height: 1,
            background: `linear-gradient(90deg, ${brandColor}, ${accentColor}, transparent)`,
            marginBottom: 40,
            opacity: 0.5,
          }}
        />

        {/* Bullet points */}
        <div style={{display: 'flex', flexDirection: 'column', gap: 28}}>
          {bullets.slice(0, 4).map((bullet, i) => {
            const bulletDelay = 45 + i * 18;
            const bulletOpacity = interpolate(
              frame,
              [bulletDelay, bulletDelay + 20],
              [0, 1],
              {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
            );
            const bulletX = interpolate(
              frame,
              [bulletDelay, bulletDelay + 25],
              [60, 0],
              {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
            );

            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 20,
                  opacity: bulletOpacity,
                  transform: `translateX(${bulletX}px)`,
                }}
              >
                {/* Icon dot */}
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${brandColor}, ${accentColor})`,
                    flexShrink: 0,
                    boxShadow: `0 0 8px ${accentColor}`,
                  }}
                />
                <div
                  style={{
                    fontFamily: 'Arial, sans-serif',
                    fontSize: 30,
                    fontWeight: 500,
                    color: '#ffffff',
                    lineHeight: 1.3,
                  }}
                >
                  {bullet}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stats bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 160,
          left: 40,
          right: 40,
          display: 'flex',
          justifyContent: 'space-around',
          opacity: interpolate(frame, [fps * 7, fps * 8], [0, 1], {
            extrapolateRight: 'clamp',
            extrapolateLeft: 'clamp',
          }),
        }}
      >
        {[
          {value: '10x', label: 'Faster'},
          {value: '98%', label: 'Accuracy'},
          {value: '24/7', label: 'Active'},
        ].map((stat, i) => {
          const statScale = spring({
            frame: Math.max(0, frame - fps * 7 - i * 8),
            fps,
            from: 0,
            to: 1,
            config: {damping: 14, stiffness: 200},
          });
          return (
            <div
              key={i}
              style={{
                textAlign: 'center',
                transform: `scale(${statScale})`,
              }}
            >
              <div
                style={{
                  fontFamily: 'Arial Black, sans-serif',
                  fontSize: 52,
                  fontWeight: 900,
                  color: accentColor,
                  textShadow: `0 0 20px ${accentColor}88`,
                  lineHeight: 1,
                }}
              >
                {stat.value}
              </div>
              <div
                style={{
                  fontFamily: 'Arial, sans-serif',
                  fontSize: 22,
                  color: 'rgba(255,255,255,0.6)',
                  letterSpacing: 2,
                  textTransform: 'uppercase' as const,
                }}
              >
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress bar at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 8,
          backgroundColor: 'rgba(255,255,255,0.1)',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progressWidth}%`,
            background: `linear-gradient(90deg, ${brandColor}, ${accentColor})`,
            boxShadow: `0 0 10px ${accentColor}`,
            borderRadius: '0 4px 4px 0',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
