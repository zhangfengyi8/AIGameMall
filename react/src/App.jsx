import { useState, useEffect } from 'react'
import { accounts } from './data/accounts'
import AIAssistant from './components/AIAssistant'

const GRADIENT_MAP = {
  '氪佬号': '#ff9500,#ff4757',
  '技术号': '#3b65ff,#4579ff',
  '收藏号': '#20EB82,#00B570',
  '入门号': '#848B93,#B5BABF',
}
function getCardGradient(style) { return GRADIENT_MAP[style] || '#848B93,#B5BABF' }
function getBadgeClass(b) { return b === 'hot' ? 'badge-hot' : b === 'new' ? 'badge-new' : 'badge-recommend' }
function getBadgeText(b) { return b === 'hot' ? '热门' : b === 'new' ? '新上' : '推荐' }

const RANKS = ['不限', '青铜', '白银', '黄金', '铂金', '钻石', '星耀', '王者', '荣耀', '巅峰2000+']
const CATS = [
  { label: '全部', count: '12,836' },
  { label: '王者号', count: '3,241' },
  { label: '皮肤号', count: '5,102' },
  { label: '氪佬号', count: '1,887' },
  { label: '技术号', count: '1,206' },
  { label: '低价号', count: '3,490' },
]
const SORTS = ['综合排序', '价格 ▲', '皮肤数', '最新上架']

export default function App() {
  const [activeCat, setActiveCat] = useState('全部')
  const [activeSort, setActiveSort] = useState('综合排序')
  const [activeRank, setActiveRank] = useState('不限')
  const [modalAccount, setModalAccount] = useState(null)

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') setModalAccount(null)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  function openDetail(id) {
    setModalAccount(accounts.find(a => a.id === id) || null)
  }

  return (
    <>
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <div className="logo-icon">♦</div>
          <span className="logo-text">游戏账号交易</span>
        </div>
        <nav className="header-nav">
          <a href="#" className="active">首页</a>
          <a href="#">王者荣耀</a>
          <a href="#">和平精英</a>
          <a href="#">原神</a>
          <a href="#">LOL手游</a>
          <a href="#">估价工具</a>
        </nav>
        <div className="header-actions">
          <button className="btn-login">登录</button>
          <button className="btn-sell">我要卖号</button>
        </div>
      </header>

      <div className="main-container">
        {/* Banner */}
        <div className="banner">
          <div className="banner-text">
            <h2>🔥 百万账号 · 官方担保 · 找回包赔</h2>
            <p>实名认证 · 电子合同 · 专人客服跟进 · 安全交易有保障</p>
          </div>
          <div className="banner-stats">
            <div className="banner-stat">
              <div className="num">326,518</div>
              <div className="label">累计交易</div>
            </div>
            <div className="banner-stat">
              <div className="num">98.7%</div>
              <div className="label">交易成功率</div>
            </div>
            <div className="banner-stat">
              <div className="num">12,836</div>
              <div className="label">在售账号</div>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="search-section">
          <div className="search-row">
            <div className="search-game-select">
              <div className="game-icon">⚔</div>
              王者荣耀
              <span className="arrow">▼</span>
            </div>
            <div className="search-input-wrap">
              <span className="search-icon">🔍</span>
              <input type="text" placeholder="搜索英雄、皮肤、段位……" />
            </div>
            <button className="btn-search">搜索</button>
          </div>
          <div className="filter-row">
            <span className="filter-label">热门搜索：</span>
            {['全部', '孙尚香', '李白', '荣耀典藏', '全英雄', '王者号'].map(t => (
              <span key={t} className={`filter-tag${t === '全部' ? ' active' : ''}`}>{t}</span>
            ))}
            <span className="filter-tag hot">🔥 性价比</span>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="cat-tabs">
          {CATS.map(c => (
            <div
              key={c.label}
              className={`cat-tab${activeCat === c.label ? ' active' : ''}`}
              onClick={() => setActiveCat(c.label)}
            >
              {c.label}<span className="count">{c.count}</span>
            </div>
          ))}
        </div>

        {/* Content Layout */}
        <div className="content-layout">
          {/* Sidebar */}
          <aside className="sidebar">
            <div className="sidebar-card">
              <h4>💰 价格区间</h4>
              <div className="sidebar-price-inputs">
                <input type="number" placeholder="最低价" />
                <span>—</span>
                <input type="number" placeholder="最高价" />
              </div>
            </div>
            <div className="sidebar-card">
              <h4>🏆 段位要求</h4>
              <div className="sidebar-rank-grid">
                {RANKS.map(r => (
                  <div
                    key={r}
                    className={`sidebar-rank-item${activeRank === r ? ' active' : ''}`}
                    onClick={() => setActiveRank(r)}
                  >
                    {r}
                  </div>
                ))}
              </div>
            </div>
            <div className="sidebar-card">
              <h4>✔ 筛选条件</h4>
              <div className="sidebar-check-group">
                <label className="sidebar-check"><input type="checkbox" /> 全英雄 (120)</label>
                <label className="sidebar-check"><input type="checkbox" /> 荣耀典藏 (×2) (85)</label>
                <label className="sidebar-check"><input type="checkbox" defaultChecked /> 传说皮肤 (×5) (342)</label>
                <label className="sidebar-check"><input type="checkbox" /> 限定皮肤 (×10) (218)</label>
                <label className="sidebar-check"><input type="checkbox" /> 高胜率 (156)</label>
                <label className="sidebar-check"><input type="checkbox" /> 国服战力 (48)</label>
                <label className="sidebar-check"><input type="checkbox" /> 可换绑 (256)</label>
                <label className="sidebar-check"><input type="checkbox" defaultChecked /> 低风险 (189)</label>
              </div>
            </div>
            <button className="btn-sidebar-filter">筛选</button>
          </aside>

          {/* Account Grid */}
          <div className="main-content">
            <div className="sort-bar">
              <div className="result-count">共找到 <strong>12,836</strong> 个账号</div>
              <div className="sort-options">
                {SORTS.map(s => (
                  <div
                    key={s}
                    className={`sort-opt${activeSort === s ? ' active' : ''}`}
                    onClick={() => setActiveSort(s)}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </div>

            <div className="card-grid">
              {accounts.map(a => (
                <div className="account-card" key={a.id} onClick={() => openDetail(a.id)}>
                  <div className="card-img">
                    <div style={{
                      width: '100%', height: '100%',
                      background: `linear-gradient(135deg,${getCardGradient(a.style)})`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontSize: '48px', opacity: 0.3,
                    }}>⚔</div>
                    <span className={`card-badge ${getBadgeClass(a.badge)}`}>{getBadgeText(a.badge)}</span>
                    <div className="card-tag-row">
                      {a.heroList.slice(0, 3).map(h => (
                        <span key={h} className="card-mini-tag">{h}</span>
                      ))}
                    </div>
                  </div>
                  <div className="card-body">
                    <div className="card-title">{a.title}</div>
                    <div className="card-attrs">
                      <span className="card-attr">英雄<span className="attr-val">{a.heroes}</span></span>
                      <span className="card-attr">皮肤<span className="attr-val">{a.skins}</span></span>
                      <span className="card-attr">{a.rank}</span>
                      <span className="card-attr">V{a.vip}</span>
                    </div>
                  </div>
                  <div className="card-footer">
                    <div>
                      <span className="card-price"><span className="unit">¥</span>{a.price.toLocaleString()}</span>
                      <span className="card-price original">¥{a.estValue.toLocaleString()}</span>
                    </div>
                    <div className="card-actions">
                      <button className="btn-card btn-compare" onClick={e => e.stopPropagation()}>对比</button>
                      <button className="btn-card btn-buy" onClick={e => e.stopPropagation()}>购买</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="pagination">
              <span className="page-btn disabled">«</span>
              <span className="page-btn active">1</span>
              {[2, 3, 4, 5, 6, 7].map(p => <span key={p} className="page-btn">{p}</span>)}
              <span className="page-btn">...</span>
              <span className="page-btn">99</span>
              <span className="page-btn">»</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>游戏账号交易平台 · 官方担保交易 · 安全可靠</p>
        <p style={{ marginTop: '4px' }}>Copyright © 2026 GameAccountTrade. All rights reserved.</p>
      </footer>

      {/* Account Detail Modal */}
      {modalAccount && (
        <div className="modal-overlay open" onClick={e => { if (e.target === e.currentTarget) setModalAccount(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalAccount.title}</h3>
              <button className="modal-close" onClick={() => setModalAccount(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-section">
                  <h5>🎮 英雄资产</h5>
                  <div className="detail-row"><span>英雄数量</span><span className="dv">{modalAccount.heroes} / 120 {modalAccount.heroesFull ? '✅ 全英雄' : ''}</span></div>
                  <div className="detail-row"><span>核心英雄</span><span className="dv">{modalAccount.heroList.join('、')}</span></div>
                  <div className="detail-row"><span>位置倾向</span><span className="dv">{modalAccount.position}号</span></div>
                  <div className="detail-row"><span>主打英雄</span><span className="dv">{modalAccount.topHero}</span></div>
                </div>
                <div className="detail-section">
                  <h5>🎨 皮肤资产</h5>
                  <div className="detail-row"><span>皮肤总数</span><span className="dv">{modalAccount.skins}</span></div>
                  <div className="detail-row"><span>传说皮肤</span><span className="dv">{modalAccount.skinsLegend} 个</span></div>
                  <div className="detail-row"><span>限定皮肤</span><span className="dv">{modalAccount.skinsLimited} 个</span></div>
                  <div className="detail-row"><span>荣耀典藏</span><span className="dv">{modalAccount.skinsCollector} 个</span></div>
                  <div className="detail-row"><span>核心皮肤</span><span className="dv">{modalAccount.highlightSkins.slice(0, 4).join('、')}</span></div>
                </div>
                <div className="detail-section">
                  <h5>🏆 竞技属性</h5>
                  <div className="detail-row"><span>当前段位</span><span className="dv">{modalAccount.rank}</span></div>
                  <div className="detail-row"><span>贵族等级</span><span className="dv">V{modalAccount.vip}</span></div>
                  <div className="detail-row"><span>账号等级</span><span className="dv">Lv.{modalAccount.level}</span></div>
                  <div className="detail-row"><span>账号风格</span><span className="dv">{modalAccount.style}</span></div>
                  <div className="detail-row"><span>所在大区</span><span className="dv">{modalAccount.region}</span></div>
                </div>
                <div className="detail-section">
                  <h5>💰 价格评估</h5>
                  <div className="detail-row">
                    <span>卖家报价</span>
                    <span className="dv" style={{ color: 'var(--orange)', fontSize: '22px', fontWeight: 700 }}>¥{modalAccount.price.toLocaleString()}</span>
                  </div>
                  <div className="detail-row"><span>系统估价</span><span className="dv">¥{modalAccount.estValue.toLocaleString()}</span></div>
                  <div className="detail-row">
                    <span>性价比</span>
                    <span className="dv" style={{ color: modalAccount.estTag === 'good' ? 'var(--brand-green-dark)' : 'var(--orange)' }}>{modalAccount.estLabel}</span>
                  </div>
                  <div className="detail-row"><span>匹配度</span><span className="dv">{modalAccount.match}%</span></div>
                </div>
                <div className="detail-section detail-full">
                  <h5>🛡 风险评估</h5>
                  <div className={`risk-bar ${modalAccount.risk === '低' ? 'risk-low' : modalAccount.risk === '中' ? 'risk-mid' : 'risk-high'}`}>
                    <span style={{ fontSize: '18px' }}>{modalAccount.risk === '低' ? '✅' : modalAccount.risk === '中' ? '⚠' : '❌'}</span>
                    <span>风险等级：<strong>{modalAccount.risk}</strong></span>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {modalAccount.riskItems.map((item, i) => (
                      <div key={i} style={{ padding: '4px 0' }}>{i + 1}. {item}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant accounts={accounts} onCardClick={openDetail} />
    </>
  )
}
