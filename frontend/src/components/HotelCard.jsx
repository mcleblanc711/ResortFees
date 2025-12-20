import './HotelCard.css'

const segmentColors = {
  'Luxury': '#a855f7',
  'Upscale': '#3b82f6',
  'Upper-Midscale': '#22c55e',
  'Midscale': '#f59e0b',
  'Economy': '#6b7280',
}

function HotelCard({ hotel, onClick }) {
  const taxCount = hotel.taxes?.length || 0
  const feeCount = hotel.fees?.length || 0
  const totalCharges = taxCount + feeCount

  const resortFee = hotel.fees?.find(f =>
    f.name.toLowerCase().includes('resort')
  )

  return (
    <article className="hotel-card" onClick={onClick} tabIndex={0} role="button">
      <div className="card-header">
        <div className="hotel-rank">#{hotel.tripadvisorRank || '-'}</div>
        <span
          className="segment-badge"
          style={{ backgroundColor: segmentColors[hotel.marketSegment] || '#6b7280' }}
        >
          {hotel.marketSegment}
        </span>
      </div>

      <h3 className="hotel-name">{hotel.name}</h3>

      <div className="hotel-location">
        <span className="location-icon">{'\u{1F4CD}'}</span>
        {hotel.town}, {hotel.country}
      </div>

      <div className="card-stats">
        <div className="stat-item">
          <span className="stat-number">{totalCharges}</span>
          <span className="stat-text">taxes & fees</span>
        </div>

        {resortFee && (
          <div className="stat-item highlight">
            <span className="stat-number">{resortFee.amount}</span>
            <span className="stat-text">resort fee</span>
          </div>
        )}
      </div>

      <div className="card-footer">
        <span className="source-indicator">
          {hotel.sources?.dataSource === 'official' ? 'Official site' : 'Booking.com'}
        </span>
        <span className="view-details">View details {'\u2192'}</span>
      </div>
    </article>
  )
}

export default HotelCard
