"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { TypeAnimation } from "react-type-animation"
import { WebGLShader } from "./web-gl-shader"

interface LoadingScreenProps {
  onLoadingComplete?: () => void
}

export function LoadingScreen({ onLoadingComplete }: LoadingScreenProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Assets to preload
    const imageUrls = [
      "https://images.unsplash.com/photo-1581092335397-9583eb92d232?auto=format&fit=crop&w=900&q=80",
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80",
      "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80"
    ]

    let loadedCount = 0
    const totalAssets = imageUrls.length

    const handleAssetLoad = () => {
      loadedCount++
      const newProgress = Math.round((loadedCount / totalAssets) * 100)
      setProgress(newProgress)
      
      if (loadedCount === totalAssets) {
        // Add a slight artificial delay for a smoother feel
        setTimeout(() => {
          setIsLoaded(true)
          if (onLoadingComplete) {
            onLoadingComplete()
          }
        }, 1800)
      }
    }

    imageUrls.forEach(url => {
      const img = new Image()
      img.src = url
      img.onload = handleAssetLoad
      img.onerror = handleAssetLoad // Continue even if one fails
    })
    
    // Fallback if images take too long
    const timeout = setTimeout(() => {
      if (loadedCount < totalAssets) {
        setIsLoaded(true)
        if (onLoadingComplete) onLoadingComplete()
      }
    }, 5000)

    return () => clearTimeout(timeout)
  }, [onLoadingComplete])

  return (
    <AnimatePresence>
      {!isLoaded && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.8, ease: [0.43, 0.13, 0.23, 0.96] }}
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-black overflow-hidden"
        >
          {/* Background Layer: Shader */}
          <WebGLShader />
          
          {/* Overlay Vignet */}
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-0" />

          {/* Center Content */}
          <div className="relative z-10 flex flex-col items-center">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-4xl md:text-6xl font-headline font-extrabold tracking-tighter text-white/95 mb-8"
            >
              <TypeAnimation
                sequence={["MatDAO", 1000]}
                wrapper="span"
                cursor={true}
                repeat={0}
                className="text-[#89fdff] drop-shadow-[0_0_20px_rgba(137,253,255,0.4)]"
              />
            </motion.div>

            {/* Micro progress indicator */}
            <div className="w-48 h-[2px] bg-white/10 rounded-full overflow-hidden relative">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-[#89fdff] to-cyan-400 shadow-[0_0_10px_#89fdff]"
              />
            </div>
            <motion.span 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 text-[10px] uppercase tracking-[0.3em] text-white/40 font-medium"
            >
              Synchronizing Protocol
            </motion.span>
          </div>

          {/* Glowing bottom accent */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-cyan-500/10 blur-[120px] rounded-full pointer-events-none" />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
