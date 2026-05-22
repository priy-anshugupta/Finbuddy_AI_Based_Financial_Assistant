'use client';

import { CardFan3D } from '@/components/animations';

/**
 * Demo page showcasing the 3D Card Fan animation
 * Visit /demo to see the animation in action
 */
export default function DemoPage() {
  return (
    <main>
      {/* Default: Fan out on page load */}
      <CardFan3D 
        triggerOn="load"
        config={{
          fanSpreadAngle: 70,      // Wider spread
          baseTiltX: -12,          // Slight backward tilt
          depthTranslateZ: 60,     // More depth
          floatIntensity: 1.2,     // Slightly more float
          fanDuration: 0.9,        // Smooth animation
          staggerDelay: 0.08,      // Quick stagger
        }}
      />
    </main>
  );
}
