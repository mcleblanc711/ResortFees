import { useState, useMemo } from 'react'
import { useTheme } from './hooks/useTheme'
import { useFilters } from './hooks/useFilters'
import Layout from './components/Layout'
import ThemeSelector from './components/ThemeSelector'
import FilterPanel from './components/FilterPanel'
import StatsPanel from './components/StatsPanel'
import HotelCard from './components/HotelCard'
import HotelDetail from './components/HotelDetail'
import hotelsData from './data/hotels.json'

import './themes/dark.css'
import './themes/frutiger-aero.css'
import './themes/flat.css'
import './themes/cyberpunk.css'
import './themes/modern.css'

function App() {
  const { theme, setTheme } = useTheme()
  const {
    filters,
    setCountryFilter,
    setTownFilter,
    setSegmentFilter,
    setSearchQuery,
    clearFilters,
  } = useFilters()

  const [selectedHotel, setSelectedHotel] = useState(null)

  // Get unique countries and towns for filter options
  const filterOptions = useMemo(() => {
    const countries = [...new Set(hotelsData.map(h => h.country))].sort()
    const towns = filters.countries.length > 0
      ? [...new Set(
          hotelsData
            .filter(h => filters.countries.includes(h.country))
            .map(h => h.town)
        )].sort()
      : [...new Set(hotelsData.map(h => h.town))].sort()
    const segments = ['Luxury', 'Upscale', 'Upper-Midscale', 'Midscale', 'Economy']

    return { countries, towns, segments }
  }, [filters.countries])

  // Filter hotels based on current filters
  const filteredHotels = useMemo(() => {
    return hotelsData.filter(hotel => {
      // Country filter
      if (filters.countries.length > 0 && !filters.countries.includes(hotel.country)) {
        return false
      }

      // Town filter
      if (filters.towns.length > 0 && !filters.towns.includes(hotel.town)) {
        return false
      }

      // Segment filter
      if (filters.segments.length > 0 && !filters.segments.includes(hotel.marketSegment)) {
        return false
      }

      // Search query
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        const searchableText = `${hotel.name} ${hotel.town} ${hotel.country}`.toLowerCase()
        if (!searchableText.includes(query)) {
          return false
        }
      }

      return true
    })
  }, [filters])

  // Calculate stats
  const stats = useMemo(() => {
    const total = filteredHotels.length

    const byCountry = filteredHotels.reduce((acc, hotel) => {
      acc[hotel.country] = (acc[hotel.country] || 0) + 1
      return acc
    }, {})

    const bySegment = filteredHotels.reduce((acc, hotel) => {
      acc[hotel.marketSegment] = (acc[hotel.marketSegment] || 0) + 1
      return acc
    }, {})

    // Calculate average resort fee by segment
    const resortFeesBySegment = {}
    filteredHotels.forEach(hotel => {
      const resortFee = hotel.fees?.find(f =>
        f.name.toLowerCase().includes('resort')
      )
      if (resortFee) {
        const amount = parseFloat(resortFee.amount.replace(/[^0-9.]/g, ''))
        if (!isNaN(amount)) {
          if (!resortFeesBySegment[hotel.marketSegment]) {
            resortFeesBySegment[hotel.marketSegment] = []
          }
          resortFeesBySegment[hotel.marketSegment].push(amount)
        }
      }
    })

    const avgResortFeeBySegment = {}
    Object.entries(resortFeesBySegment).forEach(([segment, fees]) => {
      avgResortFeeBySegment[segment] = fees.reduce((a, b) => a + b, 0) / fees.length
    })

    // Most common fee types
    const feeTypeCounts = {}
    filteredHotels.forEach(hotel => {
      hotel.fees?.forEach(fee => {
        const type = fee.name.toLowerCase()
        feeTypeCounts[type] = (feeTypeCounts[type] || 0) + 1
      })
    })

    const commonFees = Object.entries(feeTypeCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }))

    return {
      total,
      byCountry,
      bySegment,
      avgResortFeeBySegment,
      commonFees,
    }
  }, [filteredHotels])

  const hasActiveFilters =
    filters.countries.length > 0 ||
    filters.towns.length > 0 ||
    filters.segments.length > 0 ||
    filters.searchQuery

  return (
    <Layout>
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <h1>Hotel Policy Explorer</h1>
            <p>Compare taxes, fees, and policies across resort hotels</p>
          </div>
          <ThemeSelector currentTheme={theme} onThemeChange={setTheme} />
        </div>
      </header>

      <main className="app-main">
        <aside className="sidebar">
          <FilterPanel
            options={filterOptions}
            filters={filters}
            onCountryChange={setCountryFilter}
            onTownChange={setTownFilter}
            onSegmentChange={setSegmentFilter}
            onSearchChange={setSearchQuery}
            onClearFilters={clearFilters}
            hasActiveFilters={hasActiveFilters}
          />
          <StatsPanel stats={stats} />
        </aside>

        <section className="hotel-grid">
          {filteredHotels.length === 0 ? (
            <div className="no-results">
              <p>No hotels found matching your filters.</p>
              {hasActiveFilters && (
                <button onClick={clearFilters} className="clear-filters-btn">
                  Clear all filters
                </button>
              )}
            </div>
          ) : (
            filteredHotels.map(hotel => (
              <HotelCard
                key={hotel.id}
                hotel={hotel}
                onClick={() => setSelectedHotel(hotel)}
              />
            ))
          )}
        </section>
      </main>

      {selectedHotel && (
        <HotelDetail
          hotel={selectedHotel}
          onClose={() => setSelectedHotel(null)}
        />
      )}
    </Layout>
  )
}

export default App
