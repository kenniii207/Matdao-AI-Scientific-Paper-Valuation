'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

type SceneRefs = {
  scene: THREE.Scene | null;
  camera: THREE.OrthographicCamera | null;
  renderer: THREE.WebGLRenderer | null;
  mesh: THREE.Mesh | null;
  uniforms: {
    resolution: { value: [number, number] };
    time: { value: number };
    xScale: { value: number };
    yScale: { value: number };
    distortion: { value: number };
  } | null;
  animationId: number | null;
};

export function WebGLShader() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<SceneRefs>({
    scene: null,
    camera: null,
    renderer: null,
    mesh: null,
    uniforms: null,
    animationId: null,
  });

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const { current: refs } = sceneRef;

    const vertexShader = `
      attribute vec3 position;
      void main() {
        gl_Position = vec4(position, 1.0);
      }
    `;

    const fragmentShader = `
      precision highp float;
      uniform vec2 resolution;
      uniform float time;
      uniform float xScale;
      uniform float yScale;
      uniform float distortion;

      void main() {
        vec2 p = (gl_FragCoord.xy * 2.0 - resolution) / min(resolution.x, resolution.y);
        
        float t = time * 0.3;
        
        // Flowing distortion
        p.x += sin(t * 0.7 + p.y * 2.5) * 0.4;
        p.y += cos(t * 0.5 + p.x * 2.0) * 0.4;
        
        float r = 0.06 / abs(p.y + sin((p.x + t) * 1.5) * 0.4);
        float g = 0.06 / abs(p.y + sin((p.x + t * 1.2) * 1.6) * 0.4);
        float b = 0.06 / abs(p.y + sin((p.x + t * 1.4) * 1.7) * 0.4);
        
        // Flowing cyan-indigo aesthetic themes
        vec3 color = vec3(r * 0.2, g * 0.6, b * 0.9);
        
        gl_FragColor = vec4(color, 1.0);
      }
    `;

    const handleResize = () => {
      if (!refs.renderer || !refs.uniforms) return;
      const width = window.innerWidth;
      const height = window.innerHeight;
      refs.renderer.setSize(width, height, false);
      refs.uniforms.resolution.value = [width, height];
    };

    const initScene = () => {
      refs.scene = new THREE.Scene();
      refs.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: 'high-performance' });
      refs.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      refs.renderer.setClearColor(0x000000, 0);

      refs.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, -1);
      refs.uniforms = {
        resolution: { value: [window.innerWidth, window.innerHeight] },
        time: { value: 0.0 },
        xScale: { value: 1.0 },
        yScale: { value: 0.5 },
        distortion: { value: 0.045 },
      };

      const position = [
        -1.0, -1.0, 0.0,
         1.0, -1.0, 0.0,
        -1.0,  1.0, 0.0,
         1.0, -1.0, 0.0,
        -1.0,  1.0, 0.0,
         1.0,  1.0, 0.0,
      ];

      const positions = new THREE.BufferAttribute(new Float32Array(position), 3);
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', positions);

      const material = new THREE.RawShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: refs.uniforms,
        side: THREE.DoubleSide,
      });

      refs.mesh = new THREE.Mesh(geometry, material);
      refs.scene.add(refs.mesh);
      handleResize();
    };

    const animate = () => {
      if (refs.uniforms) refs.uniforms.time.value += 0.008;
      if (refs.renderer && refs.scene && refs.camera) refs.renderer.render(refs.scene, refs.camera);
      refs.animationId = requestAnimationFrame(animate);
    };

    const onVisibility = () => {
      if (document.hidden && refs.animationId) {
        cancelAnimationFrame(refs.animationId);
        refs.animationId = null;
      } else if (!document.hidden && !refs.animationId) {
        animate();
      }
    };

    initScene();
    animate();
    window.addEventListener('resize', handleResize);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      if (refs.animationId) cancelAnimationFrame(refs.animationId);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', onVisibility);
      if (refs.mesh) {
        refs.scene?.remove(refs.mesh);
        refs.mesh.geometry.dispose();
        if (refs.mesh.material instanceof THREE.Material) refs.mesh.material.dispose();
      }
      refs.renderer?.dispose();
    };
  }, []);

  return <canvas ref={canvasRef} className="fixed inset-0 h-full w-full block pointer-events-none -z-10" />;
}
