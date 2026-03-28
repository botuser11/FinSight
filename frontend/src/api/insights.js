import client from './client'

export const getSubscriptions = () => client.get('/insights/subscriptions')
export const getTrends = () => client.get('/insights/trends')
export const getPriceAlerts = () => client.get('/insights/price-alerts')
