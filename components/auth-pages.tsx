'use client'
import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react'
import { intentLockApi, IntentLockApiError } from '@/lib/intentlock-api'

function Brand(){return <Link href="/" className="auth-brand"><span className="auth-mark">◎</span><span>intent<span>lock</span></span></Link>}

function AuthShell({mode}:{mode:'login'|'register'}){
  const router=useRouter(); const register=mode==='register'
  const [store,setStore]=useState(''); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [busy,setBusy]=useState(false); const [error,setError]=useState('')
  useEffect(()=>{intentLockApi.me().then(me=>router.replace(me.merchant.onboarding_completed?'/dashboard':'/onboard')).catch(()=>{})},[router])
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{const me=register?await intentLockApi.register(store,email,password):await intentLockApi.login(email,password);router.replace(me.merchant.onboarding_completed?'/dashboard':'/onboard')}catch(err){setError(err instanceof IntentLockApiError?err.message:'Could not connect to IntentLock API')}finally{setBusy(false)}}
  return <main className="auth-page"><section className="auth-side"><Brand/><div><span className="kicker">MERCHANT CONTROL PLANE</span><h1>{register?'Make your store AI-transactable.':'Welcome back to IntentLock.'}</h1><p>{register?'Create your merchant account, then complete the existing six-step setup for catalog, policy, identity and agent discovery.':'Sign in to operate your autonomous commerce channel and financial boundary.'}</p><div className="auth-proof"><span><ShieldCheck size={16}/>Merchant-scoped data</span><span><LockKeyhole size={16}/>HttpOnly session</span><span>◎ Console locked until onboarding completes</span></div></div><small>Razorpay Test Mode · Local hackathon environment</small></section><section className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><span className="kicker">{register?'CREATE MERCHANT ACCOUNT':'MERCHANT SIGN IN'}</span><h2>{register?'Onboard your store':'Sign in'}</h2><p>{register?'Your store name becomes the merchant identity used across IntentLock.':'Use the account that owns your onboarded merchant.'}</p>{register&&<label>Store name<input required minLength={2} value={store} onChange={e=>setStore(e.target.value)} placeholder="Demo Audio Store" /></label>}<label>Work email<input required type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@company.com" /></label><label>Password<input required minLength={8} type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 8 characters" /></label>{error&&<div className="auth-error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy?(register?'Creating account…':'Signing in…'):(register?'Create account & continue':'Sign in')} <ArrowRight size={15}/></button><div className="auth-switch">{register?'Already onboarded?':'New merchant?'} <Link href={register?'/login':'/register'}>{register?'Sign in':'Onboard your store'}</Link></div></form></section></main>
}
export function LoginPage(){return <AuthShell mode="login"/>}
export function RegisterPage(){return <AuthShell mode="register"/>}
