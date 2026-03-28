import { useEffect, useState } from 'react'
import { getAccounts } from '../api/banking'
import { getSummary, getTransactions } from '../api/transactions'

export default function useDashboard(month, year) {
  const [accounts, setAccounts] = useState([])
  const [summary, setSummary] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const fetchAll = async () => {
      try {
        const [acctRes, summaryRes, txRes] = await Promise.all([
          getAccounts(),
          getSummary(month, year),
          getTransactions({ month, year, page_size: 500 }),
        ])
        if (!cancelled) {
          setAccounts(acctRes.data)
          setSummary(summaryRes.data)
          setTransactions(txRes.data.transactions || [])
        }
      } catch (err) {
        if (!cancelled) setError(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [month, year])

  const metrics = {
    totalSpent: transactions.filter(t => t.amount < 0).reduce((s, t) => s + t.amount, 0),
    totalIncome: transactions.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0),
    anomalyCount: transactions.filter(t => t.is_anomaly).length,
  }
  metrics.saved = metrics.totalIncome + metrics.totalSpent

  const dailyData = (() => {
    const daysInMonth = new Date(year, month, 0).getDate()
    const today = new Date()
    const isCurrentMonth = month === today.getMonth() + 1 && year === today.getFullYear()
    const todayDay = today.getDate()

    return Array.from({ length: daysInMonth }, (_, i) => {
      const day = i + 1
      const total = transactions
        .filter(tx => {
          const d = new Date(tx.timestamp)
          return d.getDate() === day && tx.amount < 0
        })
        .reduce((s, tx) => s + Math.abs(tx.amount), 0)
      return { day, amount: parseFloat(total.toFixed(2)), isFuture: isCurrentMonth && day > todayDay }
    })
  })()

  const recent = [...transactions]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 10)

  return { accounts, summary, transactions, dailyData, recent, metrics, loading, error }
}
