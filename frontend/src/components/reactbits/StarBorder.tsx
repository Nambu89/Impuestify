// Based on React Bits StarBorder (MIT via reactbits.dev)
import React from 'react'
import './StarBorder.css'

interface StarBorderProps {
  className?: string
  children?: React.ReactNode
  color?: string
  speed?: string
}

export default function StarBorder({
  className = '',
  color = '#1a56db',
  speed = '6s',
  children,
}: StarBorderProps) {
  return (
    <div className={`star-border-container ${className}`}>
      <div
        className="border-gradient-bottom"
        style={{
          background: `radial-gradient(circle, ${color}, transparent 10%)`,
          animationDuration: speed,
        }}
      />
      <div
        className="border-gradient-top"
        style={{
          background: `radial-gradient(circle, ${color}, transparent 10%)`,
          animationDuration: speed,
        }}
      />
      <div className="star-border-inner">{children}</div>
    </div>
  )
}
