export interface MarketingVideoProps {
  title?: string;
  subtitle?: string;
  bodyText?: string;
  ctaText?: string;
  brandColor?: string;
  accentColor?: string;
  backgroundType?: 'gradient' | 'particles' | 'solid';
  logoText?: string;
  hashtags?: string[];
  socialHandle?: string;
  bulletPoints?: string[];
}

export const defaultProps: Required<MarketingVideoProps> = {
  title: 'Transform Your Business',
  subtitle: 'AI-Powered Marketing Solutions',
  bodyText: 'Reach your audience at scale with intelligent automation.',
  ctaText: 'Get Started Today',
  brandColor: '#6366f1',
  accentColor: '#f59e0b',
  backgroundType: 'gradient',
  logoText: 'MAMA',
  hashtags: ['#Marketing', '#AI', '#Growth'],
  socialHandle: '@mama.ai',
  bulletPoints: [
    '✦ Automated content creation',
    '✦ Multi-platform publishing',
    '✦ AI-driven insights',
    '✦ Real-time analytics',
  ],
};
