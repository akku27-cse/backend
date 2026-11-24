import React, { useEffect, useRef } from 'react'

// Orthographic projection of a tilted celestial globe and its orbital planes.
export default function Atlas() {
  const ref = useRef(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    function paint() {
      const { width, height } = canvas.getBoundingClientRect()
      if (!width || !height) return
      const scale = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)
      ctx.scale(scale, scale)
      const cx = width * .66, cy = height * .49, radius = Math.min(height * .35, width * .24)
      const tilt = -.38, pitch = .30
      function project(x, y, z) {
        const py = y * Math.cos(pitch) - z * Math.sin(pitch)
        return [cx + radius * (x * Math.cos(tilt) - py * Math.sin(tilt)),
          cy + radius * (x * Math.sin(tilt) + py * Math.cos(tilt)),
          y * Math.sin(pitch) + z * Math.cos(pitch)]
      }
      let seed = 9751
      const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
      for (let i = 0; i < 145; i++) {
        const x = random() * width, y = random() * height
        const intensity = random()
        ctx.fillStyle = 'rgba(239,224,184,' + (.19 + intensity * .64) + ')'
        ctx.beginPath()
        ctx.arc(x, y, intensity > .94 ? 1.3 : .56, 0, Math.PI * 2)
        ctx.fill()
        if (intensity > .984) { ctx.fillRect(x - 3, y - .45, 6, .9); ctx.fillRect(x - .45, y - 3, .9, 6) }
      }
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 1.65)
      glow.addColorStop(0, 'rgba(214,170,101,.12)')
      glow.addColorStop(.65, 'rgba(214,170,101,.05)')
      glow.addColorStop(1, 'rgba(214,170,101,0)')
      ctx.fillStyle = glow
      ctx.fillRect(0, 0, width, height)
      function curve(point, color, weight = 1, frontOnly = false) {
        ctx.strokeStyle = color
        ctx.lineWidth = weight
        ctx.beginPath()
        let drawing = false
        for (let i = 0; i <= 220; i++) {
          const [x, y, z] = point(i * Math.PI / 110)
          if (frontOnly && z < 0) { drawing = false; continue }
          if (drawing) ctx.lineTo(x, y)
          else ctx.moveTo(x, y)
          drawing = true
        }
        ctx.stroke()
      }
      const copper = 'rgba(219,184,131,.55)'
      for (let latitude = -75; latitude <= 75; latitude += 15) {
        const a = latitude * Math.PI / 180
        const point = t => project(Math.cos(a) * Math.cos(t), Math.sin(a), Math.cos(a) * Math.sin(t))
        curve(point, 'rgba(202,175,129,.14)', .65)
        curve(point, copper, .8, true)
      }
      for (let i = 0; i < 12; i++) {
        const a = i * Math.PI / 12
        const point = t => project(Math.cos(t) * Math.cos(a), Math.sin(t), Math.cos(t) * Math.sin(a))
        curve(point, 'rgba(211,183,138,.14)', .65)
        curve(point, copper, .8, true)
      }
      ctx.strokeStyle = '#cab18a'
      ctx.lineWidth = 1.05
      ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke()
      function orbit(rx, ry, angle, color, dashed = false) {
        ctx.setLineDash(dashed ? [2, 5] : [])
        ctx.strokeStyle = color
        ctx.beginPath()
        ctx.ellipse(cx, cy, radius * rx, radius * ry, angle, 0, Math.PI * 2)
        ctx.stroke()
        ctx.setLineDash([])
      }
      orbit(1.82, .38, -.36, '#d4b582')
      orbit(1.48, .65, -.79, 'rgba(221,201,156,.45)')
      orbit(1.23, 1.23, 0, 'rgba(219,199,154,.37)', true)
      const ax = cx - radius * 1.82 * Math.cos(.36), ay = cy + radius * 1.82 * Math.sin(.36)
      ctx.beginPath(); ctx.fillStyle = '#f6cc81'; ctx.arc(ax, ay, 3, 0, Math.PI * 2); ctx.fill()
    }
    const observer = new ResizeObserver(paint)
    observer.observe(canvas)
    paint()
    return () => observer.disconnect()
  }, [])
  return <canvas ref={ref} className="atlas" aria-hidden="true" />
}
