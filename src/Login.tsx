import { useState } from 'react';
import { ArrowRight, Croissant, Eye, EyeOff, Loader2, LockKeyhole, Mail, ShieldCheck, Store } from 'lucide-react';

export type BakeryUser = { email:string; bakery_name:string };
export type AuthStatus = { needs_setup:boolean; user:BakeryUser|null };

export function Login({needsSetup,onSignedIn}:{needsSetup:boolean;onSignedIn:(user:BakeryUser)=>void}){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[bakery,setBakery]=useState(''),[show,setShow]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const submit=async(e:React.FormEvent)=>{
  e.preventDefault();setBusy(true);setError('');
  try{
   const response=await fetch(`/api/auth/${needsSetup?'setup':'login'}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password,...(needsSetup?{bakery_name:bakery}:{})})});
   const data=await response.json();
   if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Please check your details and try again.');
   onSignedIn(data.user);
  }catch(e){setError(e instanceof Error?e.message:'Unable to connect. Check that BentaBuddy is running.')}finally{setBusy(false)}
 };
 return <main className="login-page">
  <div className="login-background" aria-hidden="true"/><div className="login-shade" aria-hidden="true"/>
  <a href="#" className="login-brand" aria-label="BentaBuddy home"><span><Croissant size={24}/></span><div>benta<b>buddy</b><small>MADE FOR YOUR DISKARTE</small></div></a>
  <section className="login-card" aria-labelledby="login-title">
   <div className="login-emblem"><Croissant size={31} strokeWidth={1.6}/></div>
   <p className="login-eyebrow">YOUR BAKERY. A LITTLE MORE ORGANIZED.</p>
   <h1 id="login-title">{needsSetup?'Let’s open your bakery.':'Welcome back, baker.'}</h1>
   <p className="login-intro">{needsSetup?'Create your owner account to get started.':'A little less admin. A lot more baking.'}</p>
   <form className="login-form" onSubmit={submit}>
    {needsSetup&&<label htmlFor="bakery-name">Bakery name<div className="login-input"><Store size={18}/><input id="bakery-name" name="organization" autoComplete="organization" required maxLength={100} value={bakery} onChange={e=>setBakery(e.target.value)} placeholder="e.g. Pan de Amihan" disabled={busy}/></div></label>}
    <label htmlFor="login-email">Email address<div className="login-input"><Mail size={18}/><input id="login-email" name="email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={254} value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@yourbakery.com" disabled={busy}/></div></label>
    <label htmlFor="login-password">Password<div className="login-input"><LockKeyhole size={18}/><input id="login-password" name="password" type={show?'text':'password'} autoComplete={needsSetup?'new-password':'current-password'} required minLength={needsSetup?10:1} maxLength={256} value={password} onChange={e=>setPassword(e.target.value)} placeholder={needsSetup?'At least 10 characters':'Enter your password'} disabled={busy}/><button type="button" aria-label={show?'Hide password':'Show password'} aria-pressed={show} onClick={()=>setShow(!show)}>{show?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></label>
    {error&&<div className="login-error" role="alert">{error}</div>}
    <button className="login-submit" disabled={busy} type="submit">{busy?<><Loader2 size={18} className="spin"/>{needsSetup?'Setting up your bakery…':'Signing you in…'}</>:<>{needsSetup?'Create my bakery account':'Log in to my bakery'}<ArrowRight size={18}/></>}</button>
   </form>
   <div className="login-divider"/>
   <div className="login-private"><ShieldCheck size={19}/><div><strong>At home on your computer.</strong><p>Your account and bakery data are stored locally.</p></div></div>
   {needsSetup&&<p className="login-setup-note">One owner account for this installation. No internet needed.</p>}
  </section>
  <div className="login-caption" aria-hidden="true"><span>GOOD THINGS START IN YOUR KITCHEN.</span><p>Keep the orders flowing.<br/>We’ll help with the rest.</p></div>
  <footer className="login-footer"><span><span className="login-status-dot"/>Local AI. Made for your diskarte.</span><span>BentaBuddy · Made for small businesses.</span></footer>
 </main>;
}
