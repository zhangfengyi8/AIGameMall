import { useState, useRef, useEffect } from 'react'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.132:8000').replace(/\/$/, '')

function parseSseChunk(buffer) {
  const parts = buffer.split('\n\n')
  const events = []
  for (const part of parts.slice(0, -1)) {
    if (!part.trim()) continue
    let evName = 'message', dataStr = ''
    for (const line of part.split('\n')) {
      if (line.startsWith('event: ')) evName = line.slice(7).trim()
      else if (line.startsWith('data: ')) dataStr = line.slice(6)
    }
    try {
      events.push({ event: evName, data: JSON.parse(dataStr) })
    } catch {
      // skip malformed SSE frames
    }
  }
  return { events, rest: parts[parts.length - 1] }
}

export default function AIAssistant({ onCardClick }) {
  const [isOpen, setIsOpen] = useState(false)
  const [showBadge, setShowBadge] = useState(true)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([{ id: 0, type: 'welcome' }])
  const [isStreaming, setIsStreaming] = useState(false)
  const historyRef = useRef([])
  const sessionIdRef = useRef(`web-${Date.now()}`)
  const bodyRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [messages])

  useEffect(() => () => { abortRef.current?.abort() }, [])

  function toggle() {
    setIsOpen(o => !o)
    setShowBadge(false)
    if (!isOpen) setTimeout(() => inputRef.current?.focus(), 50)
  }

  function close() { setIsOpen(false) }

  async function sendMsg(text) {
    const msg = (text !== undefined ? text : input).trim()
    if (!msg || isStreaming) return
    setInput('')

    const userId = Date.now()
    const thinkId = userId + 1
    setMessages(prev => [
      ...prev,
      { id: userId, type: 'user', text: msg },
      { id: thinkId, type: 'thinking' },
    ])

    setIsStreaming(true)
    try {
      await requestAgentStream(msg, thinkId)
    } catch (err) {
      if (err?.name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === thinkId
            ? { id: thinkId, type: 'error', text: '暂时无法连接导购服务，请稍后再试。' }
            : m
        ))
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  function quickSearch(text) { sendMsg(text) }

  async function requestAgentStream(message, messageId) {
    abortRef.current = new AbortController()

    const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionIdRef.current,
        message,
        history: historyRef.current,
      }),
      signal: abortRef.current.signal,
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || response.statusText)
    }
    if (!response.body) throw new Error('no response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let firstDelta = true

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { events, rest } = parseSseChunk(buffer)
      buffer = rest

      for (const { event: evName, data } of events) {
        if (evName === 'message_delta') {
          const text = data?.text || ''
          if (firstDelta) {
            // Replace thinking indicator with first character
            setMessages(prev => prev.map(m =>
              m.id === messageId
                ? { id: messageId, type: 'result', responseType: 'clarification', message: text, cards: [] }
                : m
            ))
            firstDelta = false
          } else {
            setMessages(prev => prev.map(m =>
              m.id === messageId ? { ...m, message: (m.message || '') + text } : m
            ))
          }
        } else if (evName === 'recommendations') {
          setMessages(prev => prev.map(m =>
            m.id === messageId
              ? { ...m, type: 'result', responseType: 'recommendations', cards: data || [] }
              : m
          ))
        } else if (evName === 'done') {
          historyRef.current = data?.history || historyRef.current
          setMessages(prev => prev.map(m => {
            if (m.id !== messageId) return m
            return {
              ...m,
              type: 'result',
              responseType: data?.type || m.responseType || 'clarification',
              // Prefer accumulated typewriter text; fallback to done.message
              message: m.message || data?.message || '',
              // Prefer cards already set by recommendations event
              cards: m.cards?.length ? m.cards : (data?.cards || []),
            }
          }))
        } else if (evName === 'error') {
          setMessages(prev => prev.map(m =>
            m.id === messageId
              ? { id: messageId, type: 'error', text: data?.detail || '导购服务异常。' }
              : m
          ))
        }
      }
    }
  }

  return (
    <>
      {/* Floating Ball */}
      <div className="ai-ball">
        <div className="ai-ball-label">AI导购 · 帮你找号</div>
        <div className="ai-ball-btn" onClick={toggle}>
          <svg viewBox="0 0 32 32">
            <path d="M16 2C8.3 2 2 8.3 2 16s6.3 14 14 14 14-6.3 14-14S23.7 2 16 2zm-2 18.5v-2h-2.8c-.4 0-.7-.3-.7-.7s.3-.7.7-.7H14v-2.3h-2.8c-.4 0-.7-.3-.7-.7s.3-.7.7-.7H14v-2c0-1.1.9-2 2-2s2 .9 2 2v2h2.8c.4 0 .7.3.7.7s-.3.7-.7.7H18v2.3h2.8c.4 0 .7.3.7.7s-.3.7-.7.7H18v2c0 .4-.3.7-.7.7s-.7-.3-.7-.7z" />
          </svg>
          {showBadge && <div className="ai-ball-badge" />}
        </div>
      </div>

      {/* Chat Panel */}
      <div className={`ai-panel${isOpen ? ' open' : ''}`}>
        <div className="ai-panel-header">
          <div className="ai-title">
            <div className="ai-avatar">🐯</div>
            <div>
              <div className="ai-name">AI 智能导购</div>
              <div className="ai-desc">帮你找到最合适的账号</div>
            </div>
          </div>
          <div className="ai-actions">
            <button onClick={close} title="最小化">−</button>
            <button onClick={close} title="关闭">×</button>
          </div>
        </div>

        <div className="ai-panel-body" ref={bodyRef}>
          {messages.map(m => {
            if (m.type === 'welcome') return (
              <div className="msg msg-ai" key={m.id}>
                <div className="ai-msg-avatar">🐯</div>
                <div>
                  <div className="msg-bubble">
                    你好！我是AI导购<strong>小虎</strong>👋<br />
                    告诉我你的需求，我帮你精准匹配账号——<br />
                    📌 想要哪个英雄的皮肤？<br />
                    📌 预算多少？<br />
                    📌 对段位有要求吗？
                  </div>
                  <div className="quick-tags">
                    {['安卓QQ，预算1000', '貂蝉典藏号', '王者段位 3000内', '便宜入门号'].map(t => (
                      <span key={t} className="quick-tag" onClick={() => quickSearch(t)}>{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            )

            if (m.type === 'user') return (
              <div className="msg msg-user" key={m.id}>{m.text}</div>
            )

            if (m.type === 'thinking') return (
              <div className="msg msg-ai" key={m.id}>
                <div className="ai-msg-avatar">🐯</div>
                <div className="msg-bubble">
                  <div className="msg-think">
                    <span>Thinking</span>
                    <span className="dot" /><span className="dot" /><span className="dot" />
                  </div>
                </div>
              </div>
            )

            if (m.type === 'result') {
              const cards = m.cards || []
              if (cards.length > 0) {
                console.log('cards:', cards)
              }
              return (
                <div className="msg msg-ai" key={m.id}>
                  <div className="ai-msg-avatar">🐯</div>
                  <div className="msg-bubble" style={{ maxWidth: '340px' }}>
                    {cards.length > 0 ? (
                      <>
                        <div style={{ marginBottom: '6px' }}>
                          {m.message || <>根据你的需求，为你推荐<strong>{cards.length}</strong>个匹配账号：</>}
                        </div>
                        {cards.map((a, i) => (
                          <div className="ai-card" key={a.id} onClick={() => onCardClick(a.id)}>
                            <div className="ai-card-top">
                              <span className="ai-card-title">{i === 0 ? '🔥 ' : ''}{a.title}</span>
                              <span className={`ai-card-match ${a.match >= 90 ? 'match-high' : 'match-mid'}`}>匹配 {a.match}%</span>
                            </div>
                            <div className="ai-card-attrs">
                              <span>🎮 {a.heroes}英雄</span>
                              <span>🎨 {a.skins}皮肤</span>
                              <span>🏆 {a.rank}</span>
                              <span>👑 V{a.vip}</span>
                              <span>📍 {a.region}</span>
                            </div>
                            <div className="ai-card-footer">
                              <div>
                                <div className="ai-card-price-row">
                                  <span className="ai-card-price">¥{a.price.toLocaleString()}</span>
                                  <span className="ai-card-estimate">估价 <span className="est-val">¥{a.estValue.toLocaleString()}</span></span>
                                  <span className={`ai-card-value-tag ${a.estLabel === '高性价比' ? 'val-good' : 'val-fair'}`}>{a.estLabel}</span>
                                </div>
                                <div className="ai-card-risk">🛡 风险{a.risk} · {a.riskItems.slice(0, 2).map(s => s.replace(/NONE/g, '正常').replace(/SUPPORTED/g, '支持').replace(/FULL_SUPPORTED/g, '支持')).join(' · ')}</div>
                              </div>
                            </div>
                          </div>
                        ))}
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                          💡 推荐理由：{cards[0].highlightSkins.slice(0, 3).join('、') || '账号资产匹配'}，{cards[0].estLabel}
                        </div>
                      </>
                    ) : (
                      <div>{m.message}</div>
                    )}
                  </div>
                </div>
              )
            }

            if (m.type === 'error') return (
              <div className="msg msg-ai" key={m.id}>
                <div className="ai-msg-avatar">🐯</div>
                <div className="msg-bubble" style={{ color: 'var(--red)' }}>{m.text}</div>
              </div>
            )

            return null
          })}
        </div>

        <div className="ai-panel-input">
          <input
            ref={inputRef}
            type="text"
            placeholder={isStreaming ? '正在回复中…' : '输入你的需求……'}
            value={input}
            disabled={isStreaming}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMsg()}
          />
          <button className="btn-send" disabled={isStreaming} onClick={() => sendMsg()}>➤</button>
        </div>
      </div>
    </>
  )
}
