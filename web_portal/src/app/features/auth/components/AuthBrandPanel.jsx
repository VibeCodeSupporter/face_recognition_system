import { useEffect, useRef } from 'react'
import { Typography } from 'antd'
import BrandMark from '../../../components/BrandMark.jsx'
import './AuthBrandPanel.css'

function NeuralNetworkCanvas() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) return undefined

    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const pointer = { x: 0, y: 0, active: false, gatherUntil: 0 }
    let width = 0
    let height = 0
    let pixelRatio = 1
    let nodes = []
    let stars = []
    let frameId = 0
    let previousTime = 0

    const random = (min, max) => min + Math.random() * (max - min)

    const resize = () => {
      const bounds = canvas.getBoundingClientRect()
      const nextWidth = Math.max(1, bounds.width)
      const nextHeight = Math.max(1, bounds.height)
      const ratioX = width ? nextWidth / width : 1
      const ratioY = height ? nextHeight / height : 1
      width = nextWidth
      height = nextHeight
      pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(width * pixelRatio)
      canvas.height = Math.round(height * pixelRatio)
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

      const count = Math.min(135, Math.max(54, Math.round((width * height) / 6200)))
      if (nodes.length === 0) {
        nodes = Array.from({ length: count }, () => ({
          x: random(0, width), y: random(0, height),
          vx: random(-0.22, 0.22), vy: random(-0.22, 0.22),
          radius: random(1.1, 2.5), phase: random(0, Math.PI * 2),
          gatherX: 0, gatherY: 0,
        }))
      } else {
        nodes.forEach((node) => { node.x *= ratioX; node.y *= ratioY })
        nodes = nodes.slice(0, count)
        while (nodes.length < count) nodes.push({
          x: random(0, width), y: random(0, height),
          vx: random(-0.22, 0.22), vy: random(-0.22, 0.22),
          radius: random(1.1, 2.5), phase: random(0, Math.PI * 2), gatherX: 0, gatherY: 0,
        })
      }
      stars = Array.from({ length: Math.max(24, Math.round((width * height) / 8500)) }, () => ({
        x: random(0, width), y: random(0, height), phase: random(0, Math.PI * 2), size: random(0.4, 1.25),
      }))
    }

    const updatePointer = (event) => {
      const bounds = canvas.getBoundingClientRect()
      pointer.x = event.clientX - bounds.left
      pointer.y = event.clientY - bounds.top
      pointer.active = true
    }
    const leavePointer = () => { pointer.active = false }

    const gatherNodes = (event) => {
      updatePointer(event)
      const now = performance.now()
      pointer.gatherUntil = now + 1250
      nodes.forEach((node) => {
        const angle = random(0, Math.PI * 2)
        const radius = random(8, 70)
        node.gatherX = pointer.x + Math.cos(angle) * radius
        node.gatherY = pointer.y + Math.sin(angle) * radius
      })
    }

    const render = (time) => {
      frameId = requestAnimationFrame(render)
      if (motionPreference.matches && time - previousTime < 80) return
      const elapsed = previousTime ? Math.min((time - previousTime) / 16.67, 2) : 1
      previousTime = time
      context.clearRect(0, 0, width, height)

      stars.forEach((star) => {
        const shimmer = 0.22 + (Math.sin(time * 0.0013 + star.phase) + 1) * 0.3
        context.fillStyle = `rgba(190, 230, 255, ${shimmer})`
        context.beginPath()
        context.arc(star.x, star.y, star.size, 0, Math.PI * 2)
        context.fill()
      })

      const gathering = time < pointer.gatherUntil
      nodes.forEach((node) => {
        if (gathering) {
          node.vx += (node.gatherX - node.x) * 0.0065 * elapsed
          node.vy += (node.gatherY - node.y) * 0.0065 * elapsed
        } else if (pointer.active) {
          const dx = pointer.x - node.x
          const dy = pointer.y - node.y
          const distance = Math.hypot(dx, dy)
          if (distance < 190 && distance > 1) {
            const pull = (1 - distance / 190) * 0.0018 * elapsed
            node.vx += dx * pull
            node.vy += dy * pull
          }
        }

        node.vx += Math.sin(time * 0.00028 + node.phase) * 0.006 * elapsed
        node.vy += Math.cos(time * 0.00024 + node.phase) * 0.006 * elapsed
        node.vx *= 0.994
        node.vy *= 0.994
        node.x += node.vx * elapsed
        node.y += node.vy * elapsed
        if (node.x < 0 || node.x > width) node.vx *= -1
        if (node.y < 0 || node.y > height) node.vy *= -1
        node.x = Math.max(0, Math.min(width, node.x))
        node.y = Math.max(0, Math.min(height, node.y))
      })

      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const first = nodes[i]
          const second = nodes[j]
          const distance = Math.hypot(first.x - second.x, first.y - second.y)
          if (distance < 128) {
            const alpha = (1 - distance / 128) * 0.38
            context.strokeStyle = `rgba(102, 199, 255, ${alpha})`
            context.lineWidth = 0.7
            context.beginPath()
            context.moveTo(first.x, first.y)
            context.lineTo(second.x, second.y)
            context.stroke()
          }
        }
      }

      nodes.forEach((node) => {
        const twinkle = 0.66 + (Math.sin(time * 0.0018 + node.phase) + 1) * 0.17
        context.shadowBlur = 12
        context.shadowColor = 'rgba(104, 206, 255, 0.8)'
        context.fillStyle = `rgba(203, 240, 255, ${twinkle})`
        context.beginPath()
        context.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
        context.fill()
      })
      context.shadowBlur = 0
    }

    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    canvas.addEventListener('pointermove', updatePointer)
    canvas.addEventListener('pointerleave', leavePointer)
    canvas.addEventListener('pointerdown', gatherNodes)
    frameId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(frameId)
      observer.disconnect()
      canvas.removeEventListener('pointermove', updatePointer)
      canvas.removeEventListener('pointerleave', leavePointer)
      canvas.removeEventListener('pointerdown', gatherNodes)
    }
  }, [])

  return <canvas ref={canvasRef} className="auth-brand__network" aria-hidden="true" />
}

export default function AuthBrandPanel() {
  return (
    <div className="auth-brand">
      <div className="auth-brand__top"><BrandMark tone="light" /></div>
      <div className="auth-brand__body">
        <div className="auth-brand__eyebrow"><span className="auth-brand__live-dot" /> FACEACCESS</div>
        <Typography.Title level={1} className="auth-brand__headline">
          Giải pháp nhận diện khuôn mặt hiệu quả.
        </Typography.Title>
        <Typography.Paragraph className="auth-brand__description">
          Hệ thống kiểm soát ra vào bằng khuôn mặt, kết nối nhân sự và thiết bị trong một nền tảng.
        </Typography.Paragraph>
        <div className="auth-brand__visual"><NeuralNetworkCanvas /></div>
      </div>
      <footer className="auth-brand__footer">
        <span className="auth-brand__copyright">© {new Date().getFullYear()} Bản quyền thuộc về sinh viên Trường Đại học Công nghiệp Hà Nội</span>
        <span className="auth-brand__university-logo"><img src="/haui-logo.jpg" alt="Logo Đại học Công nghiệp Hà Nội (HaUI)" /></span>
      </footer>
    </div>
  )
}
