"use client"

import { useEffect, useRef } from "react"
import { useTheme } from "@/contexts/theme-context"

interface Point {
  x: number
  y: number
  vx: number
  vy: number
}

export function NeuralGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationId: number
    let points: Point[] = []
    const numPoints = 50
    const connectionDistance = 150
    const pointSpeed = 0.3

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    const initPoints = () => {
      points = []
      for (let i = 0; i < numPoints; i++) {
        points.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * pointSpeed,
          vy: (Math.random() - 0.5) * pointSpeed,
        })
      }
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Colors based on theme
      const dotColor = theme === "dark" ? "rgba(129, 140, 248, 0.6)" : "rgba(212, 168, 83, 0.5)"
      const lineColor = theme === "dark" ? "rgba(129, 140, 248, 0.15)" : "rgba(212, 168, 83, 0.12)"

      // Update and draw points
      points.forEach((point, i) => {
        // Update position
        point.x += point.vx
        point.y += point.vy

        // Bounce off walls
        if (point.x < 0 || point.x > canvas.width) point.vx *= -1
        if (point.y < 0 || point.y > canvas.height) point.vy *= -1

        // Keep in bounds
        point.x = Math.max(0, Math.min(canvas.width, point.x))
        point.y = Math.max(0, Math.min(canvas.height, point.y))

        // Draw connections
        for (let j = i + 1; j < points.length; j++) {
          const other = points[j]
          const dx = point.x - other.x
          const dy = point.y - other.y
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance < connectionDistance) {
            const opacity = 1 - distance / connectionDistance
            ctx.beginPath()
            ctx.strokeStyle = lineColor.replace("0.15", String(opacity * 0.15)).replace("0.12", String(opacity * 0.12))
            ctx.lineWidth = 1
            ctx.moveTo(point.x, point.y)
            ctx.lineTo(other.x, other.y)
            ctx.stroke()
          }
        }

        // Draw point
        ctx.beginPath()
        ctx.arc(point.x, point.y, 2, 0, Math.PI * 2)
        ctx.fillStyle = dotColor
        ctx.fill()
      })

      animationId = requestAnimationFrame(animate)
    }

    resize()
    initPoints()
    animate()

    window.addEventListener("resize", () => {
      resize()
      initPoints()
    })

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener("resize", resize)
    }
  }, [theme])

  return (
    <canvas
      ref={canvasRef}
      className="neural-grid"
      aria-hidden="true"
    />
  )
}