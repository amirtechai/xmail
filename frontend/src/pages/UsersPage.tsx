import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Plus, X, ShieldCheck } from 'lucide-react'
import { usersApi, type User, type UserCreate, type UserUpdate } from '../lib/api'
import { useAuth } from '../lib/auth'
import clsx from 'clsx'

function CreateUserModal({
  onCreated,
  onClose,
}: {
  onCreated: (u: User) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<UserCreate>({ email: '', password: '', role: 'viewer' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    setSaving(true)
    setError(null)
    try {
      const { data } = await usersApi.create(form)
      onCreated(data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to create user'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Create User</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-text-muted mb-1">Email</label>
            <input
              type="email"
              className="input w-full text-xs"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Password</label>
            <input
              type="password"
              className="input w-full text-xs"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Role</label>
            <select
              className="input w-full text-xs"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserCreate['role'] })}
            >
              <option value="viewer">Viewer</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        {error && <p className="text-xs text-accent-red mt-2">{error}</p>}
        <div className="flex gap-2 justify-end mt-4">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn-primary flex items-center gap-1.5"
            disabled={saving || !form.email || !form.password}
            onClick={() => { void handleSubmit() }}
          >
            <Plus className="w-3.5 h-3.5" />
            {saving ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function UsersPage() {
  const currentUser = useAuth((s) => s.user)

  if (currentUser && currentUser.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await usersApi.list()
      setUsers(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleUpdate = async (id: string, patch: UserUpdate) => {
    setUpdatingId(id)
    try {
      const { data } = await usersApi.updateUser(id, patch)
      setUsers((prev) => prev.map((u) => (u.id === id ? data : u)))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-accent-yellow" />
          Users
          <span className="text-text-muted text-base font-normal">({users.length})</span>
        </h1>
        <button
          className="btn-primary flex items-center gap-1.5 text-sm"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="w-4 h-4" />
          New User
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="pb-2 text-left font-medium">Email</th>
              <th className="pb-2 text-left font-medium">Role</th>
              <th className="pb-2 text-left font-medium">Status</th>
              <th className="pb-2 text-left font-medium">Created</th>
              <th className="pb-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-text-muted">Loading…</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-text-muted">No users found.</td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-bg-hover">
                  <td className="py-2.5 font-mono text-text-primary">{u.email}</td>
                  <td className="py-2.5">
                    <select
                      className={clsx('input text-xs py-0.5 px-1', updatingId === u.id && 'opacity-50')}
                      value={u.role}
                      disabled={updatingId === u.id || u.id === currentUser?.id}
                      onChange={(e) => { void handleUpdate(u.id, { role: e.target.value as UserUpdate['role'] }) }}
                    >
                      <option value="viewer">viewer</option>
                      <option value="operator">operator</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="py-2.5">
                    <span className={clsx(
                      'font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest uppercase',
                      u.is_active
                        ? 'bg-accent-green/10 text-accent-green border-accent-green'
                        : 'bg-border text-text-muted border-border',
                    )}>
                      {u.is_active ? 'active' : 'disabled'}
                    </span>
                  </td>
                  <td className="py-2.5 text-text-muted">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2.5 text-right">
                    {u.id !== currentUser?.id && (
                      <button
                        className={clsx(
                          'text-xs px-2 py-1 rounded border transition-colors',
                          u.is_active
                            ? 'border-accent-red/40 text-accent-red hover:bg-accent-red/10'
                            : 'border-accent-green/40 text-accent-green hover:bg-accent-green/10',
                          updatingId === u.id && 'opacity-50 pointer-events-none',
                        )}
                        onClick={() => { void handleUpdate(u.id, { is_active: !u.is_active }) }}
                      >
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateUserModal
          onCreated={(u) => { setUsers((prev) => [...prev, u]); setShowCreate(false) }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
