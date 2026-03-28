import client from './client'

export const getTransactions = (params) => client.get('/transactions', { params })
export const getSummary = (month, year) => client.get('/transactions/summary', { params: { month, year } })
export const getTransaction = (id) => client.get(`/transactions/${id}`)
export const updateCategory = (id, category_id) => client.patch(`/transactions/${id}`, { category_id })
export const categoriseAll = () => client.post('/transactions/categorise?use_llm=false')
export const getCategories = () => client.get('/transactions/categories')
