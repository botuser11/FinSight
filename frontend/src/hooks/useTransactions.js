import { useEffect, useState } from 'react'
import { getTransactions } from '../api/transactions'

export default function useTransactions(filters) {
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    getTransactions(filters)
      .then(res => {
        if (!cancelled) {
          setTransactions(res.data.transactions || [])
          setTotal(res.data.total || 0)
        }
      })
      .catch(err => {
        if (!cancelled) setError(err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [JSON.stringify(filters)])

  return { transactions, total, loading, error }
}
