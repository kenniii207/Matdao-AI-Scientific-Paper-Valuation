"use client"

import { useEffect, useRef } from "react"
import * as THREE from "three"

export function WebGLShader() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sceneRef = useRef<{
    scene: THREE.Scene | null
    camera: THREE.OrthographicCamera | null
    renderer: THREE.WebGLRenderer | null
    mesh: THREE.Mesh | null
    uniforms: any
    animationId: number | null
  }>({
    scene: null,
    camera: null,
    renderer: null,
    mesh: null,
    uniforms: null,
    animationId: null,
  })

  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const { current: refs } = sceneRef

    const vertexShader = `
      attribute vec3 position;
      void main() {
        gl_Position = vec4(position, 1.0);
      }
    `

    const fragmentShader = `
      precision highp float;
      uniform vec2 resolution;
      uniform float time;
      uniform float xScale;
      uniform float yScale;
      uniform float distortion;

      void main() {
        vec2 p = (gl_FragCoord.xy * 2.0 - resolution) / min(resolution.x, resolution.y);
        
        float d = length(p) * distortion;
        
        float rx = p.x * (1.0 + d);
        float gx = p.x;
        float bx = p.x * (1.0 - d);

        float r = 0.12 / abs(p.y + sin((rx + time) * xScale) * yScale);
        float g = 0.12 / abs(p.y + sin((gx + time) * xScale) * yScale);
        float b = 0.12 / abs(p.y + sin((bx + time) * xScale) * yScale);
        
        // High vibrancy for production visibility on all displays
        vec3 finalColor = vec3(r, g, b);
        // Ensure some alpha even for dimmer parts to prevent invisible lines
        gl_FragColor = vec4(finalColor, clamp(max(max(r, g), b) * 3.0, 0.1, 1.0));
      }
    `

    const initScene = () => {
      console.log('MatDAO: Initializing WebGL Shader...');
      refs.scene = new THREE.Scene()
      refs.renderer = new THREE.WebGLRenderer({ 
        canvas, 
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance'
      })
      refs.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      refs.renderer.setClearColor(0x000000, 0)
      console.log('MatDAO: Renderer initialized');

      refs.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, -1)

      refs.uniforms = {
        resolution: { value: [window.innerWidth, window.innerHeight] },
        time: { value: 0.0 },
        xScale: { value: 1.0 },
        yScale: { value: 0.5 },
        distortion: { value: 0.05 },
      }

      const position = [
        -1.0, -1.0, 0.0,
         1.0, -1.0, 0.0,
        -1.0,  1.0, 0.0,
         1.0, -1.0, 0.0,
        -1.0,  1.0, 0.0,
         1.0,  1.0, 0.0,
      ]

      const positions = new THREE.BufferAttribute(new Float32Array(position), 3)
      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute("position", positions)

      const material = new THREE.RawShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: refs.uniforms,
        side: THREE.DoubleSide,
        transparent: true,
      })

      refs.mesh = new THREE.Mesh(geometry, material)
      refs.scene.add(refs.mesh)

      handleResize()
    }

    let lastLogTime = 0;
    const animate = (time: number) => {
      if (!refs.renderer || !refs.scene || !refs.camera || !refs.mesh || !refs.uniforms) return
      
      const currentTime = time * 0.001
      refs.uniforms.time.value = currentTime
      refs.renderer.render(refs.scene, refs.camera)
      
      // Every 5 seconds, log a heartbeat to production console for debugging
      if (currentTime - lastLogTime > 5) {
        console.log('MatDAO Shader: Heartbeat (Looping UI Animation)...');
        lastLogTime = currentTime;
      }
      
      refs.animationId = requestAnimationFrame(animate)
    }

    const handleResize = () => {
      if (!refs.renderer || !refs.uniforms) return
      const width = window.innerWidth
      const height = window.innerHeight
      refs.renderer.setSize(width, height, false)
      refs.uniforms.resolution.value = [width, height]
    }

    initScene()
    refs.animationId = requestAnimationFrame(animate)
    window.addEventListener("resize", handleResize)

    return () => {
      if (refs.animationId) cancelAnimationFrame(refs.animationId)
      window.removeEventListener("resize", handleResize)
      if (refs.mesh) {
        refs.scene?.remove(refs.mesh)
        refs.mesh.geometry.dispose()
        if (refs.mesh.material instanceof THREE.Material) {
          refs.mesh.material.dispose()
        }
      }
      refs.renderer?.dispose()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed top-0 left-0 w-full h-full block pointer-events-none z-[1]"
      style={{ background: 'transparent', opacity: 0.99 }} // Slight opacity trick to force compositor layer
    />
  )
}

