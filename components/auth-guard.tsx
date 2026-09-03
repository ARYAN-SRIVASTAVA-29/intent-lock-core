'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { intentLockApi } from '@/lib/intentlock-api'

export function ConsoleGuard({children}:{children:React.ReactNode}){
  const router=useRouter(); const [allowed,setAllowed]=useState(false)
  useEffect(()=>{let active=true;intentLockApi.me().then(me=>{if(!active)return;if(!me.merchant.onboarding_completed)router.replace('/onboard');else setAllowed(true)}).catch(()=>router.replace('/login'));return()=>{active=false}},[router])
  if(!allowed)return <main className="access-check"><span>◎</span><b>Verifying merchant access…</b></main>
  return <>{children}</>
}
export function OnboardingGuard({children}:{children:React.ReactNode}){
  const router=useRouter(); const [allowed,setAllowed]=useState(false)
  useEffect(()=>{intentLockApi.me().then(()=>setAllowed(true)).catch(()=>router.replace('/register'))},[router])
  if(!allowed)return <main className="access-check"><span>◎</span><b>Loading merchant setup…</b></main>
  return <>{children}</>
}
