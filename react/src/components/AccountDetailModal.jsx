export default function AccountDetailModal({ account, onClose }) {
  if (!account) return null
  console.log('account:', account)

  return (
    <div className="modal-overlay open" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{account.title}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="detail-grid">
            <div className="detail-section">
              <h5>🎮 英雄资产</h5>
              <div className="detail-row"><span>英雄数量</span><span className="dv">{account.heroes} / 120 {account.heroesFull ? '✅ 全英雄' : ''}</span></div>
              {/* <div className="detail-row"><span style={{whiteSpace:'nowrap'}}>核心英雄</span><span className="dv">{account.heroList.join('、')}</span></div> */}
              <div className="detail-row"><span>位置倾向</span><span className="dv">{account.position}</span></div>
              <div className="detail-row"><span>主打英雄</span><span className="dv">{account.topHero}</span></div>
            </div>
            <div className="detail-section">
              <h5>🎨 皮肤资产</h5>
              <div className="detail-row"><span>皮肤总数</span><span className="dv">{account.skins}</span></div>
              {account.skinsLegend > 0 && <div className="detail-row"><span>传说皮肤</span><span className="dv">{account.skinsLegend} 个</span></div>}
              {account.skinsLimited > 0 && <div className="detail-row"><span>限定皮肤</span><span className="dv">{account.skinsLimited} 个</span></div>}
              {account.skinsCollector > 0 && <div className="detail-row"><span>荣耀典藏</span><span className="dv">{account.skinsCollector} 个</span></div>}
              <div className="detail-row"><span>核心皮肤</span><span className="dv">{account.highlightSkins.slice(0, 4).join('、')}</span></div>
            </div>
            <div className="detail-section">
              <h5>🏆 账号属性</h5>
              <div className="detail-row"><span>当前段位</span><span className="dv">{account.rank}</span></div>
              <div className="detail-row"><span>贵族等级</span><span className="dv">V{account.vip}</span></div>
              <div className="detail-row"><span>账号等级</span><span className="dv">Lv.{account.level}</span></div>
              <div className="detail-row"><span>账号风格</span><span className="dv">{account.style}</span></div>
              <div className="detail-row"><span>所在大区</span><span className="dv">{account.region}</span></div>
            </div>
            <div className="detail-section">
              <h5>💰 价格评估</h5>
              <div className="detail-row">
                <span>卖家报价</span>
                <span className="dv" style={{ color: 'var(--orange)', fontSize: '22px', fontWeight: 700 }}>¥{account.price.toLocaleString()}</span>
              </div>
              <div className="detail-row"><span>系统估价</span><span className="dv">¥{account.estValue.toLocaleString()}</span></div>
              <div className="detail-row">
                <span>性价比</span>
                <span className="dv" style={{ color: account.estTag === 'good' ? 'var(--brand-green-dark)' : 'var(--orange)' }}>{account.estLabel}</span>
              </div>
              <div className="detail-row"><span>匹配度</span><span className="dv">{account.match}%</span></div>
            </div>
            <div className="detail-section detail-full">
              <h5>🛡 风险评估</h5>
              <div className={`risk-bar ${account.risk === '低' ? 'risk-low' : account.risk === '中' ? 'risk-mid' : 'risk-high'}`}>
                <span style={{ fontSize: '18px' }}>{account.risk === '低' ? '✅' : account.risk === '中' ? '⚠' : '❌'}</span>
                <span>风险等级：<strong>{account.risk}</strong></span>
              </div>
              <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                {account.riskItems.map((item, i) => (
                  <div key={i} style={{ padding: '4px 0' }}>{i + 1}. {item}</div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
