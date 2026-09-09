import { useEffect, useState } from 'react'

const cache = new Map<string, Promise<unknown>>()
export function dataUrl(name:string){ return `${import.meta.env.BASE_URL}data/${name}.json` }
export async function loadJson<T>(name:string):Promise<T>{
  const key=dataUrl(name)
  if(!cache.has(key)){
    cache.set(key, fetch(key).then(async response=>{
      if(!response.ok) throw new Error(`resource ${name} returned HTTP ${response.status}`)
      return response.json()
    }))
  }
  return cache.get(key) as Promise<T>
}
export function useResource<T>(name:string){
  const [data,setData]=useState<T|null>(null)
  const [error,setError]=useState<Error|null>(null)
  useEffect(()=>{ let active=true; loadJson<T>(name).then(v=>{if(active)setData(v)}).catch(e=>{if(active)setError(e instanceof Error?e:new Error(String(e)))}); return()=>{active=false} },[name])
  return {data,error,loading:!data&&!error}
}
export function clearDataCache(){ cache.clear() }
