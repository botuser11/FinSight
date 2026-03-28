import client from './client'

export const getConnectUrl = () => client.get('/banking/connect')
export const getAccounts = () => client.get('/banking/accounts')
export const syncTransactions = () => client.post('/banking/sync')
export const disconnectBank = () => client.delete('/banking/disconnect')
