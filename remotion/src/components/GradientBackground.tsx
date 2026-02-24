import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';

interface GradientBackgroundProps {
  brandColor?: string;
  accentColor?: string;
  backgroundType?: 'gradient' | 'particles' | 'solid';
  animated?: boolean;
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  brandColor = '#6366f1',
  accentColor = '#f59e0b',
  backgroundType = 'gradient',
  animated = true,
}) => {
  const frame = useCurrentFrame();

  const rotation = animated
    ? interpolate(frame, [0, 900], [0, 360], {extrapolateRight: 'clamp'})
    : 0;

  const pulse = animated
    ? interpolate(
        Math.sin((frame / 30) * Math.PI),
        [-1, 1],
        [0.85, 1.15]
      )
    : 1;

  if (backgroundType === 'solid') {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: brandColor,
        }}
      />
    );
  }

  const gradientAngle = animated ? `${45 + rotation * 0.1}deg` : '135deg';

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        overflow: 'hidden',
      }}
    >
      {/* Base gradient */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `linear-gradient(${gradientAngle}, ${brandColor} 0%, #1a1a2e 40%, ${accentColor}33 100%)`,
        }}
      />

      {/* Animated glow orb 1 */}
      <div
        style={{
          position: 'absolute',
          top: `${-10 + Math.sin(frame / 60) * 5}%`,
          left: `${-10 + Math.cos(frame / 80) * 5}%`,
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${brandColor}66 0%, transparent 70%)`,
          transform: `scale(${pulse})`,
        }}
      />

      {/* Animated glow orb 2 */}
      <div
        style={{
          position: 'absolute',
          bottom: `${-5 + Math.cos(frame / 70) * 8}%`,
          right: `${-15 + Math.sin(frame / 90) * 6}%`,
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accentColor}44 0%, transparent 70%)`,
          transform: `scale(${1.2 - pulse * 0.2})`,
        }}
      />

      {/* Center glow */}
      <div
        style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${brandColor}33 0%, transparent 70%)`,
          opacity: 0.5 + Math.sin(frame / 45) * 0.3,
        }}
      />

      {/* Subtle noise overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.15)',
        }}
      />

      {backgroundType === 'particles' && (
        <ParticleLayer brandColor={brandColor} accentColor={accentColor} frame={frame} />
      )}
    </div>
  );
};

const ParticleLayer: React.FC<{
  brandColor: string;
  accentColor: string;
  frame: number;
}> = ({brandColor, accentColor, frame}) => {
  const particles = Array.from({length: 20}, (_, i) => {
    const seed = i * 137.508;
    const x = ((seed * 7) % 100);
    const y = ((seed * 13) % 100);
    const size = 2 + (i % 4);
    const speed = 0.3 + (i % 5) * 0.15;
    const offsetY = (frame * speed) % 120;
    const opacity = 0.3 + (i % 4) * 0.15;
    const color = i % 3 === 0 ? accentColor : brandColor;

    return {x, y: (y - offsetY + 120) % 120, size, opacity, color};
  });

  return (
    <>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            backgroundColor: p.color,
            opacity: p.opacity,
            boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
          }}
        />
      ))}
    </>
  );
};
