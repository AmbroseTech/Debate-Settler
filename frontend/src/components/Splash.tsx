// Splash screen: pure black, "DS" blinks three times (§4).
export default function Splash() {
  return (
    <div className="splash" role="status" aria-label="Debate_Settler loading">
      <div className="splash-logo">DS</div>
    </div>
  )
}
