import { HashRouter } from 'react-router-dom'
import { Shell } from '../components/Shell'
import { LocaleProvider } from '../i18n/LocaleProvider'
import { AppRoutes } from './routes'

export function App(){
  return <LocaleProvider><HashRouter><Shell><AppRoutes/></Shell></HashRouter></LocaleProvider>
}
