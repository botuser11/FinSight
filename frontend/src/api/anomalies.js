import client from './client'

export const runDetection = () => client.post('/anomalies/run')
export const getAnomalies = () => client.get('/anomalies')
export const dismissAnomaly = (id) => client.patch(`/anomalies/${id}/dismiss`)
