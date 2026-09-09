import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { SpacePoint } from '../data/schema'
import { useLocale } from '../i18n/LocaleProvider'
import { groupLabel } from '../i18n/research'
import { buildNeighborEdges, constellationProfile, scenePosition, visualState } from './constellation'

interface Pca3DProps {
  points: SpacePoint[]
  selectedId?: string
  showNeighbors: boolean
  autoRotate: boolean
  resetKey: number
  explainedVariance: number[]
  onSelect: (point: SpacePoint) => void
}

interface SceneNode {
  point: SpacePoint
  mesh: THREE.Mesh
  material: THREE.MeshStandardMaterial
  glow: THREE.Sprite
  glowMaterial: THREE.SpriteMaterial
  ring?: THREE.Mesh
  ringMaterial?: THREE.MeshBasicMaterial
}

export default function Pca3D({
  points,
  selectedId,
  showNeighbors,
  autoRotate,
  resetKey,
  explainedVariance,
  onSelect,
}: Pca3DProps) {
  const { locale, t } = useLocale()
  const hostRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const tooltipTitleRef = useRef<HTMLElement>(null)
  const tooltipMetaRef = useRef<HTMLElement>(null)
  const tooltipPcaRef = useRef<HTMLElement>(null)
  const updateVisualRef = useRef<((id?: string, neighbors?: boolean) => void) | null>(null)
  const resetViewRef = useRef<(() => void) | null>(null)
  const autoRotateRef = useRef(autoRotate)
  const showNeighborsRef = useRef(showNeighbors)
  const selectedIdRef = useRef(selectedId)
  const userInteractedRef = useRef(false)

  useEffect(() => {
    autoRotateRef.current = autoRotate
    if (autoRotate) userInteractedRef.current = false
  }, [autoRotate])

  useEffect(() => {
    selectedIdRef.current = selectedId
    showNeighborsRef.current = showNeighbors
    updateVisualRef.current?.(selectedId, showNeighbors)
  }, [selectedId, showNeighbors])

  useEffect(() => {
    resetViewRef.current?.()
  }, [resetKey])

  useEffect(() => {
    const host = hostRef.current
    if (!host || points.length === 0) return

    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    let width = Math.max(host.clientWidth, 320)
    let height = Math.min(600, Math.max(390, width * 0.6))
    const profile = constellationProfile({ width, devicePixelRatio: window.devicePixelRatio, reducedMotion })

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#070a12')
    scene.fog = new THREE.FogExp2('#070a12', 0.085)

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.05, 100)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' })
    renderer.setPixelRatio(profile.pixelRatio)
    renderer.setSize(width, height)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15
    renderer.domElement.setAttribute('aria-label', t('space.pca3dAria'))
    renderer.domElement.setAttribute('role', 'img')
    host.prepend(renderer.domElement)

    const css = getComputedStyle(document.documentElement)
    const topColor = new THREE.Color(css.getPropertyValue('--top').trim() || '#58a2ea')
    const bottomColor = new THREE.Color(css.getPropertyValue('--bottom').trim() || '#f08a63')
    const accentColor = new THREE.Color(css.getPropertyValue('--accent').trim() || '#a98dea')
    const sceneRoot = new THREE.Group()
    scene.add(sceneRoot)

    scene.add(new THREE.HemisphereLight(0x9fb8ff, 0x10121a, 1.3))
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.15)
    keyLight.position.set(3.4, 4.6, 5.2)
    scene.add(keyLight)
    const topLight = new THREE.PointLight(topColor, 10, 12, 2)
    topLight.position.set(2.2, 1.4, 2.8)
    scene.add(topLight)
    const bottomLight = new THREE.PointLight(bottomColor, 8, 12, 2)
    bottomLight.position.set(-2.6, -1.2, 2.2)
    scene.add(bottomLight)

    const positions = points.map((point) => scenePosition(point.pca))
    const bounds = new THREE.Box3()
    positions.forEach((position) => bounds.expandByPoint(new THREE.Vector3(...position)))
    const sphere = bounds.getBoundingSphere(new THREE.Sphere())
    const initialTarget = sphere.center.clone()
    const cameraDistance = Math.max(4.8, sphere.radius * 2.9)
    const initialCamera = initialTarget.clone().add(new THREE.Vector3(0.35, 0.28, cameraDistance))
    camera.position.copy(initialCamera)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.copy(initialTarget)
    controls.enableDamping = true
    controls.dampingFactor = 0.055
    controls.rotateSpeed = 0.52
    controls.zoomSpeed = 0.75
    controls.minDistance = Math.max(1.6, sphere.radius * 0.75)
    controls.maxDistance = Math.max(8, sphere.radius * 5)
    controls.autoRotateSpeed = 0.55
    controls.addEventListener('start', () => {
      userInteractedRef.current = true
    })
    controls.update()

    const glowCanvas = document.createElement('canvas')
    glowCanvas.width = 128
    glowCanvas.height = 128
    const glowContext = glowCanvas.getContext('2d')
    if (glowContext) {
      const gradient = glowContext.createRadialGradient(64, 64, 3, 64, 64, 62)
      gradient.addColorStop(0, 'rgba(255,255,255,.95)')
      gradient.addColorStop(0.18, 'rgba(255,255,255,.48)')
      gradient.addColorStop(0.52, 'rgba(255,255,255,.11)')
      gradient.addColorStop(1, 'rgba(255,255,255,0)')
      glowContext.fillStyle = gradient
      glowContext.fillRect(0, 0, 128, 128)
    }
    const glowTexture = new THREE.CanvasTexture(glowCanvas)
    glowTexture.colorSpace = THREE.SRGBColorSpace

    const sphereGeometry = new THREE.SphereGeometry(0.052, profile.sphereSegments, profile.sphereSegments)
    const kpopGeometry = new THREE.IcosahedronGeometry(0.061, width < 640 ? 1 : 2)
    const ringGeometry = new THREE.TorusGeometry(0.078, 0.004, 6, width < 640 ? 18 : 28)
    const nodes = new Map<string, SceneNode>()
    const raycastMeshes: THREE.Mesh[] = []

    points.forEach((point, index) => {
      const color = point.group === 'top' ? topColor : bottomColor
      const material = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.62,
        roughness: 0.32,
        metalness: 0.1,
        transparent: true,
        opacity: 0.9,
      })
      const mesh = new THREE.Mesh(point.domain === 'vocaloid' ? sphereGeometry : kpopGeometry, material)
      mesh.position.set(...positions[index])
      mesh.userData.id = point.id
      mesh.userData.index = index
      sceneRoot.add(mesh)
      raycastMeshes.push(mesh)

      const glowMaterial = new THREE.SpriteMaterial({
        map: glowTexture,
        color,
        transparent: true,
        opacity: 0.34,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
      const glow = new THREE.Sprite(glowMaterial)
      glow.position.copy(mesh.position)
      glow.scale.setScalar(0.29)
      sceneRoot.add(glow)

      let ring: THREE.Mesh | undefined
      let ringMaterial: THREE.MeshBasicMaterial | undefined
      if (point.domain === 'vocaloid') {
        ringMaterial = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.45,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        })
        ring = new THREE.Mesh(ringGeometry, ringMaterial)
        ring.position.copy(mesh.position)
        ring.rotation.set(Math.PI / 2.6, 0, index * 0.37)
        sceneRoot.add(ring)
      }

      nodes.set(point.id, { point, mesh, material, glow, glowMaterial, ring, ringMaterial })
    })

    const selectedHaloMaterial = new THREE.MeshBasicMaterial({
      color: accentColor,
      transparent: true,
      opacity: 0.92,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    const selectedHalo = new THREE.Mesh(new THREE.TorusGeometry(0.115, 0.008, 8, 40), selectedHaloMaterial)
    selectedHalo.visible = false
    sceneRoot.add(selectedHalo)

    const neighborGroup = new THREE.Group()
    sceneRoot.add(neighborGroup)

    const origin = new THREE.Vector3(0, 0, 0)
    const planeSize = Math.max(4.2, sphere.radius * 3.4)
    const addZeroGrid = (rotation: [number, number, number], opacity: number) => {
      const grid = new THREE.GridHelper(planeSize, 16, 0x536887, 0x25334a)
      grid.position.copy(origin)
      grid.rotation.set(...rotation)
      const materials = Array.isArray(grid.material) ? grid.material : [grid.material]
      materials.forEach((material) => {
        material.transparent = true
        material.opacity = opacity
        material.depthWrite = false
      })
      scene.add(grid)
    }
    addZeroGrid([0, 0, 0], 0.19)
    addZeroGrid([Math.PI / 2, 0, 0], 0.09)
    addZeroGrid([0, 0, Math.PI / 2], 0.07)
    const originMaterial = new THREE.MeshBasicMaterial({ color: accentColor, transparent: true, opacity: 0.78 })
    const originMarker = new THREE.Mesh(new THREE.SphereGeometry(0.026, 10, 10), originMaterial)
    originMarker.position.copy(origin)
    scene.add(originMarker)

    const axisLength = Math.max(1.65, sphere.radius * 0.85)
    const axisDefs: Array<[THREE.Vector3, number, string]> = [
      [new THREE.Vector3(1, 0, 0), 0x6ba9ff, `PC1 · ${explainedVariance[0]?.toFixed(1) ?? '—'}%`],
      [new THREE.Vector3(0, 1, 0), 0xff8f6b, `PC2 · ${explainedVariance[1]?.toFixed(1) ?? '—'}%`],
      [new THREE.Vector3(0, 0, 1), 0xb49cff, `PC3 · ${explainedVariance[2]?.toFixed(1) ?? '—'}%`],
    ]
    axisDefs.forEach(([direction, color, label]) => {
      const arrow = new THREE.ArrowHelper(direction, origin, axisLength, color, 0.08, 0.035)
      ;(arrow.line.material as THREE.Material).transparent = true
      ;(arrow.line.material as THREE.Material).opacity = 0.34
      ;(arrow.cone.material as THREE.Material).transparent = true
      ;(arrow.cone.material as THREE.Material).opacity = 0.55
      scene.add(arrow)

      const canvas = document.createElement('canvas')
      canvas.width = 512
      canvas.height = 96
      const context = canvas.getContext('2d')
      if (context) {
        context.font = '600 30px Inter, sans-serif'
        context.fillStyle = 'rgba(228,235,255,.88)'
        context.textAlign = 'center'
        context.fillText(label, 256, 58)
      }
      const texture = new THREE.CanvasTexture(canvas)
      texture.colorSpace = THREE.SRGBColorSpace
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.78, depthWrite: false })
      const sprite = new THREE.Sprite(spriteMaterial)
      sprite.position.copy(origin.clone().add(direction.clone().multiplyScalar(axisLength + 0.2)))
      sprite.scale.set(0.82, 0.154, 1)
      scene.add(sprite)
    })

    if (profile.particleCount > 0) {
      const particlePositions = new Float32Array(profile.particleCount * 3)
      let seed = 0x4d5641
      for (let index = 0; index < profile.particleCount; index += 1) {
        seed = (seed * 1664525 + 1013904223) >>> 0
        const rx = seed / 0xffffffff
        seed = (seed * 1664525 + 1013904223) >>> 0
        const ry = seed / 0xffffffff
        seed = (seed * 1664525 + 1013904223) >>> 0
        const rz = seed / 0xffffffff
        const radius = Math.max(3.8, sphere.radius * 2.6)
        particlePositions[index * 3] = initialTarget.x + (rx - 0.5) * radius * 2
        particlePositions[index * 3 + 1] = initialTarget.y + (ry - 0.5) * radius * 1.45
        particlePositions[index * 3 + 2] = initialTarget.z + (rz - 0.5) * radius * 2
      }
      const particleGeometry = new THREE.BufferGeometry()
      particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3))
      const particleMaterial = new THREE.PointsMaterial({
        color: 0xa9b9d8,
        size: width < 640 ? 0.012 : 0.016,
        transparent: true,
        opacity: 0.28,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
      scene.add(new THREE.Points(particleGeometry, particleMaterial))
    }

    const tooltip = tooltipRef.current
    let hoveredId: string | undefined
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()

    const setPointer = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
    }

    const hitAtPointer = () => {
      raycaster.setFromCamera(pointer, camera)
      return raycaster.intersectObjects(raycastMeshes, false)[0]
    }

    const pointerMove = (event: PointerEvent) => {
      setPointer(event)
      const hit = hitAtPointer()
      const id = hit ? String(hit.object.userData.id) : undefined
      if (id !== hoveredId) {
        hoveredId = id
        renderer.domElement.style.cursor = id ? 'pointer' : 'grab'
        if (tooltip) tooltip.dataset.visible = id ? 'true' : 'false'
        if (id) {
          const point = nodes.get(id)?.point
          if (point) {
            if (tooltipTitleRef.current) tooltipTitleRef.current.textContent = point.title
            if (tooltipMetaRef.current)
              tooltipMetaRef.current.textContent = `${point.channel} · ${point.domain === 'vocaloid' ? 'Vocaloid' : 'K-pop'} · ${groupLabel(point.group, locale)}`
            if (tooltipPcaRef.current) tooltipPcaRef.current.textContent = point.score ? `display ${point.pca.map((value) => value.toFixed(3)).join(' / ')} · score ${point.score.map((value) => value.toFixed(3)).join(' / ')}` : `display ${point.pca.map((value) => value.toFixed(3)).join(' / ')}`
          }
        }
      }
      if (tooltip && id) {
        const rect = host.getBoundingClientRect()
        tooltip.style.left = `${event.clientX - rect.left + 16}px`
        tooltip.style.top = `${event.clientY - rect.top + 16}px`
      }
    }

    const pointerLeave = () => {
      hoveredId = undefined
      renderer.domElement.style.cursor = 'grab'
      if (tooltip) tooltip.dataset.visible = 'false'
    }

    const click = (event: PointerEvent) => {
      setPointer(event)
      const hit = hitAtPointer()
      if (!hit) return
      const point = nodes.get(String(hit.object.userData.id))?.point
      if (point) onSelect(point)
    }

    renderer.domElement.addEventListener('pointermove', pointerMove)
    renderer.domElement.addEventListener('pointerleave', pointerLeave)
    renderer.domElement.addEventListener('click', click)

    const focusCamera = (point?: SpacePoint) => {
      if (!point) return
      const position = new THREE.Vector3(...scenePosition(point.pca))
      const direction = camera.position.clone().sub(controls.target).normalize()
      const focusDistance = Math.max(1.7, Math.min(2.8, sphere.radius * 1.3))
      const destination = position.clone().add(direction.multiplyScalar(focusDistance)).add(new THREE.Vector3(0.18, 0.1, 0))
      const startPosition = camera.position.clone()
      const startTarget = controls.target.clone()
      const startedAt = performance.now()
      const duration = reducedMotion ? 0 : 560

      const tick = () => {
        const elapsed = performance.now() - startedAt
        const raw = duration === 0 ? 1 : Math.min(1, elapsed / duration)
        const eased = 1 - Math.pow(1 - raw, 3)
        camera.position.lerpVectors(startPosition, destination, eased)
        controls.target.lerpVectors(startTarget, position, eased)
        if (raw < 1) requestAnimationFrame(tick)
      }
      tick()
    }

    const clearNeighborLines = () => {
      while (neighborGroup.children.length) {
        const child = neighborGroup.children[0]
        neighborGroup.remove(child)
        const line = child as THREE.Line
        ;(line.geometry as THREE.BufferGeometry).dispose()
        ;(line.material as THREE.Material).dispose()
      }
    }

    const updateVisual = (id?: string, neighborsEnabled = true) => {
      clearNeighborLines()
      const edges = neighborsEnabled ? buildNeighborEdges(points, id, width < 640 ? 4 : 7) : []
      const neighborIds = new Set(edges.map((edge) => edge.targetId))

      nodes.forEach((node, nodeId) => {
        const state = visualState(nodeId, id, neighborIds)
        node.mesh.scale.setScalar(state.scale)
        node.material.opacity = state.opacity
        node.material.emissiveIntensity = state.selected ? 1.35 : state.neighbor ? 0.86 : id ? 0.22 : 0.62
        node.glowMaterial.opacity = state.selected ? 0.92 : state.neighbor ? 0.48 : id ? 0.07 : 0.34
        node.glow.scale.setScalar(state.selected ? 0.52 : state.neighbor ? 0.36 : 0.29)
        if (node.ringMaterial) node.ringMaterial.opacity = state.selected ? 0.92 : state.neighbor ? 0.58 : id ? 0.1 : 0.45
      })

      const selected = id ? nodes.get(id) : undefined
      selectedHalo.visible = Boolean(selected)
      if (selected) {
        selectedHalo.position.copy(selected.mesh.position)
        selectedHalo.material = selectedHaloMaterial
        selectedHaloMaterial.color.copy(accentColor)
        focusCamera(selected.point)
      }

      edges.forEach((edge) => {
        const source = nodes.get(edge.sourceId)
        const target = nodes.get(edge.targetId)
        if (!source || !target) return
        const geometry = new THREE.BufferGeometry().setFromPoints([source.mesh.position, target.mesh.position])
        const color = source.point.group === 'top' ? topColor : bottomColor
        const material = new THREE.LineBasicMaterial({
          color,
          transparent: true,
          opacity: 0.42,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        })
        neighborGroup.add(new THREE.Line(geometry, material))
      })
    }
    updateVisualRef.current = updateVisual

    const resetView = () => {
      userInteractedRef.current = false
      camera.position.copy(initialCamera)
      controls.target.copy(initialTarget)
      controls.update()
    }
    resetViewRef.current = resetView

    updateVisual(selectedIdRef.current, showNeighborsRef.current)

    let raf = 0
    const startedAt = performance.now()
    const draw = () => {
      const now = performance.now()
      controls.autoRotate = profile.autoRotate && autoRotateRef.current && !userInteractedRef.current && !selectedIdRef.current
      controls.update()
      if (!reducedMotion) {
        const pulse = 1 + Math.sin((now - startedAt) * 0.0045) * 0.08
        selectedHalo.scale.setScalar(pulse)
        selectedHalo.rotation.z += 0.004
      }
      renderer.render(scene, camera)
      raf = requestAnimationFrame(draw)
    }
    draw()

    const resize = () => {
      width = Math.max(host.clientWidth, 320)
      height = Math.min(600, Math.max(390, width * 0.6))
      const nextProfile = constellationProfile({ width, devicePixelRatio: window.devicePixelRatio, reducedMotion })
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setPixelRatio(nextProfile.pixelRatio)
      renderer.setSize(width, height)
    }
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(resize)
    if (observer) observer.observe(host)
    else window.addEventListener('resize', resize)

    return () => {
      cancelAnimationFrame(raf)
      observer?.disconnect()
      if (!observer) window.removeEventListener('resize', resize)
      renderer.domElement.removeEventListener('pointermove', pointerMove)
      renderer.domElement.removeEventListener('pointerleave', pointerLeave)
      renderer.domElement.removeEventListener('click', click)
      controls.dispose()
      updateVisualRef.current = null
      resetViewRef.current = null
      const geometries = new Set<THREE.BufferGeometry>()
      const materials = new Set<THREE.Material>()
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Points || object instanceof THREE.Line || object instanceof THREE.Sprite) {
          if ('geometry' in object && object.geometry instanceof THREE.BufferGeometry) geometries.add(object.geometry)
          const material = object.material
          if (Array.isArray(material)) material.forEach((item) => materials.add(item))
          else if (material instanceof THREE.Material) materials.add(material)
        }
      })
      materials.forEach((material) => {
        const map = (material as THREE.SpriteMaterial).map
        if (map && map !== glowTexture) map.dispose()
        material.dispose()
      })
      geometries.forEach((geometry) => geometry.dispose())
      glowTexture.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [explainedVariance, locale, onSelect, points, t])

  return (
    <div className="pca3d-host constellation-stage" ref={hostRef} aria-label={t('space.pca3dHostAria')}>
      <div className="constellation-corner constellation-corner--top" aria-hidden="true" />
      <div className="constellation-corner constellation-corner--bottom" aria-hidden="true" />
      <div className="constellation-stage-legend" aria-hidden="true">
        <span><i className="legend-orb legend-orb--top" />TOP</span>
        <span><i className="legend-orb legend-orb--bottom" />BOTTOM</span>
        <span><i className="legend-shape-3d legend-shape-3d--round" />Vocaloid</span>
        <span><i className="legend-shape-3d legend-shape-3d--facet" />K-pop</span>
      </div>
      <div className="constellation-hint" aria-hidden="true">DRAG · ROTATE &nbsp; / &nbsp; SCROLL · ZOOM &nbsp; / &nbsp; CLICK · FOCUS</div>
      <div className="constellation-tooltip" ref={tooltipRef} data-visible="false" role="status">
        <b ref={tooltipTitleRef} />
        <span ref={tooltipMetaRef} />
        <code ref={tooltipPcaRef} />
      </div>
      <p className="sr-only">{t('space.pca3dSr')}</p>
    </div>
  )
}
