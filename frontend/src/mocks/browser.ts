import { setupWorker } from 'msw/browser'
import { homeHandlers } from './handlers/home'

export const worker = setupWorker(...homeHandlers)
