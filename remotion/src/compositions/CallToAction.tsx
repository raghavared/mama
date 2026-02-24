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
import {ParticleEffect} from '../components/ParticleEffect';
import {ConfettiBurst} from '../components/ParticleEffect';

export const CallToAction: React.FC<MarketingVideoProps> = (rawProps) => {
  const props = {...defaultProps, ...rawProps};
  const {
    ctaText,
    brandColor,
    accentColor,
    backgroundType,
    hashtags,
    socialHandle,
  } = props;

  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  // Fade in
  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  // CTA text bounce
  const ctaScale = spring({
    frame: Math.max(0, frame - 10),
    fps,
    from: 0,
    to: 1,
    config: {damping: 10, stiffness: 160},
  });

  // Pulsing button
  const pulse = 1 + Math.sin((frame / fps) * Math.PI * 2) * 0.04;
  const buttonGlow = 20 + Math.sin((frame / fps) * Math.PI * 2) * 10;

  // Button appearance
  const buttonScale = spring({
    frame: Math.max(0, frame - 40),
    fps,
    from: 0,
    to: 1,
    config: {damping: 12, stiffness: 200},
  });

  // Hashtag animations
  const tags = hashtags || defaultProps.hashtags;
  const handle = socialHandle || defaultProps.socialHandle;

  // Final reveal: color wash
  const colorWash = interpolate(frame, [fps * 7, fps * 8], [0, 0.6], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  return (
    <AbsoluteFill style={{overflow: 'hidden', opacity: fadeIn}}>
      <GradientBackground
        brandColor={brandColor}
        accentColor={accentColor}
        backgroundType={backgroundType}
        animated
      />

      {/* Particle overlay */}
      <ParticleEffect
        brandColor={brandColor}
        accentColor={accentColor}
        particleCount={20}
        width={width}
        height={height}
      />

      {/* Confetti burst at start */}
      <ConfettiBurst
        brandColor={brandColor}
        accentColor={accentColor}
        startFrame={20}
      />

      {/* Top arc decoration */}
      <div
        style={{
          position: 'absolute',
          top: -200,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 800,
          height: 800,
          borderRadius: '50%',
          border: `2px solid ${brandColor}44`,
          boxShadow: `0 0 40px ${brandColor}22`,
          opacity: interpolate(frame, [0, 30], [0, 1], {
            extrapolateRight: 'clamp',
            extrapolateLeft: 'clamp',
          }),
        }}
      />

      {/* Main content */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          paddingLeft: 60,
          paddingRight: 60,
          gap: 0,
        }}
      >
        {/* "Don't miss out" label */}
        <div
          style={{
            fontFamily: 'Arial, sans-serif',
            fontSize: 28,
            fontWeight: 700,
            color: accentColor,
            letterSpacing: 4,
            textTransform: 'uppercase' as const,
            opacity: interpolate(frame, [5, 25], [0, 1], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            }),
            transform: `translateY(${interpolate(frame, [5, 25], [20, 0], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            })}px)`,
            marginBottom: 20,
          }}
        >
          ★ LIMITED TIME ★
        </div>

        {/* CTA Headline */}
        <div
          style={{
            transform: `scale(${ctaScale})`,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontFamily: 'Arial Black, Impact, sans-serif',
              fontSize: 96,
              fontWeight: 900,
              color: '#ffffff',
              textAlign: 'center',
              lineHeight: 1,
              letterSpacing: -2,
              textShadow: `0 0 30px ${brandColor}, 0 0 60px ${brandColor}66, 0 6px 30px rgba(0,0,0,0.5)`,
            }}
          >
            {ctaText}
          </div>
        </div>

        {/* Decorative underline */}
        <div
          style={{
            width: interpolate(frame, [30, 55], [0, 300], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            }),
            height: 4,
            background: `linear-gradient(90deg, ${brandColor}, ${accentColor}, ${brandColor})`,
            borderRadius: 2,
            boxShadow: `0 0 12px ${accentColor}`,
            marginBottom: 60,
          }}
        />

        {/* Animated CTA Button */}
        <div
          style={{
            transform: `scale(${buttonScale * pulse})`,
            cursor: 'pointer',
            marginBottom: 60,
          }}
        >
          <div
            style={{
              background: `linear-gradient(135deg, ${brandColor}, ${accentColor})`,
              borderRadius: 60,
              padding: '28px 72px',
              boxShadow: `0 8px ${buttonGlow}px ${brandColor}66, 0 0 60px ${brandColor}33, inset 0 1px 0 rgba(255,255,255,0.2)`,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Button shine */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: `${interpolate(frame, [40, fps * 8], [-100, 200], {
                  extrapolateRight: 'clamp',
                  extrapolateLeft: 'clamp',
                })}%`,
                width: '60%',
                height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent)',
                transform: 'skewX(-20deg)',
              }}
            />
            <div
              style={{
                fontFamily: 'Arial Black, sans-serif',
                fontSize: 38,
                fontWeight: 900,
                color: '#ffffff',
                letterSpacing: 2,
                textShadow: '0 2px 8px rgba(0,0,0,0.3)',
                position: 'relative',
                whiteSpace: 'nowrap' as const,
              }}
            >
              START FREE →
            </div>
          </div>
        </div>

        {/* Hashtags */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap' as const,
            justifyContent: 'center',
            gap: 16,
            marginBottom: 40,
          }}
        >
          {tags.map((tag, i) => {
            const tagDelay = 55 + i * 12;
            const tagOpacity = interpolate(
              frame,
              [tagDelay, tagDelay + 15],
              [0, 1],
              {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
            );
            const tagX = interpolate(
              frame,
              [tagDelay, tagDelay + 20],
              [i % 2 === 0 ? -80 : 80, 0],
              {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'}
            );

            return (
              <div
                key={i}
                style={{
                  opacity: tagOpacity,
                  transform: `translateX(${tagX}px)`,
                  fontFamily: 'Arial, sans-serif',
                  fontSize: 28,
                  fontWeight: 700,
                  color: accentColor,
                  background: `${accentColor}15`,
                  border: `1px solid ${accentColor}44`,
                  borderRadius: 30,
                  padding: '8px 20px',
                  letterSpacing: 1,
                }}
              >
                {tag}
              </div>
            );
          })}
        </div>

        {/* Social handle */}
        <AnimatedText
          text={handle}
          delay={70}
          animation="scaleIn"
          fps={fps}
          style={{
            fontFamily: 'Arial, sans-serif',
            fontSize: 32,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.7)',
            letterSpacing: 2,
          }}
        />
      </div>

      {/* Color wash finale */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `radial-gradient(circle at center, ${brandColor}, ${accentColor})`,
          opacity: colorWash,
        }}
      />

      {/* Bottom bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 6,
          background: `linear-gradient(90deg, ${accentColor}, ${brandColor}, ${accentColor})`,
        }}
      />
    </AbsoluteFill>
  );
};
