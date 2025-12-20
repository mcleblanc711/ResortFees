import './ThemeSelector.css'

const themeLabels = {
  'dark': 'Dark',
  'frutiger-aero': 'Frutiger Aero',
  'flat': 'Flat',
  'cyberpunk': 'Cyberpunk',
  'modern': 'Modern',
}

const themeIcons = {
  'dark': '\u{1F319}',      // crescent moon
  'frutiger-aero': '\u{1F4A7}', // droplet
  'flat': '\u{25A0}',       // square
  'cyberpunk': '\u{26A1}',  // lightning
  'modern': '\u{2728}',     // sparkles
}

function ThemeSelector({ currentTheme, onThemeChange }) {
  return (
    <div className="theme-selector">
      <span className="theme-label">Theme:</span>
      <div className="theme-buttons">
        {Object.entries(themeLabels).map(([key, label]) => (
          <button
            key={key}
            className={`theme-btn ${currentTheme === key ? 'active' : ''}`}
            onClick={() => onThemeChange(key)}
            aria-pressed={currentTheme === key}
            title={label}
          >
            <span className="theme-icon">{themeIcons[key]}</span>
            <span className="theme-name">{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default ThemeSelector
