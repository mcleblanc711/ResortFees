import './StatsPanel.css'

function StatsPanel({ stats }) {
  const formatCurrency = (amount) => {
    if (typeof amount !== 'number' || isNaN(amount)) return 'N/A'
    return `$${amount.toFixed(2)}`
  }

  return (
    <div className="stats-panel">
      <h2>Statistics</h2>

      <div className="stat-block">
        <div className="stat-value">{stats.total}</div>
        <div className="stat-label">Total Hotels</div>
      </div>

      {Object.keys(stats.byCountry).length > 0 && (
        <div className="stat-section">
          <h3>By Country</h3>
          <div className="stat-list">
            {Object.entries(stats.byCountry)
              .sort((a, b) => b[1] - a[1])
              .map(([country, count]) => (
                <div key={country} className="stat-row">
                  <span className="stat-name">{country}</span>
                  <span className="stat-count">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {Object.keys(stats.bySegment).length > 0 && (
        <div className="stat-section">
          <h3>By Segment</h3>
          <div className="stat-list">
            {['Luxury', 'Upscale', 'Upper-Midscale', 'Midscale', 'Economy']
              .filter(seg => stats.bySegment[seg])
              .map(segment => (
                <div key={segment} className="stat-row">
                  <span className="stat-name">{segment}</span>
                  <span className="stat-count">{stats.bySegment[segment]}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {Object.keys(stats.avgResortFeeBySegment).length > 0 && (
        <div className="stat-section">
          <h3>Avg. Resort Fee</h3>
          <div className="stat-list">
            {Object.entries(stats.avgResortFeeBySegment)
              .sort((a, b) => b[1] - a[1])
              .map(([segment, avg]) => (
                <div key={segment} className="stat-row">
                  <span className="stat-name">{segment}</span>
                  <span className="stat-count">{formatCurrency(avg)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {stats.commonFees.length > 0 && (
        <div className="stat-section">
          <h3>Common Fees</h3>
          <div className="stat-list">
            {stats.commonFees.map((fee, idx) => (
              <div key={idx} className="stat-row">
                <span className="stat-name fee-name">{fee.name}</span>
                <span className="stat-count">{fee.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default StatsPanel
