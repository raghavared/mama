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
import {FloatingShapes, AnimatedRings} from '../components/FloatingShapes';
import {ParticleEffect} from '../components/ParticleEffect';

export const MarketingIntro: React.FC<MarketingVideoProps> = (rawProps) => {
  const props = {...defaultProps, ...rawProps};
  const {
    title,
    subtitle,
    brandColor,
    accentColor,
    backgroundType,
    logoText,
  } = props;

  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  // Logo animation — springs in from top
  const logoScale = spring({
    frame,
    fps,
    from: 0,
    to: 1,
    config: {damping: 12, stiffness: 180},
  });
  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  // Divider line
  const lineWidth = interpolate(frame, [20, 50], [0, 200], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  // Title glow pulse
  const glowIntensity = 10 + Math.sin((frame / fps) * Math.PI) * 5;

  // Final fade out
  const totalFade = interpolate(frame, [fps * 9, fps * 10], [1, 0], {
    extrapolateRight: 'clamp',
    extrapolateLeft: 'clamp',
  });

  return (
    <AbsoluteFill style={{overflow: 'hidden', opacity: totalFade}}>
      {/* Background */}
      <GradientBackground
        brandColor={brandColor}
        accentColor={accentColor}
        backgroundType={backgroundType}
        animated
      />

      {/* Particle layer */}
      {backgroundType === 'particles' && (
        <ParticleEffect
          brandColor={brandColor}
          accentColor={accentColor}
          particleCount={25}
          width={width}
          height={height}
        />
      )}

      {/* Decorative rings */}
      <AnimatedRings brandColor={brandColor} accentColor={accentColor} />

      {/* Floating geometric shapes */}
      <FloatingShapes
        brandColor={brandColor}
        accentColor={accentColor}
        count={8}
      />

      {/* Logo badge */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, ${brandColor}, ${accentColor})`,
            borderRadius: 16,
            padding: '16px 40px',
            boxShadow: `0 8px 32px ${brandColor}66, 0 0 60px ${brandColor}33`,
          }}
        >
          <div
            style={{
              fontFamily: 'Arial Black, sans-serif',
              fontSize: 48,
              fontWeight: 900,
              color: '#ffffff',
              letterSpacing: 8,
              textShadow: '0 2px 8px rgba(0,0,0,0.3)',
            }}
          >
            {logoText}
          </div>
        </div>
      </div>

      {/* Decorative separator line */}
      <div
        style={{
          position: 'absolute',
          top: 270,
          left: '50%',
          transform: 'translateX(-50%)',
          width: lineWidth,
          height: 2,
          background: `linear-gradient(90deg, transparent, ${accentColor}, transparent)`,
          boxShadow: `0 0 8px ${accentColor}`,
        }}
      />

      {/* Main content area */}
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
          paddingTop: 100,
          paddingLeft: 60,
          paddingRight: 60,
        }}
      >
        {/* Title */}
        <AnimatedText
          text={title}
          delay={25}
          animation="charReveal"
          fps={fps}
          style={{
            fontFamily: 'Arial Black, Impact, sans-serif',
            fontSize: 82,
            fontWeight: 900,
            color: '#ffffff',
            textAlign: 'center',
            lineHeight: 1.1,
            letterSpacing: -1,
            textShadow: `0 0 ${glowIntensity}px ${brandColor}, 0 4px 20px rgba(0,0,0,0.5)`,
            marginBottom: 40,
          }}
        />

        {/* Accent line */}
        <div
          style={{
            width: interpolate(frame, [45, 70], [0, 120], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            }),
            height: 4,
            background: `linear-gradient(90deg, ${brandColor}, ${accentColor})`,
            borderRadius: 2,
            marginBottom: 36,
            boxShadow: `0 0 12px ${accentColor}`,
          }}
        />

        {/* Subtitle */}
        <AnimatedText
          text={subtitle || ''}
          delay={50}
          animation="fadeUp"
          fps={fps}
          style={{
            fontFamily: 'Arial, sans-serif',
            fontSize: 38,
            fontWeight: 400,
            color: `${accentColor}`,
            textAlign: 'center',
            lineHeight: 1.4,
            letterSpacing: 2,
          }}
        />
      </div>

      {/* Bottom decorative bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 6,
          background: `linear-gradient(90deg, ${brandColor}, ${accentColor}, ${brandColor})`,
          opacity: interpolate(frame, [60, 80], [0, 1], {
            extrapolateRight: 'clamp',
            extrapolateLeft: 'clamp',
          }),
        }}
      />
    </AbsoluteFill>
  );
};
