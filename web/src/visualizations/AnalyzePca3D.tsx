import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { AnalyzeReport } from '../data/analyzeReport'

type Props={pca:AnalyzeReport['pca'];neighborIds:string[];label:string;onUnavailable:()=>void}

/** Render on interaction only. A single uniform scale preserves raw PCA geometry. */
export default function AnalyzePca3D({pca,neighborIds,label,onUnavailable}:Props){
  const host=useRef<HTMLDivElement>(null)
  const neighbors=neighborIds.join(',')
  useEffect(()=>{
    const node=host.current
    if(!node||!pca.score)return
    const canvas=document.createElement('canvas')
    const context=canvas.getContext('webgl2',{antialias:true,alpha:false})
    if(!context){onUnavailable();return}
    const renderer=new THREE.WebGLRenderer({canvas,context,antialias:true,alpha:false})
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5))
    renderer.outputColorSpace=THREE.SRGBColorSpace
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label',label)
    canvas.setAttribute('tabindex','0')
    node.appendChild(canvas)
    const scene=new THREE.Scene()
    scene.background=new THREE.Color('#080d19')
    const camera=new THREE.PerspectiveCamera(45,1,0.01,100)
    camera.position.set(3.8,2.8,6.8)
    const controls=new OrbitControls(camera,canvas)
    controls.enableDamping=false
    controls.minDistance=1.2;controls.maxDistance=18
    const values=[...pca.reference_points.map(point=>point.score),pca.score]
    const scale=2.4/Math.max(1,...values.flat().map(Math.abs))
    const vector=(v:number[])=>new THREE.Vector3(v[0]*scale,v[1]*scale,v[2]*scale)
    const dotGeometry=new THREE.SphereGeometry(0.038,10,8)
    const top=new THREE.MeshBasicMaterial({color:'#59a8ff',transparent:true,opacity:0.68})
    const bottom=new THREE.MeshBasicMaterial({color:'#ff9672',transparent:true,opacity:0.68})
    const byId=new Map<string,THREE.Vector3>()
    for(const point of pca.reference_points){
      const mesh=new THREE.Mesh(dotGeometry,point.group==='top'?top:bottom)
      mesh.position.copy(vector(point.score));scene.add(mesh);byId.set(point.video_id,mesh.position)
    }
    const targetPosition=vector(pca.score)
    const targetMaterial=new THREE.MeshBasicMaterial({color:'#d6bbff'})
    const target=new THREE.Mesh(new THREE.SphereGeometry(0.09,20,16),targetMaterial)
    target.position.copy(targetPosition);scene.add(target)
    const ring=new THREE.Mesh(new THREE.TorusGeometry(0.145,0.009,8,40),new THREE.MeshBasicMaterial({color:'#c49aff',transparent:true,opacity:0.9}))
    ring.position.copy(targetPosition);scene.add(ring)
    const lineMaterial=new THREE.LineBasicMaterial({color:'#b59be8',transparent:true,opacity:0.48})
    for(const id of neighbors.split(',')){
      const position=byId.get(id)
      if(position)scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([targetPosition,position]),lineMaterial))
    }
    const axes=new THREE.AxesHelper(2.8);scene.add(axes)
    const grid=new THREE.GridHelper(6,12,'#293951','#152138')
    grid.position.y=-2.8;scene.add(grid)
    const origin=new THREE.Mesh(new THREE.SphereGeometry(0.025,8,6),new THREE.MeshBasicMaterial({color:'#ffffff'}));scene.add(origin)
    let disposed=false
    const draw=()=>{if(!disposed){ring.lookAt(camera.position);renderer.render(scene,camera)}}
    const resize=()=>{
      const width=Math.max(240,node.clientWidth),height=Math.min(440,Math.max(320,width*0.8))
      renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();draw()
    }
    controls.addEventListener('change',draw)
    const observer=new ResizeObserver(resize);observer.observe(node);resize()
    const lost=(event:Event)=>{event.preventDefault();onUnavailable()}
    canvas.addEventListener('webglcontextlost',lost)
    return ()=>{
      disposed=true;observer.disconnect();controls.removeEventListener('change',draw);controls.dispose()
      canvas.removeEventListener('webglcontextlost',lost)
      const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>()
      scene.traverse(object=>{
        if(object instanceof THREE.Mesh||object instanceof THREE.Line){
          geometries.add(object.geometry)
          const list=Array.isArray(object.material)?object.material:[object.material]
          list.forEach(material=>materials.add(material))
        }
      })
      geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose())
      renderer.dispose();renderer.forceContextLoss();canvas.remove()
    }
  },[pca,neighbors,label,onUnavailable])
  return <div className="analyze-pca3d" ref={host}/>
}
