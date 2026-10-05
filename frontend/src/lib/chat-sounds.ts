let audioContext: AudioContext | null = null

function context() {
  if (typeof window === 'undefined' || !window.AudioContext) return null
  audioContext ??= new window.AudioContext()
  if (audioContext.state === 'suspended') void audioContext.resume()
  return audioContext
}

function pop(
  startFrequency: number,
  endFrequency: number,
  delay = 0,
  volume = 0.045,
) {
  const audio = context()
  if (!audio) return
  const start = audio.currentTime + delay
  const oscillator = audio.createOscillator()
  const gain = audio.createGain()

  oscillator.type = 'sine'
  oscillator.frequency.setValueAtTime(startFrequency, start)
  oscillator.frequency.exponentialRampToValueAtTime(endFrequency, start + 0.075)
  gain.gain.setValueAtTime(0.0001, start)
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.008)
  gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.095)

  oscillator.connect(gain)
  gain.connect(audio.destination)
  oscillator.start(start)
  oscillator.stop(start + 0.1)
}

export function playSendSound() {
  pop(430, 650, 0, 0.052)
}

export function playReceiveSound() {
  pop(620, 880, 0, 0.058)
  pop(760, 1040, 0.065, 0.045)
}
