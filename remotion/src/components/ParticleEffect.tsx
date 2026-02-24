import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';

interface ParticleEffectProps {
  brandColor?: string;
  accentColor?: string;
  particleCount?: number;
  width?: number;
  height?: number;
}

export const ParticleEffect: React.FC<ParticleEffectProps> = ({
  brandColor = '#6366f1',
  accentColor = '#f59e0b',
  particleCount = 30,
  width = 1080,
  height = 1920,
}) => {
  const frame = useCurrentFrame();

  const particles = React.useMemo(() => {
    return Array.from({length: particleCount}, (_, i) => {
      const seed = (i + 1) * 127.3;
      const x = (seed * 3.14) % width;
      const baseY = (seed * 2.71) % height;
      const size = 2 + (i % 5);
      const speed = 0.5 + (i % 6) * 0.4;
      const opacity = 0.2 + (i % 5) * 0.12;
      const color = i % 4 === 0 ? accentColor : i % 3 === 0 ? '#ffffff' : brandColor;
      const drift = (i % 3 - 1) * 0.3;
      const twinkleSpeed = 0.05 + (i % 4) * 0.03;
      const twinkleOffset = i * 7;
      return {x, baseY, size, speed, opacity, color, drift, twinkleSpeed, twinkleOffset};
    });
  }, [particleCount, brandColor, accentColor, width, height]);

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
      {particles.map((p, i) => {
        const travel = (frame * p.speed) % (height + 50);
        const y = (p.baseY - travel + height + 50) % (height + 50) - 50;
        const x = p.x + Math.sin((frame + p.twinkleOffset) * p.drift) * 20;
        const twinkle = Math.sin((frame + p.twinkleOffset) * p.twinkleSpeed);
        const currentOpacity = p.opacity * (0.7 + twinkle * 0.3);
        const glowSize = p.size * (2 + twinkle);

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              backgroundColor: p.color,
              opacity: currentOpacity,
              boxShadow: `0 0 ${glowSize}px ${glowSize / 2}px ${p.color}`,
            }}
          />
        );
      })}
    </div>
  );
};

interface ConfettiProps {
  brandColor?: string;
  accentColor?: string;
  startFrame?: number;
}

export const ConfettiBurst: React.FC<ConfettiProps> = ({
  brandColor = '#6366f1',
  accentColor = '#f59e0b',
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  const pieces = Array.from({length: 20}, (_, i) => {
    const angle = (i / 20) * Math.PI * 2;
    const speed = 8 + (i % 5) * 4;
    const rotSpeed = (i % 2 === 0 ? 1 : -1) * (5 + (i % 6));
    const color = i % 3 === 0 ? accentColor : i % 2 === 0 ? brandColor : '#ffffff';
    const isRect = i % 3 !== 0;

    return {angle, speed, rotSpeed, color, isRect};
  });

  if (localFrame > 60) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
      }}
    >
      {pieces.map((p, i) => {
        const t = localFrame / 60;
        const x = Math.cos(p.angle) * p.speed * localFrame;
        const y = Math.sin(p.angle) * p.speed * localFrame + 0.5 * 2 * localFrame * localFrame * 0.1;
        const opacity = interpolate(localFrame, [0, 30, 60], [1, 0.8, 0], {
          extrapolateRight: 'clamp',
          extrapolateLeft: 'clamp',
        });
        const rotate = localFrame * p.rotSpeed;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: p.isRect ? 8 : 10,
              height: p.isRect ? 8 : 10,
              borderRadius: p.isRect ? '2px' : '50%',
              backgroundColor: p.color,
              opacity,
              transform: `translate(${x}px, ${y}px) rotate(${rotate}deg)`,
              left: 0,
              top: 0,
            }}
          />
        );
      })}
    </div>
  );
};
