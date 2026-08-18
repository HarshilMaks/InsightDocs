import React from 'react';

interface BrandLogoProps {
  size?: number | string;
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ size = 32, className = '' }) => {
  return (
    <div 
      className={`inline-flex items-center justify-center shrink-0 select-none ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-[0_4px_12px_rgba(224,26,138,0.35)]"
      >
        <defs>
          {/* Main Hexagon Vibrant Magenta-Purple Gradient */}
          <linearGradient id="brandHexGradient" x1="180" y1="20" x2="20" y2="180" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FF0080" />
            <stop offset="35%" stopColor="#E6007A" />
            <stop offset="70%" stopColor="#8A14E6" />
            <stop offset="100%" stopColor="#5312E6" />
          </linearGradient>

          {/* Left/Bottom Deep Curved Shadow on Hexagon Fold */}
          <linearGradient id="brandFoldShadow" x1="40" y1="80" x2="100" y2="160" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3C096C" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#240046" stopOpacity="0" />
          </linearGradient>

          {/* Inner 3D Drop Shadow for Ribbon */}
          <filter id="ribbonShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="-2" dy="4" stdDeviation="4" floodColor="#1a0033" floodOpacity="0.45" />
          </filter>

          {/* Top Fold Shadow on Ribbon */}
          <linearGradient id="innerFoldGradient" x1="70" y1="70" x2="130" y2="130" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#200040" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#200040" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Outer Rounded Hexagon Background */}
        <path
          d="M 100 12 
             C 108 12, 114 15, 172 48 
             C 180 52, 185 60, 185 70 
             L 185 130 
             C 185 140, 180 148, 172 152 
             L 114 185 
             C 106 189, 94 189, 86 185 
             L 28 152 
             C 20 148, 15 140, 15 130 
             L 15 70 
             C 15 60, 20 52, 28 48 
             L 86 15 
             C 92 12, 96 12, 100 12 Z"
          fill="url(#brandHexGradient)"
        />

        {/* 3D Curvature depth layer on lower left bevel */}
        <path
          d="M 15 70 
             C 15 60, 20 52, 28 48 
             L 75 22 
             C 50 55, 45 100, 75 145 
             L 28 152 
             C 20 148, 15 140, 15 130 Z"
          fill="#3A0868"
          fillOpacity="0.3"
        />

        {/* Inner Dark Cutout / Negative Cavity for 3D depth */}
        <path
          d="M 68 76 
             L 112 52 
             C 122 47, 134 53, 134 65 
             L 134 105 
             L 88 130 
             C 74 138, 62 128, 62 115 
             L 62 85 
             C 62 80, 64 78, 68 76 Z"
          fill="#35065E"
          fillOpacity="0.65"
        />

        {/* Stylized White "S" 3D Ribbon Structure */}
        {/* Upper S Arm & Diagonal */}
        <path
          d="M 172 90 
             L 112 56 
             C 98 48, 76 58, 76 74 
             L 76 86 
             C 76 96, 84 104, 94 110 
             L 130 130 
             C 142 137, 142 153, 130 160 
             L 70 142 
             C 62 139, 62 129, 62 124 
             L 62 110 
             L 92 127 
             C 100 131, 110 128, 114 122 
             L 114 108 
             C 114 98, 106 91, 96 85 
             L 80 76 
             C 68 69, 68 53, 80 46 
             L 138 64 
             C 148 67, 158 74, 172 82 Z"
          fill="#FFFFFF"
          filter="url(#ribbonShadow)"
        />

        {/* Exact Precision S-Curve Continuous White Ribbon */}
        <path
          d="M 168 96 
             L 126 72 
             C 116 66, 102 62, 88 70 
             C 76 77, 72 90, 78 102 
             C 82 109, 90 114, 98 119 
             L 124 134 
             C 134 140, 138 150, 132 159 
             C 126 166, 112 170, 98 162 
             L 70 146 
             L 70 122 
             L 94 136 
             C 102 141, 112 140, 116 134 
             C 120 128, 118 120, 110 115 
             L 86 101 
             C 74 94, 66 84, 68 70 
             C 70 54, 86 42, 104 42 
             C 118 42, 134 48, 150 58 
             L 168 68 Z"
          fill="#FFFFFF"
        />

        {/* Ambient occlusion shadow under the central crossing fold */}
        <path
          d="M 86 101 
             L 110 115 
             C 106 122, 98 122, 94 118 
             Z"
          fill="url(#innerFoldGradient)"
        />

        {/* Highlight sheen along top edge */}
        <path
          d="M 100 14 
             L 168 52 
             C 174 55, 178 61, 178 68 
             L 178 74 
             C 178 67, 174 61, 168 58 
             L 100 20 
             C 94 17, 88 17, 82 20 
             L 28 50 
             C 24 52, 20 56, 20 62 
             C 20 57, 24 53, 28 51 
             L 82 21 
             C 88 17, 94 14, 100 14 Z"
          fill="#FFFFFF"
          fillOpacity="0.4"
        />
      </svg>
    </div>
  );
};
