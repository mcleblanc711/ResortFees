import './Layout.css'

function Layout({ children }) {
  return (
    <div className="layout">
      {children}
      <footer className="app-footer">
        <p>Hotel Policy Explorer - Revenue Management Analytics</p>
        <p className="footer-note">Data sourced from official hotel websites and Booking.com</p>
      </footer>
    </div>
  )
}

export default Layout
