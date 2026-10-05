const letters = ['M', 'O', 'D', 'O']

export function Wordmark() {
  return (
    <span className="wordmark-letters" aria-label="MODO">
      {letters.map((letter, index) => (
        <span key={`${letter}-${index}`} className="wordmark-letter" aria-hidden="true">
          {letter}
        </span>
      ))}
    </span>
  )
}
