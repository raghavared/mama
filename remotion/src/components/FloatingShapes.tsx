import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';

interface FloatingShapesProps {
  brandColor?: string;
  accentColor?: string;
  count?: number;
}

export const FloatingShapes: React.FC<FloatingShapesProps> = ({
  brandColor = '#6366f1',
  accentColor = '#f59e0b',
  count = 6,
}) => {
  const frame = useCurrentFrame();

  const shapes = Array.from({length: count}, (_, i) => {
    const seed = (i + 1) * 137.508;
    const x = (seed * 3) % 80 + 10;
    const y = (seed * 7) % 80 + 10;
    const size = 30 + (i % 5) * 20;
    const isCircle = i % 2 === 0;
    const color = i % 3 === 0 ? accentColor : brandColor;
    const rotSpeed = (i % 2 === 0 ? 1 : -1) * (0.3 + (i % 3) * 0.2);
    const floatSpeed = 0.5 + (i % 4) * 0.3;
    const floatAmp = 10 + (i % 3) * 8;
    const delay = i * 15;

    return {x, y, size, isCircle, color, rotSpeed, floatSpeed, floatAmp, delay};
  });

  return (
    <>
      {shapes.map((shape, i) => {
        const adjustedFrame = Math.max(0, frame - shape.delay);
        const appear = interpolate(adjustedFrame, [0, 30], [0, 1], {
          extrapolateRight: 'clamp',
          extrapolateLeft: 'clamp',
        });
        const floatY = Math.sin((frame / 30) * shape.floatSpeed) * shape.floatAmp;
        const rotate = frame * shape.rotSpeed;
        const scale = 0.8 + Math.sin((frame / 60) * shape.floatSpeed) * 0.1;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
              width: shape.size,
              height: shape.size,
              borderRadius: shape.isCircle ? '50%' : '4px',
              border: `2px solid ${shape.color}`,
              backgroundColor: `${shape.color}11`,
              opacity: appear * 0.4,
              transform: `translateY(${floatY}px) rotate(${rotate}deg) scale(${scale})`,
              boxShadow: `0 0 15px ${shape.color}33`,
            }}
          />
        );
      })}
    </>
  );
};

interface RingProps {
  brandColor?: string;
  accentColor?: string;
}

export const AnimatedRings: React.FC<RingProps> = ({
  brandColor = '#6366f1',
  accentColor = '#f59e0b',
}) => {
  const frame = useCurrentFrame();

  const rings = [
    {size: 200, color: brandColor, speed: 0.8, delay: 0},
    {size: 350, color: accentColor, speed: -0.5, delay: 10},
    {size: 500, color: brandColor, speed: 0.3, delay: 20},
  ];

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      }}
    >
      {rings.map((ring, i) => {
        const adjustedFrame = Math.max(0, frame - ring.delay);
        const opacity = interpolate(adjustedFrame, [0, 40], [0, 0.3], {
          extrapolateRight: 'clamp',
          extrapolateLeft: 'clamp',
        });
        const rotate = frame * ring.speed;
        const scale = 1 + Math.sin((frame / 60) * 0.5) * 0.05;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: ring.size,
              height: ring.size,
              borderRadius: '50%',
              border: `1px solid ${ring.color}`,
              left: -ring.size / 2,
              top: -ring.size / 2,
              opacity,
              transform: `rotate(${rotate}deg) scale(${scale})`,
              boxShadow: `0 0 20px ${ring.color}22, inset 0 0 20px ${ring.color}11`,
            }}
          />
        );
      })}
    </div>
  );
};
