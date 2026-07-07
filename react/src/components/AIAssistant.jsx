import { useState, useRef, useEffect } from 'react'

const HEROES = ['孙尚香', '李白', '貂蝉', '鲁班', '后羿', '花木兰', '武则天', '孙悟空', '韩信', '裴擒虎', '马可波罗', '诸葛亮', '小乔', '安琪拉', '妲己', '铠', '宫本武藏', '关羽', '马超']

function matchAccounts(msg, accounts) {
  let results = [...accounts]
  const matchedHero = HEROES.find(h => msg.includes(h))
  if (matchedHero) {
    results = results.filter(a => a.heroList.some(h => h.includes(matchedHero)) || a.title.includes(matchedHero))
    results.sort((a, b) => {
      const aHas = a.heroList.some(h => h.includes(matchedHero)) ? 1 : 0
      const bHas = b.heroList.some(h => h.includes(matchedHero)) ? 1 : 0
      return bHas - aHas || b.match - a.match
    })
  }
  if (msg.includes('便宜') || msg.includes('入门')) results = results.filter(a => a.price <= 1000)
  else if (msg.includes('3000') || msg.includes('3千')) results = results.filter(a => a.price >= 2000 && a.price <= 4000)
  else if (msg.includes('5000') || msg.includes('5千')) results = results.filter(a => a.price >= 4000 && a.price <= 6000)
  if (msg.includes('王者')) results = results.filter(a => a.rankNum >= 16)
  if (msg.includes('星耀')) results = results.filter(a => a.rankNum >= 10 && a.rankNum < 16)
  if (msg.includes('射手')) results = results.filter(a => a.position === '射手')
  if (msg.includes('法师')) results = results.filter(a => a.position === '法师')
  if (msg.includes('打野')) results = results.filter(a => a.position === '打野')
  if (msg.includes('全皮') || msg.includes('全皮肤')) results = results.filter(a => a.highlightSkins.length >= 3)
  if (msg.includes('典藏')) results = results.filter(a => a.skinsCollector > 0)
  if (msg.includes('限定')) results = results.filter(a => a.skinsLimited > 10)
  if (msg.includes('技术') || msg.includes('战力') || msg.includes('国服')) results = results.filter(a => a.style === '技术号')
  if (msg.includes('氪佬') || msg.includes('v10') || msg.includes('V10')) results = results.filter(a => a.style === '氪佬号' || a.vip >= 8)
  return { top3: results.slice(0, 3), matchedHero: matchedHero || null }
}

export default function AIAssistant({ accounts, onCardClick }) {
  const [isOpen, setIsOpen] = useState(false)
  const [showBadge, setShowBadge] = useState(true)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([{ id: 0, type: 'welcome' }])
  const bodyRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [messages])

  function toggle() {
    setIsOpen(o => !o)
    setShowBadge(false)
    if (!isOpen) setTimeout(() => inputRef.current?.focus(), 50)
  }

  function close() { setIsOpen(false) }

  function sendMsg(text) {
    const msg = (text !== undefined ? text : input).trim()
    if (!msg) return
    setInput('')

    const userId = Date.now()
    const thinkId = userId + 1
    setMessages(prev => [
      ...prev,
      { id: userId, type: 'user', text: msg },
      { id: thinkId, type: 'thinking' },
    ])

    setTimeout(() => {
      const { top3, matchedHero } = matchAccounts(msg, accounts)
      setMessages(prev => prev.map(m =>
        m.id === thinkId
          ? { id: thinkId, type: 'result', top3, matchedHero, query: msg }
          : m
      ))
    }, 1500)
  }

  function quickSearch(text) { sendMsg(text) }

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
                <div className="ai-msg-avatar">🤖</div>
                <div>
                  <div className="msg-bubble">
                    你好！我是AI导购<strong>小虎</strong>👋<br />
                    告诉我你的需求，我帮你精准匹配账号——<br />
                    📌 想要哪个英雄的皮肤？<br />
                    📌 预算多少？<br />
                    📌 对段位有要求吗？
                  </div>
                  <div className="quick-tags">
                    {['孙尚香全皮', '貂蝉典藏号', '王者段位 3000内', '便宜入门号'].map(t => (
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
                <div className="ai-msg-avatar">🤖</div>
                <div className="msg-bubble">
                  <div className="msg-think">
                    <span>正在为你匹配账号</span>
                    <span className="dot" /><span className="dot" /><span className="dot" />
                  </div>
                </div>
              </div>
            )

            if (m.type === 'result') {
              const { top3, matchedHero, query } = m
              return (
                <div className="msg msg-ai" key={m.id}>
                  <div className="ai-msg-avatar">🤖</div>
                  <div className="msg-bubble" style={{ maxWidth: '340px' }}>
                    {top3.length > 0 ? (
                      <>
                        <div style={{ marginBottom: '6px' }}>
                          {matchedHero
                            ? <>我找到了<strong>{top3.length}</strong>个包含<strong>{matchedHero}</strong>的优质账号：</>
                            : <>根据你的需求，为你推荐<strong>{top3.length}</strong>个匹配账号：</>
                          }
                        </div>
                        {top3.map((a, i) => (
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
                                  <span className={`ai-card-value-tag ${a.estTag === 'good' ? 'val-good' : 'val-fair'}`}>{a.estLabel}</span>
                                </div>
                                <div className="ai-card-risk">🛡 风险{a.risk} · {a.riskItems.slice(0, 2).join(' · ')}</div>
                              </div>
                            </div>
                          </div>
                        ))}
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                          💡 推荐理由：{top3[0].highlightSkins.slice(0, 3).join('、')}等核心皮肤，{top3[0].estLabel}，{top3[0].riskItems[0]}
                        </div>
                      </>
                    ) : (
                      <div style={{ color: 'var(--text-secondary)' }}>
                        抱歉，没有找到完全匹配的账号 😔<br />
                        试试调整条件：去掉段位限制、放宽价格区间？
                      </div>
                    )}
                  </div>
                </div>
              )
            }

            return null
          })}
        </div>

        <div className="ai-panel-input">
          <input
            ref={inputRef}
            type="text"
            placeholder="输入你的需求……"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMsg()}
          />
          <button className="btn-send" onClick={() => sendMsg()}>➤</button>
        </div>
      </div>
    </>
  )
}
