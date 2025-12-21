import { useState, useCallback } from 'react'

const initialFilters = {
  countries: [],
  towns: [],
  segments: [],
  searchQuery: '',
  hideNoData: true,
}

export function useFilters() {
  const [filters, setFilters] = useState(initialFilters)

  const setCountryFilter = useCallback((countries) => {
    setFilters(prev => ({
      ...prev,
      countries: Array.isArray(countries) ? countries : [countries],
      // Clear town filter if countries change
      towns: prev.countries.join(',') !== countries.join(',') ? [] : prev.towns,
    }))
  }, [])

  const setTownFilter = useCallback((towns) => {
    setFilters(prev => ({
      ...prev,
      towns: Array.isArray(towns) ? towns : [towns],
    }))
  }, [])

  const setSegmentFilter = useCallback((segments) => {
    setFilters(prev => ({
      ...prev,
      segments: Array.isArray(segments) ? segments : [segments],
    }))
  }, [])

  const setSearchQuery = useCallback((query) => {
    setFilters(prev => ({
      ...prev,
      searchQuery: query,
    }))
  }, [])

  const clearFilters = useCallback(() => {
    setFilters(initialFilters)
  }, [])

  const toggleCountry = useCallback((country) => {
    setFilters(prev => {
      const countries = prev.countries.includes(country)
        ? prev.countries.filter(c => c !== country)
        : [...prev.countries, country]
      return {
        ...prev,
        countries,
        // Clear towns if all countries are deselected or new country added
        towns: countries.length === 0 ? [] : prev.towns,
      }
    })
  }, [])

  const toggleTown = useCallback((town) => {
    setFilters(prev => ({
      ...prev,
      towns: prev.towns.includes(town)
        ? prev.towns.filter(t => t !== town)
        : [...prev.towns, town],
    }))
  }, [])

  const toggleSegment = useCallback((segment) => {
    setFilters(prev => ({
      ...prev,
      segments: prev.segments.includes(segment)
        ? prev.segments.filter(s => s !== segment)
        : [...prev.segments, segment],
    }))
  }, [])

  const toggleHideNoData = useCallback(() => {
    setFilters(prev => ({
      ...prev,
      hideNoData: !prev.hideNoData,
    }))
  }, [])

  return {
    filters,
    setCountryFilter,
    setTownFilter,
    setSegmentFilter,
    setSearchQuery,
    clearFilters,
    toggleCountry,
    toggleTown,
    toggleSegment,
    toggleHideNoData,
  }
}

export default useFilters
