import client from './client'

export const getForecast = (months = 3) =>
  client.get('/forecast', { params: { months_ahead: months } })

export const getForecastHistory = () => client.get('/forecast/history')
