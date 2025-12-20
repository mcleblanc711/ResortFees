import { useState } from 'react'
import './FilterPanel.css'

function FilterPanel({
  options,
  filters,
  onCountryChange,
  onTownChange,
  onSegmentChange,
  onSearchChange,
  onClearFilters,
  hasActiveFilters,
}) {
  const [isExpanded, setIsExpanded] = useState({
    countries: true,
    towns: true,
    segments: true,
  })

  const toggleSection = (section) => {
    setIsExpanded(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const handleCountryToggle = (country) => {
    const newCountries = filters.countries.includes(country)
      ? filters.countries.filter(c => c !== country)
      : [...filters.countries, country]
    onCountryChange(newCountries)
  }

  const handleTownToggle = (town) => {
    const newTowns = filters.towns.includes(town)
      ? filters.towns.filter(t => t !== town)
      : [...filters.towns, town]
    onTownChange(newTowns)
  }

  const handleSegmentToggle = (segment) => {
    const newSegments = filters.segments.includes(segment)
      ? filters.segments.filter(s => s !== segment)
      : [...filters.segments, segment]
    onSegmentChange(newSegments)
  }

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h2>Filters</h2>
        {hasActiveFilters && (
          <button className="clear-btn" onClick={onClearFilters}>
            Clear all
          </button>
        )}
      </div>

      {/* Search */}
      <div className="filter-section">
        <label htmlFor="search" className="filter-label">Search Hotels</label>
        <input
          id="search"
          type="text"
          className="search-input"
          placeholder="Hotel name..."
          value={filters.searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Country Filter */}
      <div className="filter-section">
        <button
          className="section-header"
          onClick={() => toggleSection('countries')}
          aria-expanded={isExpanded.countries}
        >
          <span>Country</span>
          <span className="toggle-icon">{isExpanded.countries ? '\u25BC' : '\u25B6'}</span>
        </button>
        {isExpanded.countries && (
          <div className="filter-options">
            {options.countries.map(country => (
              <label key={country} className="filter-option">
                <input
                  type="checkbox"
                  checked={filters.countries.includes(country)}
                  onChange={() => handleCountryToggle(country)}
                />
                <span className="checkbox-custom"></span>
                <span className="option-label">{country}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Town Filter */}
      <div className="filter-section">
        <button
          className="section-header"
          onClick={() => toggleSection('towns')}
          aria-expanded={isExpanded.towns}
        >
          <span>Town</span>
          <span className="toggle-icon">{isExpanded.towns ? '\u25BC' : '\u25B6'}</span>
        </button>
        {isExpanded.towns && (
          <div className="filter-options scrollable">
            {options.towns.length === 0 ? (
              <p className="no-options">Select a country first</p>
            ) : (
              options.towns.map(town => (
                <label key={town} className="filter-option">
                  <input
                    type="checkbox"
                    checked={filters.towns.includes(town)}
                    onChange={() => handleTownToggle(town)}
                  />
                  <span className="checkbox-custom"></span>
                  <span className="option-label">{town}</span>
                </label>
              ))
            )}
          </div>
        )}
      </div>

      {/* Market Segment Filter */}
      <div className="filter-section">
        <button
          className="section-header"
          onClick={() => toggleSection('segments')}
          aria-expanded={isExpanded.segments}
        >
          <span>Market Segment</span>
          <span className="toggle-icon">{isExpanded.segments ? '\u25BC' : '\u25B6'}</span>
        </button>
        {isExpanded.segments && (
          <div className="segment-pills">
            {options.segments.map(segment => (
              <button
                key={segment}
                className={`segment-pill ${filters.segments.includes(segment) ? 'active' : ''}`}
                onClick={() => handleSegmentToggle(segment)}
              >
                {segment}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default FilterPanel
