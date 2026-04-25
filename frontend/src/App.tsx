import { Navigate, Route, Routes } from 'react-router-dom'
import TerminalShell from './components/terminal/TerminalShell'
import ExplorerView from './pages/ExplorerView'
import LandingView from './pages/LandingView'
import RadarView from './pages/RadarView'
import SettingsView from './pages/SettingsView'
import TokenWarRoomView from './pages/TokenWarRoomView'
import WhalesView from './pages/WhalesView'
import WatchlistView from './pages/WatchlistView'
import WhaleDetailView from './pages/WhaleDetailView'
import AlertsView from './pages/AlertsView'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingView />} />
      <Route element={<TerminalShell />}>
        <Route path="radar" element={<RadarView />} />
        <Route path="whales" element={<WhalesView />} />
        <Route path="whale/:address" element={<WhaleDetailView />} />
        <Route path="explorer" element={<ExplorerView />} />
        <Route path="watchlist" element={<WatchlistView />} />
        <Route path="alerts" element={<AlertsView />} />
        <Route path="settings" element={<SettingsView />} />
        <Route path="token/:address" element={<TokenWarRoomView />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
