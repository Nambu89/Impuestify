// Lightweight FadeContent using IntersectionObserver (no GSAP dependency)
import React, { useRef, useEffect, useState } from 'react'

interface FadeContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  blur?: boolean
  duration?: number
  delay?: number
  threshold?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
  distance?: number
  stagger?: number
}

const FadeContent: React.FC<FadeContentProps> = ({
  children,
  blur = false,
  duration = 600,
  delay = 0,
  threshold = 0.1,
  direction = 'up',
  distance = 30,
  className = '',
  style,
  ...props
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // If element is already in viewport on mount (above the fold), show immediately
    const rect = el.getBoundingClientRect()
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      setIsVisible(true)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.disconnect()
        }
      },
      { threshold },
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold])

  const getTransform = () => {
    if (direction === 'up') return `translateY(${distance}px)`
    if (direction === 'down') return `translateY(-${distance}px)`
    if (direction === 'left') return `translateX(${distance}px)`
    if (direction === 'right') return `translateX(-${distance}px)`
    return 'none'
  }

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'none' : getTransform(),
        filter: blur ? (isVisible ? 'blur(0px)' : 'blur(8px)') : undefined,
        transition: `opacity ${duration}ms ease ${delay}ms, transform ${duration}ms ease ${delay}ms${blur ? `, filter ${duration}ms ease ${delay}ms` : ''}`,
        willChange: 'opacity, transform',
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  )
}

export default FadeContent
