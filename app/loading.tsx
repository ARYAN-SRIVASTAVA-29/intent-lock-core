export default function Loading(){
  return <main className="route-loader" aria-label="Loading IntentLock">
    <div className="route-loader-mark"><span/><span/></div>
    <strong>IntentLock</strong>
    <small>Synchronizing merchant control plane…</small>
    <div className="route-loader-track"><i/></div>
  </main>
}
