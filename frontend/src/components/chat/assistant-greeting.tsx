export function AssistantGreeting() {
  return (
    <div className="assistant-greeting">
      <span className="assistant-mark" aria-hidden="true">
        <img src="/modo-studio-logo.png" alt="" />
      </span>
      <article className="message-row message-row-assistant">
        <div className="message-bubble message-assistant greeting-bubble">
          <strong>Hi there <span aria-hidden="true">👋</span></strong>
          <p>You’re speaking with Ren. How can I help you today?</p>
          <span className="assistant-byline">Ren · AI assistant</span>
        </div>
      </article>
    </div>
  )
}
