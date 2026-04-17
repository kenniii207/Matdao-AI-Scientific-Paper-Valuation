"use client"

import { useEffect, useRef, useState } from "react"
import * as THREE from "three"

type ShaderUniforms = {
  resolution: THREE.IUniform<THREE.Vector2>
  time: THREE.IUniform<number>
  xScale: THREE.IUniform<number>
  yScale: THREE.IUniform<number>
  distortion: THREE.IUniform<number>
}

type SceneRefs = {
  scene: THREE.Scene | null
  camera: THREE.OrthographicCamera | null
  renderer: THREE.WebGLRenderer | null
  mesh: THREE.Mesh | null
  uniforms: ShaderUniforms | null
  animationId: number | null
}

export function WebGLShader({ disableShader = false }: { disableShader?: boolean }) {
  const [fallbackMode, setFallbackMode] = useState(disableShader)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sceneRef = useRef<SceneRefs>({
    scene: null,
    camera: null,
    renderer: null,
    mesh: null,
    uniforms: null,
    animationId: null,
  })

  useEffect(() => {
    if (!canvasRef.current || disableShader) {
      setFallbackMode(true)
      return
    }

    const canvas = canvasRef.current
    const { current: refs } = sceneRef
    let isDisposed = false

    const setFallback = () => {
      if (!isDisposed) setFallbackMode(true)
    }

    const context =
      canvas.getContext("webgl2", {
        alpha: true,
        antialias: false,
        powerPreference: "default",
      }) ||
      canvas.getContext("webgl", {
        alpha: true,
        antialias: false,
        powerPreference: "default",
      })

    if (!context) {
      setFallback()
      return
    }

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

        // Clamp denominator so low-precision GPUs do not collapse to NaN/Inf.
        float rDen = max(abs(p.y + sin((rx + time) * xScale) * yScale), 0.03);
        float gDen = max(abs(p.y + sin((gx + time) * xScale) * yScale), 0.03);
        float bDen = max(abs(p.y + sin((bx + time) * xScale) * yScale), 0.03);

        float r = 0.12 / rDen;
        float g = 0.12 / gDen;
        float b = 0.12 / bDen;

        vec3 finalColor = vec3(r, g, b);
        gl_FragColor = vec4(finalColor, clamp(max(max(r, g), b) * 3.0, 0.1, 1.0));
      }
    `

    const initScene = () => {
      refs.scene = new THREE.Scene()
      try {
        refs.renderer = new THREE.WebGLRenderer({
          canvas,
          context: context as WebGLRenderingContext | WebGL2RenderingContext,
          alpha: true,
          antialias: false,
          powerPreference: "default",
        })
      } catch {
        setFallback()
        return false
      }
      refs.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      refs.renderer.setClearColor(0x000000, 0)

      refs.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10)
      refs.camera.position.z = 1

      refs.uniforms = {
        resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
        time: { value: 0.0 },
        xScale: { value: 1.0 },
        yScale: { value: 0.5 },
        distortion: { value: 0.05 },
      }

      const positions = new THREE.BufferAttribute(
        new Float32Array([
          -1.0, -1.0, 0.0,
           1.0, -1.0, 0.0,
          -1.0,  1.0, 0.0,
           1.0, -1.0, 0.0,
          -1.0,  1.0, 0.0,
           1.0,  1.0, 0.0,
        ]),
        3
      )
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
      setFallbackMode(false)
      return true
    }

    const animate = (time: number) => {
      if (!refs.renderer || !refs.scene || !refs.camera || !refs.mesh || !refs.uniforms) return
      refs.uniforms.time.value = time * 0.001
      refs.renderer.render(refs.scene, refs.camera)
      refs.animationId = requestAnimationFrame(animate)
    }

    const handleResize = () => {
      if (!refs.renderer || !refs.uniforms) return
      const width = window.innerWidth
      const height = window.innerHeight
      refs.renderer.setSize(width, height, false)
      refs.uniforms.resolution.value.set(width, height)
    }

    const handleContextLost = (event: Event) => {
      event.preventDefault()
      setFallback()
    }

    canvas.addEventListener("webglcontextlost", handleContextLost, false)

    if (initScene()) {
      handleResize()
      refs.animationId = requestAnimationFrame(animate)
      window.addEventListener("resize", handleResize)
    }

    return () => {
      isDisposed = true
      if (refs.animationId) cancelAnimationFrame(refs.animationId)
      window.removeEventListener("resize", handleResize)
      canvas.removeEventListener("webglcontextlost", handleContextLost)
      if (refs.mesh) {
        refs.scene?.remove(refs.mesh)
        refs.mesh.geometry.dispose()
        if (refs.mesh.material instanceof THREE.Material) {
          refs.mesh.material.dispose()
        }
      }
      refs.renderer?.dispose()
    }
  }, [disableShader])

  return (
    <div className="fixed inset-0 pointer-events-none z-[1]" aria-hidden="true">
      <canvas
        ref={canvasRef}
        className={fallbackMode ? "hidden" : "h-full w-full block"}
        style={{ background: "transparent", opacity: fallbackMode ? 0 : 0.99 }}
      />
      <div className={`light-string-fallback ${fallbackMode ? "opacity-100" : "opacity-80"}`}>
        <div className="light-string-fallback__rainbow" />
        <div className="light-string-fallback__core" />
      </div>
    </div>
  )
}
