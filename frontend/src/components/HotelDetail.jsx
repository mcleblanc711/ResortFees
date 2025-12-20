import { useEffect } from 'react'
import './HotelDetail.css'

const segmentColors = {
  'Luxury': '#a855f7',
  'Upscale': '#3b82f6',
  'Upper-Midscale': '#22c55e',
  'Midscale': '#f59e0b',
  'Economy': '#6b7280',
}

function HotelDetail({ hotel, onClose }) {
  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const policyUrl = hotel.sources?.policyPage

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          {'\u2715'}
        </button>

        <header className="modal-header">
          <div className="header-top">
            <span className="hotel-rank">#{hotel.tripadvisorRank || '-'} on TripAdvisor</span>
            <span
              className="segment-badge"
              style={{ backgroundColor: segmentColors[hotel.marketSegment] || '#6b7280' }}
            >
              {hotel.marketSegment}
            </span>
          </div>
          <h2>{hotel.name}</h2>
          <p className="hotel-location">{hotel.town}, {hotel.region}, {hotel.country}</p>
        </header>

        {/* Policy Source Link - Prominently displayed */}
        {policyUrl && (
          <div className="policy-source">
            <a href={policyUrl} target="_blank" rel="noopener noreferrer" className="policy-link">
              <span className="link-icon">{'\u{1F517}'}</span>
              View Official Policy Page
              <span className="external-icon">{'\u2197'}</span>
            </a>
            <span className="source-note">
              Data source: {hotel.sources?.dataSource === 'official' ? 'Official website' : 'Booking.com'}
            </span>
          </div>
        )}

        <div className="modal-body">
          {/* Taxes Section */}
          <section className="detail-section">
            <h3>Taxes ({hotel.taxes?.length || 0})</h3>
            {hotel.taxes?.length > 0 ? (
              <div className="items-list">
                {hotel.taxes.map((tax, idx) => (
                  <div key={idx} className="item-row">
                    <div className="item-info">
                      <span className="item-name">{tax.name}</span>
                      {tax.notes && <span className="item-notes">{tax.notes}</span>}
                    </div>
                    <div className="item-amount">
                      <span className="amount">{tax.amount}</span>
                      <span className="basis">{tax.basis}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No tax information available</p>
            )}
          </section>

          {/* Fees Section */}
          <section className="detail-section">
            <h3>Fees ({hotel.fees?.length || 0})</h3>
            {hotel.fees?.length > 0 ? (
              <div className="items-list">
                {hotel.fees.map((fee, idx) => (
                  <div key={idx} className="item-row">
                    <div className="item-info">
                      <span className="item-name">{fee.name}</span>
                      {fee.includes && fee.includes.length > 0 && (
                        <span className="item-includes">
                          Includes: {fee.includes.join(', ')}
                        </span>
                      )}
                      {fee.notes && <span className="item-notes">{fee.notes}</span>}
                    </div>
                    <div className="item-amount">
                      <span className="amount">{fee.amount}</span>
                      <span className="basis">{fee.basis}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No fee information available</p>
            )}
          </section>

          {/* Extra Person Policy */}
          <section className="detail-section">
            <h3>Extra Person Policy</h3>
            {hotel.extraPersonPolicy ? (
              <div className="policy-details">
                {hotel.extraPersonPolicy.childrenFreeAge && (
                  <div className="policy-row">
                    <span className="policy-label">Children Free Age</span>
                    <span className="policy-value">Under {hotel.extraPersonPolicy.childrenFreeAge}</span>
                  </div>
                )}
                {hotel.extraPersonPolicy.childCharge && (
                  <div className="policy-row">
                    <span className="policy-label">Child Charge</span>
                    <span className="policy-value">
                      {hotel.extraPersonPolicy.childCharge.amount} {hotel.extraPersonPolicy.childCharge.basis}
                    </span>
                  </div>
                )}
                {hotel.extraPersonPolicy.adultCharge && (
                  <div className="policy-row">
                    <span className="policy-label">Adult Charge</span>
                    <span className="policy-value">
                      {hotel.extraPersonPolicy.adultCharge.amount} {hotel.extraPersonPolicy.adultCharge.basis}
                    </span>
                  </div>
                )}
                {hotel.extraPersonPolicy.maxOccupancy && (
                  <div className="policy-row">
                    <span className="policy-label">Max Occupancy</span>
                    <span className="policy-value">{hotel.extraPersonPolicy.maxOccupancy}</span>
                  </div>
                )}
                {hotel.extraPersonPolicy.notes && (
                  <p className="policy-notes">{hotel.extraPersonPolicy.notes}</p>
                )}
              </div>
            ) : (
              <p className="no-data">No extra person policy information available</p>
            )}
          </section>

          {/* Damage Deposit */}
          <section className="detail-section">
            <h3>Damage Deposit</h3>
            {hotel.damageDeposit ? (
              <div className="policy-details">
                <div className="policy-row">
                  <span className="policy-label">Amount</span>
                  <span className="policy-value">{hotel.damageDeposit.amount}</span>
                </div>
                <div className="policy-row">
                  <span className="policy-label">Basis</span>
                  <span className="policy-value">{hotel.damageDeposit.basis}</span>
                </div>
                {hotel.damageDeposit.method && (
                  <div className="policy-row">
                    <span className="policy-label">Method</span>
                    <span className="policy-value">{hotel.damageDeposit.method}</span>
                  </div>
                )}
                {hotel.damageDeposit.refundTimeline && (
                  <div className="policy-row">
                    <span className="policy-label">Refund Timeline</span>
                    <span className="policy-value">{hotel.damageDeposit.refundTimeline}</span>
                  </div>
                )}
                {hotel.damageDeposit.notes && (
                  <p className="policy-notes">{hotel.damageDeposit.notes}</p>
                )}
              </div>
            ) : (
              <p className="no-data">No damage deposit information available</p>
            )}
          </section>

          {/* Promotions */}
          {hotel.promotions?.length > 0 && (
            <section className="detail-section">
              <h3>Current Promotions</h3>
              <div className="promotions-list">
                {hotel.promotions.map((promo, idx) => (
                  <div key={idx} className="promo-card">
                    <h4>{promo.name}</h4>
                    <p>{promo.description}</p>
                    {(promo.validFrom || promo.validTo) && (
                      <p className="promo-dates">
                        Valid: {promo.validFrom || 'N/A'} - {promo.validTo || 'N/A'}
                      </p>
                    )}
                    {promo.promoCode && (
                      <p className="promo-code">Code: <code>{promo.promoCode}</code></p>
                    )}
                    {promo.sourceUrl && (
                      <a href={promo.sourceUrl} target="_blank" rel="noopener noreferrer">
                        View promotion {'\u2197'}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Scraping Notes */}
          {hotel.scrapingNotes && (
            <div className="scraping-notes">
              <strong>Note:</strong> {hotel.scrapingNotes}
            </div>
          )}

          <div className="scraped-at">
            Last updated: {new Date(hotel.scrapedAt).toLocaleDateString()}
          </div>
        </div>
      </div>
    </div>
  )
}

export default HotelDetail
